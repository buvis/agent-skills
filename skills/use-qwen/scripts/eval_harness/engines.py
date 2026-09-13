"""The engine adapters of the qwen evaluation harness: qwen, sonnet and cmd.

Every engine runs under `run_bounded`, so a hung one is stopped at the bound
and its whole process group reaped. What a run reports is what was observed:
the identity line the wrapper announced, the transcript it filed, the exit it
returned. Nothing is echoed back from the settings as if it had been seen.
"""
import http.client
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from eval_harness.events import read_events
from eval_harness.runner import (
    CommandResult,
    JobAssignmentError,
    LaunchError,
    OrphanError,
    run_bounded,
)

# Both wrappers are reached through the `~/.agents` link farm, the one
# discovery path every host shares; the transcript root is Claude's own.
QWEN_SCRIPT = Path(".agents") / "skills" / "use-qwen" / "scripts" / "qwen-run.sh"
SONNET_SCRIPT = Path(".agents") / "skills" / "use-sonnet" / "scripts" / "sonnet-run.sh"
PROJECTS_ROOT = Path(".claude") / "projects"
SESSION_DIR_ENV = "PI_CODING_AGENT_SESSION_DIR"

_SAMPLING_KEYS = ("temperature", "top_k", "top_p", "min_p")
_CMD_IDENTITY = re.compile(r"Using engine 'cmd:[^']*'")
_PROBE_TIMEOUT_S = 60.0


@dataclass(frozen=True)
class EngineSettings:
    qwen_provider: str | None
    qwen_model: str | None
    sonnet_model: str | None
    usage_limit_cmd: Path | None
    server_reasoning_effort: str | None


def build_argv(engine_id: str, command: str, prompt_file: Path, clone: Path,
               out_file: Path, settings: EngineSettings,
               session_uuid: str) -> list[str]:
    """The exact argv one engine is dispatched with."""
    if command == "qwen":
        return ["bash", str(Path.home() / QWEN_SCRIPT), "--approved-only",
                "-P", settings.qwen_provider, "-m", settings.qwen_model,
                "-f", str(prompt_file), "-o", str(out_file)]
    if command == "sonnet":
        return ["bash", str(Path.home() / SONNET_SCRIPT), "-y", "-m", settings.sonnet_model,
                "-d", str(clone), "-f", str(prompt_file), "-o", str(out_file),
                "-S", session_uuid]
    return [*_command_tokens(command), str(prompt_file)]


def _command_tokens(command: str) -> list[str]:
    """The argv a `cmd:` engine string names, whole, on this platform."""
    if not command.startswith("cmd:"):
        raise ValueError(f"not an engine command: {command!r}")
    tokens = shlex.split(command[len("cmd:"):], posix=os.name != "nt")
    if os.name == "nt":
        tokens = [token.strip('"') for token in tokens]
    if tokens and tokens[0].lower().endswith(".py"):
        tokens = [sys.executable, *tokens]
    return tokens


def dispatch(engine_id: str, command: str, prompt_file: Path, clone: Path,
             attempt_dir: Path, settings: EngineSettings,
             bound_s: float) -> dict:
    """Run one attempt and report its engine_run block, launched or not.

    Only a child the host refused to create is "not-started": the runner says
    so structurally, and every failure after creation is a started run. A halt
    raised past this point - the tree still has members, or the host would not
    contain the child - carries the block measured so far as its `observed`.
    """
    session_uuid = str(uuid.uuid4())
    out_file, wrapper = attempt_dir / "out.txt", attempt_dir / "wrapper.txt"
    argv = build_argv(engine_id, command, prompt_file, clone, out_file, settings, session_uuid)
    env = None
    if command == "qwen":
        env = dict(os.environ, **{SESSION_DIR_ENV: str(attempt_dir / "pi-sessions")})
    # The wrappers fill out.txt themselves through `-o`, so both their streams
    # go to wrapper.txt; a cmd engine's stdout is its out.txt, its stderr the wrapper.
    sinks = {"stdout_path": wrapper}
    if command.startswith("cmd:"):
        sinks = {"stdout_path": out_file, "stderr_path": wrapper}
    try:
        result, tree = run_bounded(argv, clone, bound_s, env=env, **sinks)
    except LaunchError:
        return _unmeasured(argv, "not-started", out_file)
    except JobAssignmentError as halt:
        halt.observed = _unmeasured(argv, "started", out_file)
        raise
    except OSError as error:
        # The child was created; what failed came after it. This line is the
        # failure's whole record: the block says only that the run started.
        with (attempt_dir / "progress.log").open("a", encoding="utf-8") as log:
            log.write("engine: %s: %s\n" % (type(error).__name__, error))
        return _unmeasured(argv, "started", out_file)
    session = _collect_transcript(command, attempt_dir, session_uuid)
    run = _engine_run(argv, "started", result, _identity(command, wrapper, settings),
                      read_events(session, out_file),
                      _usage_limit(settings.usage_limit_cmd, out_file))
    if tree.survivors():
        halt = OrphanError("%s: the process group still has members" % engine_id)
        halt.observed = run
        raise halt
    return run


def _unmeasured(argv: list[str], launch: str, out_file: Path) -> dict:
    """The block of a run nothing was measured of: null fields around the launch state."""
    return _engine_run(argv, launch, None, None, read_events(None, out_file), "unchecked")


