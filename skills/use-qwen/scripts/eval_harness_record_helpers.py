"""Contract-valid run, pretask, sealed and server record builders.

Shared by test_eval_records (its `sample()`) and eval_harness_evidence_helpers
(its `_build_run`). It imports from neither: eval_harness_evidence_helpers
already imports from test_eval_records, so a builder there would close a cycle.
Every builder takes `**over` and updates its base, the `attempt(**over)` pattern.
"""


def server_record(**over):
    """A server block for a run without qwen: every field null is in-domain."""
    base = {"n_ctx": None, "model_alias": None, "build_info": None, "sampling": None,
            "supports_reasoning_effort": None, "declared_effort": None, "metadata_error": None}
    base.update(over)
    return base


def run_record(**over):
    """A run of one cmd engine over one single-file task, no qwen server."""
    base = {
        "schema_version": 1,
        "run_id": "r1",
        "started": "2026-09-13T12:00:00Z",
        "config": {"run_id": "r1", "engines": ["cmd:fake pass"], "shape": "description",
                   "bound": 30.0, "gate_bound": 1800.0, "alternate": False,
                   "retry_discarded": "none", "server_reasoning_effort": None,
                   "qwen_provider": None, "qwen_model": None, "sonnet_model": None,
                   "usage_limit_cmd": None},
        "engines": [{"id": "cmd1", "command": "cmd:fake pass"}],
        "tasks": [{"id": 1, "slug": "calc", "repo": "/tmp/eval-harness/fixture",
                   "kind": "single-file", "writable": ["calc.py"], "oracle": ["test_calc.py"],
                   "prompt_sha256": "a" * 64}],
        "versions": {"pi": None, "claude": None},
        "server": server_record(),
    }
    base.update(over)
    return base


def pretask_record(**over):
    """The sealed template: one hashed writable path, one absent oracle path."""
    base = {"head_sha": "0123456789abcdef0123456789abcdef01234567",
            "writable": {"calc.py": "b" * 64},
            "oracle": {"test_calc.py": "absent"}}
    base.update(over)
    return base


def sealed_record(**over):
    """Same shape as pretask: the tree an attempt left behind."""
    return pretask_record(**over)
