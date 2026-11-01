# Assumption ledger

Per-plan. Current plan: 00161-migration-publisher-reports-false-success-v1.

## 1: Fix upload() exit-code/HTTP-status check in confluence_attach.py

Tess (test author):
- The brief said "FAIL: line names the exit code 23" and "message naming curl" without pinning the exact print format, so I asserted substring containment ("FAIL" and "23" present; "curl" present) rather than an exact string, to avoid inventing a contract the implementer must match verbatim.
- Passed a literal token string directly to `upload()` as the `token` positional argument (distinct from the module's `ENV["CONFLUENCE_TOKEN"]`) since `upload()`'s signature takes `token` explicitly; this is the most direct way to prove it is never printed.
- Added one extra case (`existing={"a.png": "99"}` -> "Updated" wording) beyond the five enumerated test cases, to cover the DEVON-PROOF requirement that a passed argument (the `existing` dict) must be proven to reach the function's logic; this did not require assuming any new interface, since the `upload()` source and its `existing.get(filename)` branch were already given verbatim in the brief.

Ivan (implementor), initial dispatch:
- The exact failure-message wording was unconstrained by the tests beyond requiring "FAIL"/"23"/"curl" substrings, so a format consistent with the existing "OK: ..." message style was chosen.

Ivan, retry dispatch (os.devnull contract fix): none.

## 2: Escape filenames in image_tag() in confluence_embed_images.py

Tess (test author):
- The tag fragment uses undeclared `ac:`/`ri:` prefixes, so I wrap it in a synthetic root element declaring `xmlns:ac="ac-ns" xmlns:ri="ri-ns"` before calling `ET.fromstring`, which is a reasonable parse harness, not a production shape.
- For the main()-level backslash test, I built a page body containing a `note` macro whose body mentions the stem `a\b` (matching the image filename `a\b.png`'s stem) so the existing note-macro-match regex finds it; this exercises the literal-replacement requirement end to end via `main()`.
- No ambiguity found in the contract itself (field names, escaping function, call shape were all given verbatim in the PRD), so no blockers were raised.

Ivan (implementor), initial dispatch: none stated — but the dispatch only hand-escaped `&`/`"` and missed `<`/`>`, caught in review and corrected in the retry dispatch below (not an invented-ambiguity assumption, a missed Contract line).

Ivan, retry dispatch (quoteattr for full XML escaping): none — quoteattr's automatic quote-character selection was verified against each test case and matches expected XML semantics; no ambiguity required a guess.
