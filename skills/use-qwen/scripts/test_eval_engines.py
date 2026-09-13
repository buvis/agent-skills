"""Tests for eval_harness/engines.py: the qwen, sonnet and cmd adapters."""
import json
import os
import shlex
import shutil
import sys
import time
import uuid
from pathlib import Path

import pytest

import eval_harness_fixtures
from eval_harness import engines
from eval_harness import records
from eval_harness_engine_helpers import (ASCII_TEXT, FINAL_TEXT, QWEN_MODEL, QWEN_PROVIDER,
                                         SONNET_MODEL, _assistant, _expected_usage, _settings,
                                         _user)
from eval_harness_fixture_helpers import (ATTEMPT_DIR_ENV, HEARTBEAT_ENV, _engine_argv,
                                          _prompt_in, _stopped_growing)


# -- the engine adapters: what the cases below are built from ---------------

# The harness dispatches through the `~/.agents` link farm, which is the one
# discovery path every host shares, so both paths hang off `Path.home()`.
QWEN_SCRIPT = ".agents/skills/use-qwen/scripts/qwen-run.sh"
SONNET_SCRIPT = ".agents/skills/use-sonnet/scripts/sonnet-run.sh"

# qwen-run.sh prints this on stderr, outside its `-o` tee, so it lands in the
# wrapper capture and never in out.txt.
QWEN_IDENTITY = "Using provider '%s' model '%s'" % (QWEN_PROVIDER, QWEN_MODEL)

# A stderr line that names the same provider and model without being the
# announcement: the literal is the evidence, and this is not the literal.
QWEN_STDERR_NOISE = ("warn: provider '%s' answered slowly for model '%s'"
                     % (QWEN_PROVIDER, QWEN_MODEL))

# Three well-formed announcements that name the wrong pair: another provider,
# another model, or both. Each is the literal's shape, so only a comparison
# against the configured provider AND model tells them from the real one.
QWEN_WRONG_ANNOUNCEMENTS = (
    "Using provider 'other-provider' model 'other-model'",
    "Using provider 'other-provider' model '%s'" % QWEN_MODEL,
    "Using provider '%s' model 'other-model'" % QWEN_PROVIDER,
)

# What the fake engine announces on stderr in `pass` mode, byte for byte.
FAKE_IDENTITY = "Using engine 'cmd:pass'"

# What every stub wrapper writes to its `-o` file. Its length matches no
# transcript text below, so a byte count says which of the two was read.
WRAPPER_NOISE = "the wrapper printed a diagnostic and nothing else"

# A third final text, 39 bytes: unlike both texts above, so a second attempt's
# transcript can be told from the first's and from a decoy's by size alone.
SECOND_TEXT = "the second attempt answered differently"

# A stale answer far longer than any attempt's, so the biggest transcript in a
# session directory is never the newest one: a lookup ranking by size lands
# here, and only the modification time reaches this run's.
LONG_STALE_TEXT = ("an earlier run of the day answered at length: it read the parser, "
                   "traced the empty-input path through three helpers, wrote a regression "
                   "test, and then explained every step of the fix in four more sentences")

# Two transcript names that sort before and after any lowercase uuid4, so a
# lookup that takes the first or the last name under a projects root lands on
# one of these rather than on the transcript the wrapper filed.
DECOY_UUIDS = ("00000000-0000-4000-8000-000000000000", "ffffffff-ffff-4fff-bfff-ffffffffffff")

# How long a hung engine is given before the bound fires, and the most wall
# time a bounded run may then report: enough for a terminate and a reap, far
# short of the fake's own 600 s sleep.
HANG_BOUND_S = 2.0
HANG_WALL_CEILING_S = 15.0

NEEDS_BASH = pytest.mark.skipif(
    shutil.which("bash") is None,
    reason="both wrappers are dispatched as `bash <script>`",
)


# -- helpers: transcripts, stubs -------------------------------------------


