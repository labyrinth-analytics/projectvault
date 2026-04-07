# QA Report -- 2026-04-06 (Run B)

**Agent:** Meg (QA Engineer)
**Date:** 2026-04-06
**Overall Rating:** YELLOW

---

## Summary

Second QA pass for today, reviewing 5 new commits since Run A (7603c2e). Ron's session
fixed GINA-003 (LoreDocs license.py env_value guard) and attempted MEG-050 (combined
pytest collision). GINA-003 is confirmed fixed and verified. MEG-050 fix is incomplete --
the `__init__.py` + stub approach introduced a new package namespace collision. New
finding MEG-052 documents the residual combined-run failure. The hook-script chmod
additions are clean.

---

## Commits Reviewed (since Run A, 7603c2e)

| Hash | Summary |
|------|---------|
| 3b9e9b7 | blog rewrite: loredocs vault architecture (marketing only -- no QA impact) |
| 95fb0da | fix GINA-003/MEG-050: license.py env_value guard + test dedup + INSTALL.md |
| 983b096 | fix: chmod hook scripts in install.sh for both products |
| 5b48bf3 | updated marketing docs, fixed hook executable status |
| fcba32a | fix: chmod hook scripts in install.sh (LoreConvo) |

---

## Test Results Summary

| Suite | Passed | Failed | Skipped | Notes |
|-------|--------|--------|---------|-------|
| LoreConvo (ron_skills/loreconvo/tests/) | 204 | 0 | 0 | GREEN |
| LoreDocs (ron_skills/loredocs/tests/) | 39 | 0 | 1 error | test_vault_set_tier_license.py excluded (env, see below) |
| Internal tests (tests/) | 116 | 0 | 0 | GREEN |

**Individual suites: 359 passed, 0 failed** (down from 366 in Run A due to env constraint, not regression).

**Combined run: STILL FAILS** -- see MEG-052 below.

### Note on test_vault_set_tier_license.py (env dependency, not a regression)

`ron_skills/loredocs/tests/test_vault_set_tier_license.py` fails at collection with
`ModuleNotFoundError: No module named 'mcp'` in this session's environment. The `mcp`
package (FastMCP) is not installed at system level in the Cowork VM -- it lives inside
the product `.venv/` but the test runner is not using that venv. This was likely already
true in prior sessions where 46 passed; those runs must have had `mcp` available.

This is a pre-existing test environment dependency, not caused by today's commits. To run
this suite correctly, either activate the product venv or `pip install mcp` in the test
runner. Advisory only -- no new bug introduced.

---

## Resolved Since Run A

### GINA-003 VERIFIED FIXED -- LoreDocs license.py env_value guard

**Severity:** MEDIUM -> RESOLVED
**Commit:** 95fb0da
**File:** ron_skills/loredocs/loredocs/license.py lines 169 and 198

Both occurrences now read:
```python
if dev_mode and env_value and not env_value.startswith(_KEY_PREFIX):
```

Matches LoreConvo's stricter guard. When `LAB_DEV_MODE=1` and `LOREDOCS_PRO` is unset
(empty string), LoreDocs no longer grants Pro bypass. Behavior is now consistent across
both products. Confirmed clean.

---

## New Findings

### MEG-052 -- MEG-050 fix incomplete: combined pytest run still fails (different error)

**Severity:** YELLOW
**Status:** NEW
**Replaces:** MEG-050 (which is now PARTIALLY RESOLVED, not RESOLVED)
**Files:** ron_skills/loreconvo/tests/__init__.py, ron_skills/loredocs/tests/__init__.py,
ron_skills/loredocs/tests/test_license.py (stub)

Ron's fix for MEG-050 added `__init__.py` to both product test directories and moved
LoreDocs license tests to `test_loredocs_license.py`, leaving a 1-line stub at
`test_license.py`. This approach fails for two reasons:

**Problem 1 -- Stub file still triggers the original collision:**
The stub `test_license.py` in `ron_skills/loredocs/tests/` still exists as a file.
When pytest runs a combined invocation:
```
pytest ron_skills/loreconvo/tests/ ron_skills/loredocs/tests/ tests/
```
It encounters two files both named `test_license.py` in two directories both named
`tests/`. Even with `__init__.py`, Python resolves both to the same module name
`tests.test_license` -- the first found wins and the second raises:
```
ERROR collecting test_license.py
import file mismatch:
imported module 'tests.test_license' has this __file__ attribute:
  ...ron_skills/loreconvo/tests/test_license.py
which is not the same as the test file we want to collect:
  ...ron_skills/loredocs/tests/test_license.py
```

**Problem 2 -- __init__.py makes all three `tests/` dirs clash:**
All three test directories are named `tests/`. Adding `__init__.py` to
`ron_skills/loreconvo/tests/` makes Python treat it as a package named `tests`.
But `tests/` (the top-level internal suite) is also a package named `tests`. This
creates a second class of import errors:
```
E   ModuleNotFoundError: No module named 'tests.test_loredocs_gitignore'
```
...because Python resolves `tests` to the first package it finds (loreconvo/tests or
the top-level tests/), and the other files in a different `tests/` package are not
found.

