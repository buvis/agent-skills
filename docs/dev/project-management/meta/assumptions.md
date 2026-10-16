# Assumptions ledger: 00077-docket-never-raises-v1

## 1: Widen the proposals-dir read guard and validate the batch shape

- (Tess) The latin-1 sibling test uses a complete record named `cafe-note` with file `cafe-note.md`, and the sibling holds `"caf\xe9 body\n"` encoded as latin-1.
- (Tess) The missing-`file` test also writes a sibling `.md` file, so the fault under test is only the missing key.
- (Tess) The object top-level test uses `{"name": "x"}`.

## 2: Guard the queue write in the save, decide and start verbs

- (Tess) `_proposal(line_no=1)` replaces the brief's `_proposal(1)`: `make_proposal`'s first positional argument is `transcript`, so `_proposal(1)` would not build the `t.jsonl:1` entry.
- (Tess) The save test's proposals-dir record is `gear-note` at line 2, so it does not collide with the seeded line-1 entry.
- (Tess) The decide test patches the write only after seeding and makes no `start` call first.
- (Qwen) `main()` grew to 56 lines under the per-call-site prescription; the step-5.65 style fix (5b341be) moved the decide verb into `_decide_verb`.