def _transcript(path, lines):
    """The JSONL body `_session` writes, at a path of the caller's choosing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    return path


def _answered(text):
    """A whole transcript of a run that finished its turn with `text`."""
    return [_user("fix the parser"), _assistant(text)]


def _final_text(session):
    """The text the terminal message of a written transcript carries."""
    last = json.loads(session.read_text(encoding="utf-8").splitlines()[-1])
    return last["message"]["content"][0]["text"]


def _quoted(path):
    """A path as one shell word, in the slash form Git Bash also accepts."""
    return shlex.quote(Path(path).as_posix())


def _capture_flags(names):
    """sh that walks "$@" and leaves each named flag's value in a variable.

    A stub answering for a flag has to find it wherever the adapter put it, so
    nothing here depends on the order the flags arrive in.
    """
    lines = ['%s=""' % name for name in names]
    lines.append('while [ "$#" -gt 0 ]; do')
    lines.extend('  if [ "$1" = "-%s" ]; then %s="$2"; fi' % (name, name) for name in names)
    lines.extend(["  shift", "done"])
    return lines


def _shell_stub(path, lines):
    """Write a stub the harness runs as `bash <path>`; no shebang is needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_qwen_stub(home, argv_file, session_dir_file, stderr_line=QWEN_IDENTITY):
    """A stand-in for qwen-run.sh: it records what it was handed, fills the `-o`
    file and prints one line on stderr, the way the real wrapper announces
    itself. The line is the announcement unless a case hands in another."""
    lines = [
        f'printf "%s\\n" "$@" > {_quoted(argv_file)}',
        f'printf "%s\\n" "$PI_CODING_AGENT_SESSION_DIR" > {_quoted(session_dir_file)}',
        *_capture_flags(["o"]),
        f'if [ -n "$o" ]; then printf "%s\\n" {shlex.quote(WRAPPER_NOISE)} > "$o"; fi',
        f'printf "%s\\n" {shlex.quote(stderr_line)} >&2',
        "exit 0",
    ]
    return _shell_stub(home / QWEN_SCRIPT, lines)


def _write_sonnet_stub(home, argv_file, projects_dir, prepared):
    """A stand-in for sonnet-run.sh: it records what it was handed, fills the
    `-o` file, and files a transcript named after the session uuid it was given."""
    lines = [
        f'printf "%s\\n" "$@" > {_quoted(argv_file)}',
        *_capture_flags(["o", "S"]),
        f'if [ -n "$o" ]; then printf "%s\\n" {shlex.quote(WRAPPER_NOISE)} > "$o"; fi',
        f"mkdir -p {_quoted(projects_dir)}",
        f'cp {_quoted(prepared)} {_quoted(projects_dir)}/"$S".jsonl',
        "exit 0",
    ]
    return _shell_stub(home / SONNET_SCRIPT, lines)


# -- helpers: one dispatched attempt ---------------------------------------


def _dispatch_qwen(tmp_path, isolate_home, stderr_line=QWEN_IDENTITY):
    """Run one qwen attempt against the stub wrapper; hand back what it left."""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    isolate_home(home)
    clone = tmp_path / "clone"
    clone.mkdir(exist_ok=True)
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    argv_file = tmp_path / "wrapper-argv.txt"
    session_dir_file = tmp_path / "wrapper-session-dir.txt"
    _write_qwen_stub(home, argv_file, session_dir_file, stderr_line)
    prompt = _prompt_in(tmp_path / "prompts")
    # Three transcripts in the session directory: pi leaves the day's earlier
    # runs beside this one. The two older ones sort first and last by name, one
    # is far bigger than this run's and the other smaller, so neither the name
    # nor the size picks this run's: only the modification time does.
    sessions = attempt / "pi-sessions"
    now = time.time()
    for name, age_s, text in (("0-earliest.jsonl", 1200, LONG_STALE_TEXT),
                              ("z-earlier.jsonl", 600, ASCII_TEXT)):
        stale = _transcript(sessions / name, _answered(text))
        os.utime(stale, (now - age_s, now - age_s))
    fresh = _transcript(sessions / "m-latest.jsonl", _answered(FINAL_TEXT))
    assert (sessions / "0-earliest.jsonl").stat().st_size > fresh.stat().st_size
    settings = _settings(qwen_provider=QWEN_PROVIDER, qwen_model=QWEN_MODEL)
    run = engines.dispatch("qwen", "qwen", prompt, clone, attempt, settings, 120.0)
    return {"run": run, "home": home, "attempt": attempt, "prompt": prompt, "fresh": fresh,
            "argv_file": argv_file, "session_dir_file": session_dir_file, "sessions": sessions}


