# SDD ledger — plan: docs/superpowers/plans/2026-10-26-mahid-lite-scoring.md

## Identity and scope

- User goal: finish R1–R6/R10; paperporo already complete. Root owns MAHID, demo Coder owns demo independently.
- MAHID checkout: E:/company_work/MAHID五类人才评测, base main@69097146d1df09db97a53a62dce59fcbb0c7a33e.
- Current branch: feat/1019-lite-scoring in the same compatible primary worktree. No new worktree.
- Ruling: reuse the primary checkout and create a feature branch in place — global worktree freshness/reuse rules take precedence over a generic skill's new-worktree preference.
- Ruling: use this durable progress note and native file tools — shell-authored helper ledgers conflict with PC2 file-writing rules.

## Evidence and frontier

- Original baseline: 10 unittest tests passed using E:/Anaconda3/envs/rag-env/python.exe.
- Task 1 scoring: missing module RED → 9 GREEN; independent reviewer verified exact original bank/TYPE_INFO and 100 legacy comparisons with zero core-metric differences.
- Accepted reviewer P2: legacy close-score reason retained new threshold; added fixed-seed gap=1 RED, corrected legacy explanation, now GREEN.
- Task 2 API: original 404 RED → selection, snapshot, strict answers, ownership, stats, upgrade and retry GREEN.
- Concrete discovered storage risk: sqlite connection context committed without closing, causing reproducible Windows file locks. graft callers showed all callers use with; focused close/commit RED → contextmanager close GREEN, original auth/PDF regression passed.
- Latest API and PDF evidence: 19 tests passed after latest-result, lite PDF, metadata and mixed-conclusion additions.
- Synthetic command: scripts/validate_assessment.py --synthetic passed 100 distribution/30 noisy coherent profile pairs; median score spread 46, strength counts 27/26/47, leading direction agreement 100%. These are constructed diagnostic samples only.
- Production database inspected read-only: 0 saved results, no existing real-user sample set.
- Frontend Coder delivered HTML/tests; root now owns final frontend/backend/PDF acceptance. Full suite53 passed; independent final review accepted fixes for instructor late-response identity, old-bank upgrade, legacy PDF shares, and completed-result retry after bank update.
- Chrome acceptance passed: 12 lite questions, retry after network interruption, four blocks/3 traits, 32-question upgrade with no overlap (44 total), complete full report, teacher stats and CSV, exact current-result PDF. Mobile emulation width390/scroll390; no page errors.
- Browser QA used only E:/codex-acceptance/mahid-1019/qa.db on127.0.0.1:8017. All owned lifetime turns v1/v2/v3/v4 were cancelled with terminal/quiescent evidence. Final v4 turn_ed1b5c2a74cd4e1d9eac7722e9969cdd/PID52548 served the current-source PDF re-export; exact handles remain under E:/codex-acceptance/lifetime.
- demo Coder owns its separate isolated backend18080. Initial .env override incident was fixed by process-env precedence, proven test rows were backed up and precisely removed, independently checked. Do not reuse any earlier demo service handle in this ledger; owner supplies current runtime readback before QA.
- Validation import rejects out-of-range legacy question indexes (RED→GREEN); 3 diagnostic-input tests passed. CLI outputs aggregate data only, without names or answers.
- User clarified acceptance: use equal-scale simulated data; real samples/physical-phone access do not block this delivery. Synthetic scope remains explicit.
- PDF visual QA found split feature heading and footer-only third page. Sections now remain together, redundant timestamp removed, spacing adjusted; actual Chromium output is2 pages for the full QA sample, all modules retained and every page visually checked.

## Current Why chain

Service-owned versioned scoring and immutable selections → preserve question/answer/algorithm identity across save and upgrade → make lite/full results traceable and comparable → users finish both versions and continue without repeating answered questions.

## Completion boundary

MAHID implementation and simulated acceptance are complete; final current-source PDF UI re-export and all owned-service cleanup passed. Overall two-project goal remains active while demo real browser acceptance and independent review fixes continue. Requirement evidence is in docs/acceptance/2026-10-26-mahid.md; no deployment or main merge is implied.
