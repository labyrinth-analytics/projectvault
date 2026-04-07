# Product Architecture Review - 2026-04-06

**Agent:** Gina (Enterprise Architect)
**Run type:** Scheduled (Monday product review)
**Products reviewed:** LoreConvo v0.3.0, LoreDocs v0.1.0
**Git range:** Commits since 2026-04-05 product review (b6e65ec, d950b80, 1ceeab3, a076ad4)
**Overall Assessment:** YELLOW

---

## Executive Summary

This session reviewed whether Ron's recent commits correctly addressed the prior open
findings (GINA-001, GINA-002) and assessed the current state of both products after
the Stability Mandate was declared complete. Both GINA-001 and GINA-002 are now
RESOLVED -- the pre-marketplace security gate (vault_set_tier bypass) and the
lore-onboard packaging gap are both closed.

YELLOW rating is driven by three remaining test suite failures (MEG-043b, MEG-046,
MEG-047) and one newly identified architectural inconsistency (GINA-003) in the
license.py dev_mode logic. None of these are blockers for current work, but MEG-046
is a regression introduced by Ron's fix attempt and should be prioritized.

The Stability Mandate is complete. Both products install and run correctly on Cowork
(confirmed by Debbie 2026-04-05). The frozen CLI and new-product work may now proceed
per the mandate's definition of done.

---

## Stability Mandate Status

**COMPLETE.** Debbie confirmed the full Cowork plugin install flow end-to-end on
2026-04-05 (LoreConvo session 37457620). Three install bugs were found and fixed.
LoreConvo MCP tools are callable in Cowork sessions. The mandate definition of done
is satisfied: both products install, MCP tools are callable, sessions persist and are
retrievable.

This unblocks all FROZEN items in CLAUDE.md (CLI entry points, new products, etc.).

---

## Findings Verification (Prior Items)

### GINA-001 / SEC-017: vault_set_tier bypasses license validation (LoreDocs)

**Prior finding:** vault_set_tier() in loredocs/server.py wrote "pro" to config.json
without validating LOREDOCS_PRO. Any caller could bypass the paywall.

**Status: RESOLVED (commit b6e65ec, 2026-04-05)**

Code review confirmed. The fix correctly places a license check before set_tier():

  - If params.tier == "pro", get_license_status() is called first.
  - If status["is_pro"] is False, an error string is returned immediately with clear
    instructions for the user to set LOREDOCS_PRO and get a license key.
  - Two distinct error messages cover the "no key" and "invalid key" cases.
  - Downgrade to "free" does not require a license check (correct -- no paywall on downgrade).
  - Dev bypass (LOREDOCS_DEV=true) is preserved as expected.
  - Brock independently confirmed the fix in security_report_2026_04_05.md with 7 targeted tests.

Fix assessment: CORRECT and well-tested. GINA-001 is fully closed.

---

### GINA-002 / MEG-041: /lore-onboard skill not packaged in .plugin bundle (LoreConvo)

**Prior finding:** The loreconvo-v0.3.0.plugin zip did not include the /lore-onboard
skill, so users installing from the plugin bundle could not use the onboarding flow.

**Status: RESOLVED (commit d950b80, 2026-04-05)**

Verified: ron_skills/loreconvo-plugin/skills/ now contains three skills:
  - lore-onboard/
  - recall/
  - save/

MEG-041 confirmed all 18 plugin-related tests pass. The plugin bundle is complete.

Fix assessment: CORRECT. GINA-002 is fully closed.

---

### SEC-014: cryptography missing from pyproject.toml

**Status: RESOLVED (prior commit, confirmed in 2026-04-05 review)**

Both pyproject.toml files declare cryptography>=41.0.0. No change since last review.
Still closed.

---

## New Findings

### GINA-003 (MEDIUM): license.py dev_mode logic divergence between products

**Products:** LoreConvo and LoreDocs
**Files:** ron_skills/loreconvo/src/core/license.py vs ron_skills/loredocs/loredocs/license.py
**Found:** 2026-04-06 (via diff during cross-product consistency check)

The two license.py files have diverged in a functionally significant way in the
get_license_status() function:

  LoreConvo (line 170):
    if dev_mode and env_value and not env_value.startswith(_KEY_PREFIX):

  LoreDocs (line 169):
    if dev_mode and not env_value.startswith(_KEY_PREFIX):

The `env_value and` guard is present in LoreConvo but absent in LoreDocs. Impact:

  - LoreConvo dev mode (LAB_DEV_MODE=1) with no LORECONVO_PRO set: env_value is "",
    the `env_value and` guard is False, so the dev bypass does NOT activate. The
    function falls through to the "free tier" path. Correct for production safety.

  - LoreDocs dev mode (LAB_DEV_MODE=1) with no LOREDOCS_PRO set: env_value is "",
    `not "".startswith(_KEY_PREFIX)` is True, so the dev bypass ACTIVATES. LoreDocs
    grants Pro access with no key at all when in dev mode.

For Debbie's single-dev setup this is not a security concern (LAB_DEV_MODE is only
set intentionally). However, the behavioral asymmetry is unexpected: LoreDocs is more
permissive than LoreConvo in dev mode, and a future contributor comparing the two
products would find contradictory behavior. It also means the two products cannot share
a license validation test suite without per-product branching.

The files are already tracked as a SEC-019 open item (duplicated license.py). This
specific divergence is the most concrete behavioral consequence of that duplication.

**Recommended fix:** Add the `env_value and` guard to LoreDocs to match LoreConvo:

  if dev_mode and env_value and not env_value.startswith(_KEY_PREFIX):

This is the stricter and safer behavior. LoreDocs dev workflow only requires setting
LOREDOCS_DEV=1 (or equivalent) -- no need to rely on the empty-string bypass.

