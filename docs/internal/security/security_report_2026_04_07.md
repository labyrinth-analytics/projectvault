# Security Report -- 2026-04-07

**Agent:** Brock (Automated Security Agent)
**Posture:** NEEDS ATTENTION (stable, no new critical/high)
**CVEs found this run:** 0
**New findings:** 1 (SEC-023, INFO)
**Resolved this run:** 0

---

## Summary

Stable session. Today's Ron commit (fbfdd11) is security-positive: the DB discovery
order fix ensures fallback scripts write to Debbie's Mac-backed mount rather than
the ephemeral VM home. No injection vectors introduced. pip-audit clean on both
products. No secrets found in recent diffs. No new BROCK-REVIEW items from Gina's
architecture reports or competitive intel that have not already been assessed. One
new INFO observation (SEC-023) regarding glob sort ambiguity in the new DB discovery
pattern -- low concern in single-user context.

---

## Commits Reviewed (HEAD~2..HEAD and pending commits)

| Hash/Status | Summary                                              | Security Impact |
|-------------|------------------------------------------------------|-----------------|
| fbfdd11     | fix: DB discovery checks mounted paths before VM home | POSITIVE (data safety) |
| fdf6fc3     | documentation updates                                | None (docs only) |
| pending     | Jacqueline PM dashboard + DEBBIE_DASHBOARD corrections | None |
| pending     | John docs: LoreConvo INSTALL.md                       | None (user docs) |
| pending     | Madison: blog_loredocs_vault_architecture fix         | None (content) |
| pending     | Ron: fix MEG-043/044/045: test paths, tool count      | None (tests/docs) |
| pending     | Gina: product review 2026-04-05                       | None (review doc) |
| pending     | Competitive-intel/governance updates                  | None |

---

## Dependency Audit

### LoreConvo (requirements-lock.txt)
```
pip-audit: No known vulnerabilities found
```

### LoreDocs (requirements-lock.txt)
```
pip-audit: No known vulnerabilities found
```

Both products clean. No CVEs this run.

---

## Secrets Scan

- `.env` files found: `ron_skills/sql_query_optimizer/api/.env` (SEC-001, INFO, unchanged)
- `.env` is confirmed NOT tracked in git (`git ls-files` returns empty)
- No history of accidental commitment found
- No hardcoded secrets detected in files changed by today's commits
- No tokens, keys, or credentials appear in the fbfdd11 diff

---

## New Finding: SEC-023

### SEC-023 (INFO): Glob sort ambiguity in DB discovery candidates list

**File:** `ron_skills/loreconvo/scripts/save_to_loreconvo.py` line 49
         `ron_skills/loredocs/scripts/query_loredocs.py` line 57
**Introduced:** fbfdd11 (2026-04-07)
**Issue:** Both scripts now use `sorted(glob.glob("/sessions/*/mnt/..."))` to build
the candidate list for DB discovery. `sorted()` applies lexicographic ordering on
the full path. In the normal case (one Cowork session running), there is exactly one
match and the sort is inconsequential. If Debbie has multiple Cowork sessions open
simultaneously with the same workspace folder mounted, the script picks the
lexicographically first session directory -- which may not be the active session.

**Risk:** Data-routing edge case. Not a vulnerability in the security sense. A stale
or wrong-session DB would cause data to be written to the wrong LoreConvo/LoreDocs
instance -- a data-correctness issue, not a confidentiality/integrity attack.
**Severity:** INFO
**Action:** No immediate fix required. If multi-session confusion becomes a real
problem in practice, consider adding the current session ID to a known environment
variable and using it to pick the exact mount path instead of relying on glob.
**Assigned to:** Ron (low priority, backlog)

---

## BROCK-REVIEW Item Assessment

### BROCK-REVIEW: Marketplace approval readiness
(from competitive_scan_2026_04_04.md -- assess whether current security report
findings would block official marketplace approval)

**Status:** Previously assessed. Summarizing for reference:
- No CRITICAL or HIGH findings are open that would block marketplace approval.
- Open MEDIUM finding: SEC-011 (TOCTOU race in LoreDocs export). Should be fixed
  before v1.0 but does not pose user-facing risk in current local-only deployment.