def _plant_decoys(projects_root):
    """File two transcripts under the projects root that no uuid lookup can hit.

    They sort before and after any uuid4 the wrapper is handed, sit in two
    different project directories, are stamped in the future so they are also
    the newest files under the root, and carry a text shorter than any attempt's.
    """
    ahead = time.time() + 600
    for directory, stem in ((projects_root / "-tmp-clone" / "deep", DECOY_UUIDS[0]),
                            (projects_root / "-other-clone", DECOY_UUIDS[1])):
        decoy = _transcript(directory / (stem + ".jsonl"), _answered(ASCII_TEXT))
        os.utime(decoy, (ahead, ahead))


def _dispatch_sonnet(tmp_path, isolate_home, name="attempt", text=FINAL_TEXT):
    """Run one sonnet attempt against the stub wrapper; hand back what it left."""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    isolate_home(home)
    clone = tmp_path / "clone"
    clone.mkdir(exist_ok=True)
    attempt = tmp_path / name
    attempt.mkdir()
    argv_file = tmp_path / (name + "-argv.txt")
    # Nested two levels down under a directory named for this dispatch alone,
    # the way a real projects root nests a transcript under an encoded project
    # directory: no path written down anywhere reaches it, so only a recursive
    # search by uuid does. The decoys beside it, one of them under the fixed
    # `-tmp-clone/deep` nesting, are there before the wrapper files anything.
    projects_root = home / ".claude" / "projects"
    projects = projects_root / ("-" + uuid.uuid4().hex) / uuid.uuid4().hex[:8]
    _plant_decoys(projects_root)
    prepared = _transcript(tmp_path / (name + "-prepared.jsonl"), _answered(text))
    _write_sonnet_stub(home, argv_file, projects, prepared)
    prompt = _prompt_in(tmp_path / "prompts")
    run = engines.dispatch("sonnet", "sonnet", prompt, clone, attempt,
                           _settings(sonnet_model=SONNET_MODEL), 120.0)
    return {"run": run, "home": home, "attempt": attempt, "prompt": prompt, "clone": clone,
            "argv_file": argv_file, "projects": projects}


def _dispatch_cmd(tmp_path, monkeypatch, command, settings=None, name="attempt",
                  bound_s=120.0):
    """Run one `cmd:` attempt; hand back what it left behind."""
    clone = tmp_path / "clone"
    clone.mkdir(exist_ok=True)
    attempt = tmp_path / name
    attempt.mkdir()
    prompt = _prompt_in(tmp_path / "prompts")
    # The fake engine reads its attempt directory from the environment, so its
    # transcript lands where this attempt looks for one.
    monkeypatch.setenv(ATTEMPT_DIR_ENV, str(attempt))
    run = engines.dispatch("cmd1", command, prompt, clone, attempt,
                           settings if settings is not None else _settings(), bound_s)
    return {"run": run, "attempt": attempt, "clone": clone, "prompt": prompt}


# -- build_argv ------------------------------------------------------------