BROCK-REVIEW: Confirm whether the more permissive LoreDocs dev_mode behavior is
intentional. If LAB_DEV_MODE=1 is the only gate, an attacker who can set env vars
can already bypass everything -- the dev bypass path is moot for security. This is
LOW actual risk in the current local deployment, but document the intended behavior.

---

## Test Suite Status

| Suite | Status | Notes |
|-------|--------|-------|
| LoreConvo (204 tests) | GREEN | All passing |
| LoreDocs (45 tests) | YELLOW | 1 failing -- MEG-046 |
| tests/scripts (102 tests) | YELLOW | 3 failing -- MEG-043b |
| Total | YELLOW | 4 failures, 351 passing |

### Open Test Findings (from Meg's reports)

**MEG-043b (YELLOW): _get_loreconvo_path() path depth bug**
File: tests/scripts/test_generate_license_key.py
Ron's MEG-043 fix corrected _SCRIPT_PATH but missed a second path bug in the
TestRoundTrip class. The fix used .parent.parent (lands in tests/) but needs
.parent.parent.parent (repo root) before ron_skills/loreconvo/src. Three roundtrip
tests still fail with ModuleNotFoundError. One-line fix.

**MEG-046 (YELLOW): test_readme_tools regression from MEG-044 fix**
File: ron_skills/loredocs/tests/test_readme_tools.py
Ron's fix for MEG-044 changed _server_tool_names() to re.findall(r'@mcp\.tool', src),
which returns the literal match strings, not tool names. The cross-reference test
(test_readme_table_lists_all_tools) then tries to find '@mcp.tool' in the README and
fails. This is a regression introduced by the fix itself. The count test passes but
the name-comparison test breaks.
Correct fix: extract function names from the @mcp.tool decorator context, not the
decorator string itself. Also add get_license_tier to the README tool table (MEG-047).

**MEG-047 (ADVISORY): get_license_tier missing from LoreDocs README tool table**
get_license_tier is the 35th MCP tool. README header count says 35 but the backtick
table entry is absent. Doc gap only -- will cascade to a test failure once MEG-046 is
fixed and the cross-reference test runs correctly.

---

## Architectural Consistency Assessment

| Area | LoreConvo | LoreDocs | Consistent? |
|------|-----------|----------|-------------|
| License validation gate (tier upgrade) | YES | YES | YES (GINA-001 resolved) |
| get_tier diagnostic tool | get_tier() | get_license_tier() | YES (different name, same behavior) |
| Error message format | Labyrinth style | Labyrinth style | YES |
| pyproject.toml cryptography dep | >=41.0.0 | >=41.0.0 | YES |
| Plugin bundle skills | lore-onboard, save, recall | save, recall (no onboard) | ACCEPTABLE (LoreDocs onboard TBD) |
| Dev mode bypass logic | env_value guard present | env_value guard absent | NO -- GINA-003 |
| license.py public key constant | separate copy | separate copy | NO -- SEC-019 (duplicate) |

The two major remaining consistency gaps are both related to the duplicated license.py
(SEC-019). The most impactful is GINA-003 (behavioral divergence). The underlying fix
is to either extract a shared lore-licensing package (medium effort) or at minimum keep
the two files byte-for-byte identical except for product-name strings and test that.

---

## Brock Handoff Items

**BROCK-REVIEW (from GINA-003 above):**
Confirm the intended behavior for LoreDocs dev_mode with empty LOREDOCS_PRO env var.
Is it intentional for LAB_DEV_MODE=1 to grant Pro access with no key set? Document
the answer so the two license.py files can be reconciled with certainty.

---

## Recommendation for Next Ron Session

Priority order for the next Ron session:

1. Fix MEG-043b (1 line): change .parent.parent to .parent.parent.parent in
   _get_loreconvo_path() in tests/scripts/test_generate_license_key.py.

2. Fix MEG-046 + MEG-047 (~10 lines): rework _server_tool_names() in
   test_readme_tools.py to extract actual function names, not decorator strings.
   Then add get_license_tier to the LoreDocs README tool table.

3. Fix GINA-003 (1 line): add the `env_value and` guard to LoreDocs license.py
   to match LoreConvo's dev_mode behavior.

4. After test suite is clean (0 failures target): begin CLI entry point work
   (CLAUDE.md TODO #1 -- LoreConvo CLI). The Stability Mandate is resolved and
   the frozen items are now unblocked.

---

## Summary

| Finding | Severity | Status |
|---------|----------|--------|
| GINA-001 (vault_set_tier bypass) | MEDIUM | RESOLVED -- commit b6e65ec |
| GINA-002 (lore-onboard missing from plugin) | MEDIUM | RESOLVED -- commit d950b80 |
| GINA-003 (license.py dev_mode divergence) | MEDIUM | NEW -- 1-line fix for Ron |
| MEG-043b (roundtrip test path) | YELLOW | Open -- 1-line fix for Ron |
| MEG-046 (test_readme_tools regression) | YELLOW | Open -- requires fix |
| MEG-047 (get_license_tier README gap) | ADVISORY | Open -- doc fix |
| SEC-019 (duplicated license.py) | LOW | Open -- long-term refactor |
| Stability Mandate | CRITICAL | COMPLETE -- Cowork install confirmed |

Overall posture: YELLOW. Two prior MEDIUM findings resolved. One new MEDIUM
inconsistency identified. Remaining open items are small fixes (1-10 lines each).
Products are installable and functional on both platforms. Cleared for CLI work.

---

*Report generated by Gina (Enterprise Architect) -- 2026-04-06*
*Next scheduled run: 2026-04-08 (Wednesday)*
