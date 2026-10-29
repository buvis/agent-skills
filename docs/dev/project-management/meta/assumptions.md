# Assumption ledger

Per-plan. Current plan: 00104-sweep-overruns-process-deadline-v1.

## 1: Propagate deadline through sweep scan and control verification; terminate search subprocess trees at expiry

Step-7 regression-fix dispatch (test_sweep_resolvers.py):

- `Path.glob("*.py")` on `Path(sweep.__file__).parent` is the intended way to compute "module names that exist as `.py` files" there; it also sweeps in `sweep` itself and the sibling `test_*.py` names, which is harmless since `sweep.py` imports none of them.
- Comment wording for both repaired tests was the implementor's; the instruction specified the content, not the exact text.

Earlier dispatches for this task ran in a session that was rotated at the context cap; their `ASSUMPTIONS:` lines were not carried over.