def test_builds_the_pinned_qwen_argv(tmp_path, isolate_home):
    # Byte for byte: a drifting flag changes what an eval measured, so every
    # element is written out here rather than derived from the settings.
    home = tmp_path / "home"
    home.mkdir()
    isolate_home(home)
    prompt, clone, out = tmp_path / "prompt.md", tmp_path / "clone", tmp_path / "out.txt"

    argv = engines.build_argv("qwen", "qwen", prompt, clone, out,
                              _settings(qwen_provider=QWEN_PROVIDER, qwen_model=QWEN_MODEL),
                              "a3d1c0de-0000-4000-8000-000000000000")

    assert argv == ["bash", str(home / QWEN_SCRIPT), "--approved-only",
                    "-P", QWEN_PROVIDER, "-m", QWEN_MODEL,
                    "-f", str(prompt), "-o", str(out)]


def test_builds_the_pinned_sonnet_argv(tmp_path, isolate_home):
    # The uuid is handed in rather than generated here, so this argv is the
    # whole of the contract and not a shape with one unpredictable element.
    home = tmp_path / "home"
    home.mkdir()
    isolate_home(home)
    prompt, clone, out = tmp_path / "prompt.md", tmp_path / "clone", tmp_path / "out.txt"
    session_uuid = "a3d1c0de-0000-4000-8000-000000000000"

    argv = engines.build_argv("sonnet", "sonnet", prompt, clone, out,
                              _settings(sonnet_model=SONNET_MODEL), session_uuid)

    assert argv == ["bash", str(home / SONNET_SCRIPT), "-y", "-m", SONNET_MODEL,
                    "-d", str(clone), "-f", str(prompt), "-o", str(out),
                    "-S", session_uuid]


# -- dispatch: the qwen adapter --------------------------------------------


@NEEDS_BASH
def test_dispatches_qwen_with_the_pinned_argv_and_its_own_session_directory(
        tmp_path, isolate_home):
    # The wrapper writes down both what it was handed and where it was told to
    # keep its sessions, so the argv and the environment are read back off the
    # child rather than off the caller's own return value alone.
    result = _dispatch_qwen(tmp_path, isolate_home)
    run, attempt = result["run"], result["attempt"]

    assert run["argv"][:9] == ["bash", str(result["home"] / QWEN_SCRIPT), "--approved-only",
                               "-P", QWEN_PROVIDER, "-m", QWEN_MODEL,
                               "-f", str(result["prompt"])]
    assert run["argv"][9] == "-o"
    assert Path(run["argv"][10]) == attempt / "out.txt"
    assert len(run["argv"]) == 11
    assert result["argv_file"].read_text(encoding="utf-8").splitlines() == run["argv"][2:]
    assert result["session_dir_file"].read_text(
        encoding="utf-8").strip() == str(result["sessions"])
    # The newest transcript in that directory is this attempt's; the two older
    # ones beside it, first and last by name and the biggest of the three, carry
    # a different text.
    assert (attempt / "session.jsonl").read_text(encoding="utf-8") == result["fresh"].read_text(
        encoding="utf-8")
    assert run["final_message_bytes"] == len(FINAL_TEXT.encode("utf-8"))


@NEEDS_BASH
def test_scores_a_qwen_run_from_its_announced_identity_and_its_newest_transcript(
        tmp_path, isolate_home):
    # The capture holds the wrapper's diagnostic and the transcript holds the
    # 52-byte answer, so the byte count says the transcript was read. The
    # identity is the announced line itself, not the capture it was found in.
    result = _dispatch_qwen(tmp_path, isolate_home)
    run = result["run"]

    records.validate_record("engine_run", run)
    assert set(run) == set(records.ENGINE_RUN_KEYS)
    assert run["launch"] == "started"
    assert run["exit"] == 0
    assert run["timed_out"] is False
    assert run["wall_s"] > 0
    assert run["identity"] == QWEN_IDENTITY
    assert run["completion"] == "complete"
    assert run["final_message_bytes"] == len(FINAL_TEXT.encode("utf-8"))
    assert run["usage_limit"] == "unchecked"


@NEEDS_BASH
@pytest.mark.parametrize("stderr_line", [QWEN_STDERR_NOISE, *QWEN_WRONG_ANNOUNCEMENTS],
                         ids=["noise-naming-both", "other-pair", "other-provider", "other-model"])