- Open LOW findings: SEC-006, SEC-016, SEC-019 -- all acceptable for pre-1.0 release.
- Recommendation: Official marketplace submission should wait until SEC-011 is
  resolved. Self-hosted GitHub marketplace launch can proceed with current posture.

### BROCK-REVIEW items from LORECONVO/LOREDOCS architecture reviews
(LORECONVO_architecture_review.md and LOREDOCS_architecture_review.md)

These docs were committed in e43e50d and all BROCK-REVIEW items within them were
assessed across the 2026-04-04 and 2026-04-05 security reports. No new items
requiring re-assessment today. Status:
- FTS5 operator injection: LOW, tracked as open finding. Multi-tenant future scope.
- MCP input validation gap in LoreConvo: LOW, architectural quality issue, not acute.
- vault_import_dir/export path restriction: SEC-018, INFO, deferred.
- At-rest encryption: INFO, deferred to cloud-sync milestone.
- Tier bypass via vault_set_tier: Assessed as adequately mitigated by MCP transport
  isolation in single-user local context. Revisit before multi-user deployment.

---

## Open Findings Register

| ID      | Owner  | Severity | Status | Description                                                    |
|---------|--------|----------|--------|----------------------------------------------------------------|
| SEC-001 | Debbie | INFO     | Open   | Anthropic API key in sql_optimizer .env (local, gitignored)   |
| SEC-006 | Ron    | LOW      | Open   | CreditManager race condition (LoreConvo)                       |
| SEC-011 | Ron    | MEDIUM   | Open   | TOCTOU race in LoreDocs export                                 |
| SEC-016 | Ron    | LOW      | Open   | auto_save hook bypasses session limit (LoreConvo)              |
| SEC-018 | Ron    | INFO     | Open   | vault_import_dir/export: no path restriction (deferred)        |
| SEC-019 | Ron    | LOW      | Open   | Duplicated license.py: cross-product consistency test missing  |
| SEC-020 | Ron    | INFO     | Open   | pipeline_tracker.py f-string SQL pattern (safe, note only)    |
| SEC-022 | Ron    | INFO     | Open   | LoreDocs dev_mode dual-gate behavior undocumented              |
| SEC-023 | Ron    | INFO     | Open   | Glob sort ambiguity in DB discovery (multi-session edge case)  |

**Closed (cumulative):** SEC-002 through SEC-010, SEC-012, SEC-013, SEC-014, SEC-015,
SEC-017, SEC-021, GINA-003

---

## Recommendations (priority order)

1. **Ron (before v0.2.0 -- MEDIUM):** Fix SEC-011 (TOCTOU race in LoreDocs export).
   Use atomic write (temp file + rename) to prevent partial file corruption.

2. **Ron (before paying customers -- LOW):** Fix SEC-016 (auto_save session limit
   bypass). Add session count check in hook path before writing new session.

3. **Ron (before marketplace -- LOW):** Fix SEC-019 (add cross-product license
   consistency test). Catch divergence between LoreConvo and LoreDocs license.py
   copies before it becomes a silent bug.

4. **Ron (low effort -- INFO):** Fix SEC-022 (add dual-gate docstring to license.py
   in both products). One paragraph of comments, closes the finding.

5. **SEC-023 (INFO, backlog):** Consider using a session-ID env var to pick the
   exact mount path if multi-session DB confusion is ever observed in practice.

6. **No action needed** on SEC-001 (key stays gitignored, local only),
   SEC-018 (deferred path restriction), SEC-020 (f-string SQL is safe).

7. **Ron (near-term -- LOW):** Address CreditManager race condition (SEC-006) before
   high-volume multi-session usage.

---

## Trend

| Metric                | 2026-04-06 | 2026-04-07 | Delta                     |
|-----------------------|------------|------------|---------------------------|
| Total active findings | 8          | 9          | +1 (SEC-023 INFO added)   |
| CRITICAL              | 0          | 0          | --                        |
| HIGH                  | 0          | 0          | --                        |
| MEDIUM                | 1          | 1          | --                        |
| LOW                   | 3          | 3          | --                        |
| INFO                  | 4          | 5          | +1 (SEC-023 added)        |
| CVEs                  | 0          | 0          | --                        |

**Trend:** Stable. Today's commit (fbfdd11) is security-positive. SEC-023 added at
INFO only. No regressions. Posture unchanged from yesterday.