def _engine_run(argv: list[str], launch: str, result: CommandResult | None,
                identity: str | None, evidence: dict, usage_limit: str) -> dict:
    """The engine_run block, in the record contract's key order."""
    return {"argv": argv,
            "launch": launch,
            "exit": result.rc if result else None,
            "timed_out": result.timed_out if result else False,
            "wall_s": result.wall_s if result else None,
            "identity": identity,
            "completion": evidence["completion"],
            "final_message_bytes": evidence["final_message_bytes"],
            "usage_limit": usage_limit,
            "first_edit_s": evidence["first_edit_s"],
            "usage": evidence["usage"]}


def _collect_transcript(command: str, attempt_dir: Path, session_uuid: str) -> Path | None:
    """Copy the transcript this run filed to `<attempt_dir>/session.jsonl`.

    A `cmd:` engine files its own there; qwen's is the newest under the session
    directory it was handed, sonnet's the one its uuid names under the
    projects root, wherever it nests.
    """
    target = attempt_dir / "session.jsonl"
    if command == "qwen":
        found = _newest_jsonl(attempt_dir / "pi-sessions")
    elif command == "sonnet":
        found = next((Path.home() / PROJECTS_ROOT).rglob(session_uuid + ".jsonl"), None)
    else:
        return target
    if found is None:
        return None
    shutil.copyfile(found, target)
    return target


def _newest_jsonl(directory: Path) -> Path | None:
    """The most recently modified transcript under `directory`, whatever its name or size."""
    transcripts = list(directory.rglob("*.jsonl"))
    if not transcripts:
        return None
    return max(transcripts, key=lambda path: path.stat().st_mtime)


def _identity(command: str, wrapper: Path, settings: EngineSettings) -> str | None:
    """The identity the engine itself announced, or the model flag sonnet was passed."""
    if command == "sonnet":
        return settings.sonnet_model
    lines = wrapper.read_text(encoding="utf-8", errors="replace").splitlines()
    if command == "qwen":
        announced = f"Using provider '{settings.qwen_provider}' model '{settings.qwen_model}'"
        return announced if announced in lines else None
    return next((line for line in lines if _CMD_IDENTITY.fullmatch(line)), None)


def _usage_limit(checker: Path | None, out_file: Path) -> str:
    """What the usage-limit checker said of the capture: it exits 0 when STUCK."""
    if checker is None:
        return "unchecked"
    try:
        probe = subprocess.run([str(checker), "--log", str(out_file)], stdin=subprocess.DEVNULL,
                               capture_output=True, timeout=_PROBE_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired):
        return "unchecked"
    return "hit" if probe.returncode == 0 else "clear"


def record_versions(engine_ids: Sequence[str],
                    settings: EngineSettings) -> dict[str, str | None]:
    """Each real engine's CLI version, probed only when that engine runs."""
    return {"pi": _version("pi") if "qwen" in engine_ids else None,
            "claude": _version("claude") if "sonnet" in engine_ids else None}


def _version(cli: str) -> str | None:
    """`<cli> --version`, or None when the CLI is not on PATH or does not answer."""
    resolved = shutil.which(cli)
    if resolved is None:
        return None
    try:
        probe = subprocess.run([resolved, "--version"], stdin=subprocess.DEVNULL,
                               capture_output=True, text=True, timeout=_PROBE_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return probe.stdout.strip() or None


def server_root(provider_url: str) -> str:
    """The URL one component above a trailing /v1, or the URL less its trailing slash."""
    root = provider_url.rstrip("/")
    return root[:-len("/v1")] if root.endswith("/v1") else root


def fetch_server_props(provider_url: str, declared_effort: str | None,
                       timeout_s: float = 10.0) -> dict:
    """The server block read off `<root>/props`: nulls and a diagnostic when it cannot be.

    The declared effort is the operator's label and travels as given; what the
    server says about supporting one is reported beside it, never in its place.
    """
    body, error = _get_json(server_root(provider_url) + "/props", timeout_s)
    generation = _object(body.get("default_generation_settings"))
    params = generation.get("params")
    return {"n_ctx": generation.get("n_ctx"),
            "model_alias": body.get("model_alias"),
            "build_info": body.get("build_info"),
            "sampling": ({key: params.get(key) for key in _SAMPLING_KEYS}
                         if isinstance(params, dict) else None),
            "supports_reasoning_effort": _object(
                body.get("chat_template_caps")).get("supports_reasoning_effort"),
            "declared_effort": declared_effort,
            "metadata_error": error}


def _object(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _get_json(url: str, timeout_s: float) -> tuple[dict, str | None]:
    """The JSON object at `url`, or an empty one and a credential-free diagnostic."""
    try:
        with urllib.request.urlopen(_without_credential(url), timeout=timeout_s) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return {}, f"GET /props answered HTTP {error.code}"
    except (OSError, http.client.HTTPException, ValueError) as error:
        return {}, f"GET /props failed: {error}"
    if not isinstance(body, dict):
        return {}, f"GET /props answered a JSON {type(body).__name__}, not an object"
    return body, None


def _without_credential(url: str) -> str:
    """`url` with any userinfo dropped: it belongs in no request line and no diagnostic."""
    parts = urlsplit(url)
    if "@" not in parts.netloc:
        return url
    return urlunsplit(parts._replace(netloc=parts.netloc.rpartition("@")[2]))
