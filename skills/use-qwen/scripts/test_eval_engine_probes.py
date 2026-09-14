"""Tests for eval_harness/engines.py: version probes, server_root and /props."""
import http.server
import json
import os
import random
import socket
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import pytest

import eval_harness_fixtures
import run_eval_harness
from eval_harness import engines
from eval_harness import records
from eval_harness_engine_helpers import QWEN_MODEL, QWEN_PROVIDER, SONNET_MODEL, _settings

# `scratch` and `vetted` are fixtures the one run-driver case below resolves by name.
from eval_harness_run_helpers import (
    _copy,
    _map_provider,
    _run_argv,
    _stub_dispatch,
    scratch,
    vetted,
)

# What the two version probes answer. Neither string can reach a record unless
# that probe was actually run.
PI_VERSION = "pi 0.42.7"
CLAUDE_VERSION = "2.1.117 (Claude Code)"

# The password half of a provider URL's userinfo, which no record may repeat.
MUST_NOT_LEAK = "hunter2-never-in-a-record"

# The sampling block the mock's sanitized /props payload reports.
MOCK_SAMPLING = {"temperature": 0.7, "top_k": 20, "top_p": 0.8, "min_p": 0.0}

# One provider entry as pi's models.json spells it; its baseUrl is what a probe must use.
PROVIDER_ENTRY = {"baseUrl": "http://127.0.0.1:9/v1", "api": "openai-completions", "apiKey": "none"}

# The three provider URL shapes a /props fetch has to reduce to one root.
PROVIDER_SUFFIXES = pytest.mark.parametrize("suffix", ["/v1", "/v1/", ""],
                                            ids=["v1", "v1-slash", "bare"])

MOCK_SERVER = Path(__file__).resolve().parent / "mock-llama-server.py"


# -- helpers: the servers ---------------------------------------------------


def _no_network(*args, **kwargs):
    raise AssertionError("this run must not open a network connection")


def _free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _wait_until_listening(port, deadline_s=30.0):
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), 0.25):
                return
        except OSError:
            time.sleep(0.05)
    raise AssertionError("the mock server never listened on port %d" % port)


@pytest.fixture(scope="module")
def props_server(tmp_path_factory):
    """The shared mock llama.cpp server, on a port of its own.

    It is the same script the two shell suites drive, so the payload these cases
    read is the one route they all share rather than a fixture of their own.
    """
    mode_file = tmp_path_factory.mktemp("mock") / "mode.txt"
    mode_file.write_text("ok", encoding="utf-8")
    port = _free_port()
    server = subprocess.Popen(
        [sys.executable, str(MOCK_SERVER), str(port), str(mode_file), "mock-candidate"],
        stdin=subprocess.DEVNULL,
    )
    try:
        _wait_until_listening(port)
        yield "http://127.0.0.1:%d" % port
    finally:
        server.terminate()
        server.wait(timeout=30)


def _random_props():
    """A real-shape /props payload whose values no constant in this file can
    predict: a fetch that answers from remembered numbers cannot match it, so
    the body has to have been read off the wire."""
    return {
        "default_generation_settings": {
            "n_ctx": random.choice([8192, 16384, 32768, 65536, 262144]) + random.randint(1, 4095),
            "params": {"temperature": round(random.uniform(0.05, 1.5), 3),
                       "top_k": random.randint(1, 99),
                       "top_p": round(random.uniform(0.5, 0.99), 3),
                       "min_p": round(random.uniform(0.01, 0.2), 3)},
        },
        "model_alias": "alias-" + uuid.uuid4().hex[:12],
        "build_info": "b" + uuid.uuid4().hex[:8],
        "chat_template_caps": {"supports_reasoning_effort": random.choice([True, False])},
    }


@pytest.fixture
def owned_props_server():
    """A loopback server this test owns: it answers `/props` with a payload the
    test chose and writes down every path it was asked for.

    The shared mock serves one fixed payload, so a fetch that never reads a body
    can still repeat the mock's numbers; this one serves numbers of its own.
    """
    payload = _random_props()
    paths = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            """Keep the per-request log off the test's stderr."""
            return None

        def do_GET(self):
            paths.append(self.path)
            if self.path.rstrip("/") == "/props":
                code, body = 200, json.dumps(payload).encode("utf-8")
            else:
                code, body = 404, b"{}"
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield {"url": "http://127.0.0.1:%d" % server.server_address[1],
               "payload": payload, "paths": paths}
    finally:
        server.shutdown()
        server.server_close()