def test_reports_no_qwen_identity_when_the_wrapper_announced_none_or_another_pair(
        tmp_path, isolate_home, stderr_line):
    # The settings still name a provider and a model, the run still finished,
    # and the wrapper still wrote to stderr - a line that even names both, or
    # a well-formed announcement of some other provider or model. Only the
    # announcement of the configured pair is missing, so an adapter that
    # echoes its settings back, takes any non-empty capture for an identity,
    # or takes any announcement at all, reports one that was never observed.
    result = _dispatch_qwen(tmp_path, isolate_home, stderr_line=stderr_line)

    assert result["run"]["identity"] is None
    assert result["run"]["completion"] == "complete"
    records.validate_record("engine_run", result["run"])


# -- dispatch: the sonnet adapter ------------------------------------------


@NEEDS_BASH
def test_dispatches_sonnet_and_scores_the_transcript_its_own_uuid_names(
        tmp_path, isolate_home):
    # The transcript is filed under a temporary projects root, two directories
    # deep in a directory named for this dispatch alone, under the uuid the
    # wrapper was handed - and nothing else names it. Two decoys sit under the
    # same root, one at the fixed `-tmp-clone/deep` nesting, sorting before and
    # after it, stamped newer than it, each 34 bytes long: the 52-byte answer
    # is only in the file the uuid names.
    result = _dispatch_sonnet(tmp_path, isolate_home)
    run, argv = result["run"], result["run"]["argv"]

    assert argv[:9] == ["bash", str(result["home"] / SONNET_SCRIPT), "-y", "-m", SONNET_MODEL,
                        "-d", str(result["clone"]), "-f", str(result["prompt"])]
    assert argv[9] == "-o"
    assert Path(argv[10]) == result["attempt"] / "out.txt"
    assert argv[11] == "-S"
    assert len(argv) == 13
    assert uuid.UUID(argv[12]).version == 4
    assert result["argv_file"].read_text(encoding="utf-8").splitlines() == argv[2:]
    filed = result["projects"] / ("%s.jsonl" % argv[12])
    assert filed.is_file()
    assert (result["attempt"] / "session.jsonl").read_text(
        encoding="utf-8") == filed.read_text(encoding="utf-8")
    records.validate_record("engine_run", run)
    assert run["launch"] == "started"
    assert run["exit"] == 0
    assert run["wall_s"] > 0
    assert run["completion"] == "complete"
    assert run["final_message_bytes"] == len(FINAL_TEXT.encode("utf-8"))
    assert run["identity"] is not None and SONNET_MODEL in run["identity"]
    assert run["usage_limit"] == "unchecked"


@NEEDS_BASH
def test_gives_every_sonnet_dispatch_a_session_uuid_of_its_own(tmp_path, isolate_home):
    # A reused uuid would find the previous attempt's transcript and score this
    # attempt from it, so two dispatches may not share one - and each is scored
    # from the transcript its own uuid names, which the two texts' sizes tell
    # apart.
    first = _dispatch_sonnet(tmp_path, isolate_home, name="first")
    second = _dispatch_sonnet(tmp_path, isolate_home, name="second", text=SECOND_TEXT)

    first_uuid, second_uuid = first["run"]["argv"][12], second["run"]["argv"][12]
    assert first_uuid != second_uuid
    assert uuid.UUID(first_uuid).version == uuid.UUID(second_uuid).version == 4
    assert first["run"]["final_message_bytes"] == len(FINAL_TEXT.encode("utf-8"))
    assert second["run"]["final_message_bytes"] == len(SECOND_TEXT.encode("utf-8"))


# -- dispatch: the fake engine ---------------------------------------------


