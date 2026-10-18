## 1: Add keep guard to empty_old_trash so a run never deletes the batch it just trashed

- The test file is skills/purge-devtmp/scripts/test_purge_devtmp.py. The dispatch named only the module `purge_devtmp`.
- Test 1 uses a top-level `old.txt` rather than the nested path from `test_apply_moves_to_trash_and_records_manifest`. The dispatch asks only for "one artifact aged past the window".
- Batch names are built with `time.strftime("%Y-%m-%d", time.localtime(now - days * gc.DAY))`, the same way the existing test builds today's batch name.
- Each batch dir holds one file, so the test proves a batch with contents gets removed, not just an empty dir.
- Test 2 does not cover the case where `keep` names an expired batch. At days=30, today's batch survives with or without `keep`. Test 1 is the test that proves the guard works.
- Test 2 now pins `now` to local noon today, not `time.time()`. A batch's age counts from local midnight of its date, so noon keeps every age half a day off a whole number. That keeps the 29/31 boundary stable near midnight and across daylight-saving changes. The original assertions are unchanged.
- The original test 1 run must report `trash-batches-emptied=0`, and point 5 needs `=1`. One run cannot satisfy both, so I put the seeded-old-batch case in a second store inside the same test.
- A batch can't share a name, and so an age, with the kept one. For point 4, "non-kept batch of the same age" is the 3-day batch next to the kept 2-day batch, both past the 1-day window.
- I used nested `seed` and `present` helpers inside test 2 to keep it under 50 lines. I added no module-level helpers.