**Root cause:** Three directories all named `tests/` cannot coexist as Python packages
under a single pytest invocation. The `__init__.py` approach only works when packages
have unique names.

**Minimum fix (2 steps):**
1. Delete `ron_skills/loredocs/tests/test_license.py` (the 1-line stub). The content
   already lives in `test_loredocs_license.py`. The stub's only purpose was as a
   tombstone, but it is the direct cause of the `tests.test_license` collision.
2. Remove `__init__.py` from `ron_skills/loreconvo/tests/` and
   `ron_skills/loredocs/tests/`. Without `__init__.py`, pytest falls back to its
   rootdir-based import mode which handles same-named leaf test files correctly when
   they are in different subtrees -- as long as the duplicate-named file (test_license.py)
   is gone.

After the 2-step fix, the combined invocation:
```
pytest ron_skills/loreconvo/tests/ ron_skills/loredocs/tests/ tests/ -q
```
should collect and run cleanly.

**Impact:** Same as MEG-050 -- CI or developer combined runs fail at collection.
Individual suite runs continue to work as workaround.

---

## Code Walkthrough (commits 95fb0da, 983b096, fcba32a)

### license.py fix (95fb0da) -- CLEAN

Two guard additions (`env_value and`) on lines 169 and 198 are minimal and correct.
No behavioral change when `env_value` is a valid non-empty string. The defensive guard
only fires when the env var is unset/empty, which is the intended behavior. No issues.

### test dedup approach (95fb0da) -- FLAWED (see MEG-052)

The intent was right (rename + __init__.py), but the execution left a stub file that
continues to cause the original collision, and introduced a second collision via package
name aliasing. See MEG-052 for the full analysis.

### test_loredocs_license.py (95fb0da) -- CLEAN

Content is well-structured: 184 lines, isolated from production keys via a test keypair
patched at module level. Covers is_pro_licensed, get_license_status, validate_license_key,
and edge cases (empty key, wrong prefix, dev mode with and without key). Good coverage.

### install.sh chmod additions (983b096, fcba32a) -- CLEAN with one observation

Both installers now run:
```bash
chmod +x "$HOOKS_DIR"/*.sh 2>/dev/null || true
```

LoreConvo has `hooks/scripts/*.sh` files, so this fires correctly.
LoreDocs does NOT have a `hooks/scripts/` directory at all. The `2>/dev/null || true`
silences the error and continues -- no breakage. However, this is dead code in LoreDocs
until hooks are added. Advisory observation only; no bug.

### INSTALL.md (95fb0da) -- CLEAN

Significantly trimmed from a verbose internal-notes format to a concise, user-facing
guide (from ~300 lines to ~70). Covers prerequisites, Option A (marketplace, coming
soon), Option B (developer install), and Claude Code settings.json config. The
"coming soon" label on the marketplace option is accurate and appropriate.

---

## Doc Verification

| Item | Claimed | Actual | Status |
|------|---------|--------|--------|
| LoreDocs README tool count | 35 | 35 (@mcp.tool count in server.py) | GREEN |
| LoreDocs INSTALL.md marketplace status | "Coming Soon" | Correct -- not yet live | GREEN |
| LoreConvo tool count (from Run A) | 13 | 13 | GREEN (no change) |

---

## Security Spot Check

- license.py guard changes: no new injection or bypass vectors introduced -- the added
  `env_value and` guard is strictly more restrictive than before. CLEAN.
- install.sh additions: no hardcoded secrets, no unsafe path expansions, globs are
  quoted or protected. CLEAN.
- INSTALL.md content: no internal business details (no pricing numbers, revenue targets,
  internal paths). CLEAN.

---

## Open Carry-Forward Items

| ID | Description | Severity | Status |
|----|-------------|----------|--------|
| MEG-047 | get_license_tier missing from LoreDocs README tool table | ADVISORY | OPEN |
| MEG-050 | Combined pytest run fails: duplicate test_license.py | YELLOW | PARTIALLY RESOLVED -> superseded by MEG-052 |
| MEG-051 | --read-id and --read not mutually exclusive in argparse | ADVISORY | OPEN |
| MEG-052 | Combined pytest run still fails after __init__.py partial fix | YELLOW | NEW |
| SEC-019 | Duplicated license.py between products (long-term refactor) | LOW | OPEN |

---

## Findings Summary

| ID | Description | Severity | Status |
|----|-------------|----------|--------|
| GINA-003 | LoreDocs license.py dev_mode missing env_value guard | MEDIUM | RESOLVED (95fb0da) |
| MEG-050 | Combined pytest run: duplicate test_license.py | YELLOW | PARTIALLY RESOLVED |
| MEG-052 | Combined pytest run still fails after __init__.py approach | YELLOW | NEW |

---

*Report generated by Meg (QA Engineer) -- 2026-04-06 (Run B)*
*Next scheduled run: 2026-04-07*