def test_scores_a_fake_engine_run_from_the_evidence_it_wrote(tmp_path, monkeypatch):
    # The fake satisfies the same rules through the same evidence: its identity
    # on stderr, its answer in a transcript, its edit in the clone it ran in.
    result = _dispatch_cmd(tmp_path, monkeypatch,
                           eval_harness_fixtures.fake_engine_command("pass"))
    run = result["run"]
    answered = _final_text(result["attempt"] / "session.jsonl")

    records.validate_record("engine_run", run)
    assert run["argv"] == _engine_argv("pass", result["prompt"])
    assert run["argv"][0] == sys.executable
    assert run["launch"] == "started"
    assert run["exit"] == 0
    assert run["timed_out"] is False
    assert run["wall_s"] > 0
    assert run["identity"] == FAKE_IDENTITY
    assert run["completion"] == "complete"
    assert run["final_message_bytes"] == len(answered.encode("utf-8"))
    assert run["usage"] == _expected_usage(input_tokens=412, output_tokens=37)
    assert run["first_edit_s"] is None
    assert run["usage_limit"] == "unchecked"
    # The edit landed in the clone, which is the directory the engine ran in.
    assert (result["clone"] / "calc.py").read_text(
        encoding="utf-8") == eval_harness_fixtures.FIXED_IMPL
    # The fake's final text went to stdout and its announcement to stderr, and
    # each landed in its own capture: the message never reaches wrapper.txt.
    assert (result["attempt"] / "out.txt").read_text(encoding="utf-8").splitlines() == [
        "Fixed add() so the oracle test passes."]
    assert (result["attempt"] / "wrapper.txt").read_text(encoding="utf-8").splitlines() == [
        FAKE_IDENTITY]


def test_reports_no_identity_and_an_incomplete_stream_for_a_silent_fake_run(
        tmp_path, monkeypatch):
    # The silent mode announces nothing and its transcript ends on "length": the
    # run exited 0 and edited the tree, and neither of those is evidence enough.
    result = _dispatch_cmd(tmp_path, monkeypatch,
                           eval_harness_fixtures.fake_engine_command("silent-edit"))
    run = result["run"]

    records.validate_record("engine_run", run)
    assert run["launch"] == "started"
    assert run["exit"] == 0
    assert run["identity"] is None
    assert run["completion"] == "incomplete"


def test_splits_cmd_captures_by_stream_not_by_line_shape(tmp_path, monkeypatch):
    # The child prints an announcement-shaped line on STDOUT and a warning on
    # STDERR. Each capture holds what its stream carried: the look-alike stays
    # in out.txt, the warning in wrapper.txt, and no identity was announced
    # where one is looked for - a splitter sorting lines by what they look
    # like would swap the two and report an identity never given on stderr.
    script = tmp_path / "noisy.py"
    script.write_text(
        "import sys\n"
        "print(\"Using engine 'cmd:noisy'\")\n"
        "print('warning: slow', file=sys.stderr)\n",
        encoding="utf-8",
    )

    result = _dispatch_cmd(tmp_path, monkeypatch, "cmd:" + str(script))
    run = result["run"]

    records.validate_record("engine_run", run)
    assert run["exit"] == 0
    assert (result["attempt"] / "out.txt").read_text(encoding="utf-8").splitlines() == [
        "Using engine 'cmd:noisy'"]
    assert (result["attempt"] / "wrapper.txt").read_text(encoding="utf-8").splitlines() == [
        "warning: slow"]
    assert run["identity"] is None


def test_stops_a_hung_fake_run_at_the_bound_and_reaps_what_it_spawned(tmp_path, monkeypatch):
    # The hang mode announces itself, starts a heartbeat child and sleeps for
    # ten minutes. The bound fires long before that: the run is marked timed
    # out with no exit of its own, its wall time is the bound plus a reap, and
    # the heartbeat it left behind is dead by the time dispatch returns.
    heartbeat = tmp_path / "beat.txt"
    monkeypatch.setenv(HEARTBEAT_ENV, str(heartbeat))

    result = _dispatch_cmd(tmp_path, monkeypatch,
                           eval_harness_fixtures.fake_engine_command("hang"),
                           bound_s=HANG_BOUND_S)
    run = result["run"]

    records.validate_record("engine_run", run)
    assert run["launch"] == "started"
    assert run["timed_out"] is True
    assert run["exit"] is None
    assert HANG_BOUND_S <= run["wall_s"] < HANG_WALL_CEILING_S
    # The heartbeat was beating before the bound fired, and is not any more.
    assert heartbeat.is_file()
    assert _stopped_growing(heartbeat)