def _served_block(payload, declared):
    """The server block a fetch has to report after reading `payload`."""
    settings = payload["default_generation_settings"]
    return {"n_ctx": settings["n_ctx"],
            "model_alias": payload["model_alias"],
            "build_info": payload["build_info"],
            "sampling": settings["params"],
            "supports_reasoning_effort": payload["chat_template_caps"]["supports_reasoning_effort"],
            "declared_effort": declared,
            "metadata_error": None}


@pytest.fixture
def connections(monkeypatch):
    """Every address this process connects to during the test, on the way through.

    A fetch that answers from constants never opens a socket, so the port the
    mock listens on has to show up here before any value it "read" counts.
    """
    seen = []
    real_connect = socket.socket.connect

    def connect(sock, address, *args):
        seen.append(address)
        return real_connect(sock, address, *args)

    monkeypatch.setattr(socket.socket, "connect", connect)
    return seen


def _reached(connections, server_url):
    """True when some connection went to the port the server URL names."""
    port = urlsplit(server_url).port
    return any(isinstance(address, tuple) and address[1] == port for address in connections)


# -- record_versions -------------------------------------------------------


@pytest.mark.parametrize("engine_ids, probes_pi, probes_claude",
                         [(["qwen"], True, False),
                          (["sonnet"], False, True),
                          (["qwen", "sonnet"], True, True),
                          (["cmd1", "cmd2"], False, False)],
                         ids=["qwen-only", "sonnet-only", "both", "fake-only"])
def test_probes_a_version_only_for_the_engines_the_run_uses(
        tmp_path, monkeypatch, engine_ids, probes_pi, probes_claude):
    # A fake-only run has to work on a host with neither CLI installed and no
    # server reachable, so it may run no probe and open no connection at all.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    pi_argv, claude_argv = tmp_path / "pi-argv.txt", tmp_path / "claude-argv.txt"
    eval_harness_fixtures.write_argv_recording_stub(bin_dir, "pi", pi_argv, stdout=PI_VERSION)
    eval_harness_fixtures.write_argv_recording_stub(bin_dir, "claude", claude_argv,
                                                    stdout=CLAUDE_VERSION)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    monkeypatch.setattr(socket.socket, "connect", _no_network)

    versions = engines.record_versions(engine_ids, _settings(qwen_provider=QWEN_PROVIDER,
                                                             qwen_model=QWEN_MODEL,
                                                             sonnet_model=SONNET_MODEL))

    assert set(versions) == {"pi", "claude"}
    assert pi_argv.exists() is probes_pi
    assert claude_argv.exists() is probes_claude
    if probes_pi:
        assert pi_argv.read_text(encoding="utf-8").splitlines() == ["--version"]
        assert PI_VERSION in versions["pi"]
    else:
        assert versions["pi"] is None
    if probes_claude:
        assert claude_argv.read_text(encoding="utf-8").splitlines() == ["--version"]
        assert CLAUDE_VERSION in versions["claude"]
    else:
        assert versions["claude"] is None


def test_records_a_null_version_when_the_probed_cli_is_not_installed(tmp_path, monkeypatch):
    # A host without pi cannot answer `pi --version`; the run still has to be
    # recorded, so the probe that found nothing reports null and raises nothing.
    empty_bin = tmp_path / "empty-bin"
    empty_bin.mkdir()
    monkeypatch.setenv("PATH", str(empty_bin))
    monkeypatch.setattr(socket.socket, "connect", _no_network)

    versions = engines.record_versions(["qwen"], _settings(qwen_provider=QWEN_PROVIDER,
                                                           qwen_model=QWEN_MODEL))

    assert versions == {"pi": None, "claude": None}


# -- server_root -----------------------------------------------------------


@pytest.mark.parametrize("provider_url, expected",
                         [("http://h:8002/v1", "http://h:8002"),
                          ("http://h:8002/v1/", "http://h:8002"),
                          ("http://h/proxy/v1/", "http://h/proxy"),
                          ("http://h/v1/v1", "http://h/v1"),
                          ("http://h:8002", "http://h:8002"),
                          ("http://h:8002/", "http://h:8002")],
                         ids=["v1", "v1-slash", "proxy-path", "two-v1", "bare", "bare-slash"])
def test_strips_exactly_one_trailing_v1_from_a_provider_url(provider_url, expected):
    # One component, and only a trailing one: a proxy path above it is part of
    # the address, and a URL that never named /v1 keeps all but its slash.
    assert engines.server_root(provider_url) == expected


# -- resolve_provider_url --------------------------------------------------


def _write_models(path, doc):
    """`doc` as `path`: a JSON document, or a raw string for a file that is not one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = doc if isinstance(doc, str) else json.dumps(doc)
    path.write_text(text, encoding="utf-8")


def test_resolves_a_provider_name_to_the_base_url_configured_under_the_agent_dir(
        tmp_path, monkeypatch):
    # The name is what qwen-run.sh -P takes; the URL behind it lives in the
    # models.json of the directory $PI_CODING_AGENT_DIR names.
    _write_models(tmp_path / "agent" / "models.json",
                  {"providers": {"qwen-eval-provider": PROVIDER_ENTRY}})
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(tmp_path / "agent"))

    assert engines.resolve_provider_url("qwen-eval-provider") == "http://127.0.0.1:9/v1"


def test_resolves_a_provider_name_from_the_home_agent_dir_when_none_is_set(
        tmp_path, monkeypatch, isolate_home):
    # Without the variable the file is ~/.pi/agent/models.json, under this
    # test's home - never the developer's.
    isolate_home(tmp_path)
    monkeypatch.delenv("PI_CODING_AGENT_DIR", raising=False)
    _write_models(tmp_path / ".pi" / "agent" / "models.json",
                  {"providers": {"qwen-eval-provider": PROVIDER_ENTRY}})

    assert engines.resolve_provider_url("qwen-eval-provider") == "http://127.0.0.1:9/v1"


@pytest.mark.parametrize("models", [
    None,
    "{not json",
    "[]",
    {"providers": []},
    {"providers": {"some-other-provider": PROVIDER_ENTRY}},
    {"providers": {"qwen-eval-provider": "http://127.0.0.1:9/v1"}},
    {"providers": {"qwen-eval-provider": None}},
    {"providers": {"qwen-eval-provider": dict(PROVIDER_ENTRY, baseUrl="")}},
    {"providers": {"qwen-eval-provider": dict(PROVIDER_ENTRY, baseUrl=42)}},
], ids=["missing-file", "malformed-json", "document-not-an-object", "providers-not-an-object",
        "provider-absent", "provider-entry-a-string", "provider-entry-null", "base-url-empty",
        "base-url-not-a-string"])
def test_answers_none_instead_of_raising_when_no_base_url_is_configured(
        tmp_path, monkeypatch, models):
    # A run with an unresolved provider still has to be recorded, so the
    # resolver reports nothing rather than failing the run over its config.
    (tmp_path / "agent").mkdir()
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(tmp_path / "agent"))
    if models is not None:
        _write_models(tmp_path / "agent" / "models.json", models)

    assert engines.resolve_provider_url("qwen-eval-provider") is None


# -- fetch_server_props ----------------------------------------------------


@pytest.mark.parametrize("declared", ["xhigh", None], ids=["declared", "unset"])
def test_reads_the_server_block_from_a_v1_provider_url(props_server, connections, declared):
    # The provider URL ends in /v1 and the server answers /props only, so a
    # request to /v1/props reaches a 404 and reports nothing. The values are
    # the mock's, and the mock has to have been asked for them: a fetch that
    # never connected to its port read nothing. The declared effort is the
    # operator's own label: it is carried and never verified, while what the
    # server says about supporting one is reported separately.
    record = engines.fetch_server_props(props_server + "/v1", declared)

    assert _reached(connections, props_server)
    records.validate_record("server", record)
    assert set(record) == set(records.SERVER_KEYS)
    assert record["n_ctx"] == 131072
    assert record["model_alias"] == "mock-candidate"
    assert record["build_info"] == "mock-b0000"
    assert record["sampling"] == MOCK_SAMPLING
    assert record["supports_reasoning_effort"] is True
    assert record["declared_effort"] == declared
    assert record["metadata_error"] is None


@PROVIDER_SUFFIXES
@pytest.mark.parametrize("declared", ["xhigh", None], ids=["declared", "unset"])
def test_reports_the_values_the_server_actually_served(owned_props_server, suffix, declared):
    # This server answers /props with numbers drawn for this test alone, so the
    # only way to report them is to read the body it sent: a 200 status and a
    # remembered payload look the same on the mock and different here. It also
    # writes down what it was asked for, which has to be /props at the root
    # whatever the provider URL's tail - never /v1/props.
    record = engines.fetch_server_props(owned_props_server["url"] + suffix, declared)

    assert set(owned_props_server["paths"]) == {"/props"}
    records.validate_record("server", record)
    assert record == _served_block(owned_props_server["payload"], declared)


def test_reports_null_metadata_with_a_diagnostic_when_props_is_unavailable(
        props_server, connections):
    # A live server that serves no /props under the root this URL implies: the
    # run still has to be recordable, so every value is null and the reason is
    # kept beside them. The server was asked, and answered with the 404 the
    # diagnostic reports; nothing here is decided from the URL's shape alone.
    record = engines.fetch_server_props(props_server + "/v1/models", "xhigh")

    assert _reached(connections, props_server)
    records.validate_record("server", record)
    assert isinstance(record["metadata_error"], str) and record["metadata_error"]
    assert record["declared_effort"] == "xhigh"
    assert [record[key] for key in records.SERVER_KEYS[:5]] == [None] * 5


@pytest.mark.parametrize("tail, served", [("/v1", True), ("/v1/models", False)],
                         ids=["props-served", "props-unavailable"])
def test_keeps_a_credential_out_of_the_server_record(owned_props_server, tail, served):
    # An operator's provider URL can carry a password. The fetch still reaches
    # the server the URL names and reads the metadata it served - this test's
    # own numbers, not the mock's - and nothing stored may repeat the password:
    # not a value, and not the diagnostic a 404 leaves behind either.
    url = owned_props_server["url"].replace("http://", "http://evaluser:%s@" % MUST_NOT_LEAK)

    record = engines.fetch_server_props(url + tail, "xhigh")

    assert owned_props_server["paths"]
    records.validate_record("server", record)
    if served:
        assert record == _served_block(owned_props_server["payload"], "xhigh")
    else:
        assert isinstance(record["metadata_error"], str) and record["metadata_error"]
        assert [record[key] for key in records.SERVER_KEYS[:5]] == [None] * 5
    assert MUST_NOT_LEAK not in json.dumps(record)


# -- the run driver: a named provider reaches its configured server ---------


def test_a_qwen_run_reads_props_from_the_url_its_provider_name_resolves_to(
        tmp_path, monkeypatch, props_server, connections, vetted):
    # The run is given a provider NAME, and the mock listens on a port only
    # models.json knows: the block run.json records can only be the mock's if
    # the probe went to the URL configured for that name. The version probes
    # are stubbed out and the engine never launched, so the fetch is the one
    # thing here that opens a connection.
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    _map_provider(monkeypatch, tmp_path / "agent", "qwen-eval-provider", props_server + "/v1")
    monkeypatch.setattr(engines, "record_versions",
                        lambda ids, settings: {"pi": None, "claude": None})
    _stub_dispatch(monkeypatch)

    rc = run_eval_harness.main(_run_argv(
        root, "props", ["qwen"], "description", "--qwen-provider", "qwen-eval-provider",
        "--qwen-model", "m",
    ))

    run = json.loads((root / "runs" / "props" / "run.json").read_text(encoding="utf-8"))
    assert rc == 0
    assert _reached(connections, props_server)
    records.validate_record("run", run)
    assert run["server"] == {"n_ctx": 131072, "model_alias": "mock-candidate",
                             "build_info": "mock-b0000", "sampling": MOCK_SAMPLING,
                             "supports_reasoning_effort": True, "declared_effort": None,
                             "metadata_error": None}
    assert run["config"]["qwen_provider"] == "qwen-eval-provider"