# -- dispatch: the usage-limit checker -------------------------------------


@pytest.mark.parametrize("exit_code, verdict",
                         [(0, "hit"), (1, "clear"), (2, "clear")],
                         ids=["exit-0-is-limit-stuck", "exit-1-is-clear", "exit-2-is-clear"])
def test_reads_the_usage_limit_checker_the_way_the_checker_answers(
        tmp_path, monkeypatch, exit_code, verdict):
    # The checker prints a reset epoch and exits 0 when the account is STUCK, so
    # the intuitive reading of an exit code is the wrong one here.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    argv_file = tmp_path / "checker-argv.txt"
    checker = eval_harness_fixtures.write_argv_recording_stub(
        bin_dir, "usage-limit-check", argv_file, exit_code=exit_code, stdout="1900000000")

    result = _dispatch_cmd(tmp_path, monkeypatch,
                           eval_harness_fixtures.fake_engine_command("pass"),
                           settings=_settings(usage_limit_cmd=checker))

    assert result["run"]["usage_limit"] == verdict
    recorded = argv_file.read_text(encoding="utf-8").splitlines()
    assert "--log" in recorded
    assert Path(recorded[recorded.index("--log") + 1]) == result["attempt"] / "out.txt"
    records.validate_record("engine_run", result["run"])


def test_leaves_usage_limit_unchecked_when_the_configured_checker_is_not_there(
        tmp_path, monkeypatch):
    # A checker that cannot be run observed nothing, and nothing observed is
    # neither "clear" nor "hit".
    result = _dispatch_cmd(tmp_path, monkeypatch,
                           eval_harness_fixtures.fake_engine_command("pass"),
                           settings=_settings(usage_limit_cmd=tmp_path / "no-such-checker"))

    assert result["run"]["usage_limit"] == "unchecked"
    records.validate_record("engine_run", result["run"])


# -- dispatch: what launched and what did not ------------------------------


def test_records_a_no_launch_attempt_whole_with_null_measurements(tmp_path, monkeypatch):
    # Nothing was created, so nothing was measured - but the attempt still has
    # to be scoreable, which means the whole block is written anyway.
    result = _dispatch_cmd(tmp_path, monkeypatch, "cmd:" + str(tmp_path / "no-such-engine"))
    run = result["run"]

    records.validate_record("engine_run", run)
    assert run["launch"] == "not-started"
    assert run["argv"] != []
    assert run["exit"] is None
    assert run["timed_out"] is False
    assert run["wall_s"] is None
    assert run["identity"] is None
    assert run["completion"] == "unknown"
    assert run["final_message_bytes"] is None
    assert run["first_edit_s"] is None
    assert run["usage"] == dict.fromkeys(records.USAGE_KEYS)
    assert run["usage_limit"] == "unchecked"
    # No child, no stdout: a refused launch leaves no capture behind.
    assert not (result["attempt"] / "out.txt").exists()


def test_records_a_created_process_as_started_even_when_the_engine_never_ran(
        tmp_path, monkeypatch):
    # The interpreter exists and was created; the script it was pointed at does
    # not. Only a pre-creation failure may be blamed on the harness, so this is
    # a started run that failed rather than a launch that never happened.
    result = _dispatch_cmd(tmp_path, monkeypatch, "cmd:" + str(tmp_path / "absent_engine.py"))
    run = result["run"]

    records.validate_record("engine_run", run)
    assert run["launch"] == "started"
    assert run["exit"] is not None and run["exit"] != 0
    assert run["identity"] is None
    assert run["completion"] == "unknown"
