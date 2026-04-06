# QA Report -- 2026-04-05 (Run B)

**Agent:** Meg (QA Engineer)
**Date:** 2026-04-05
**Overall Rating:** YELLOW

---

## Test Results Summary

| Suite | Passed | Failed | Skipped | Notes |
|-------|--------|--------|---------|-------|
| LoreConvo (ron_skills/loreconvo/tests/) | 204 | 0 | 0 | GREEN -- all passing |
| LoreDocs (ron_skills/loredocs/tests/) | 45 | 1 | 0 | YELLOW -- see MEG-046 |
| Internal tests (tests/) | 102 | 3 | 0 | YELLOW -- see MEG-043b |

**Total: 351 passed, 4 failed.**

---

## Findings

### MEG-046 -- test_readme_table_lists_all_tools regression (Ron's MEG-044 fix introduces new failure)

**Severity:** YELLOW
**Status:** NEW
**File:** `ron_skills/loredocs/tests/test_readme_tools.py`

Ron's staged fix for MEG-044 changes `_server_tool_names()` to:
```python
return re.findall(r'@mcp\.tool', self.server_src)
```

This returns a list of literal strings `['@mcp.tool', '@mcp.tool', ...]`, not actual tool
names. The `test_readme_table_lists_all_tools` test then computes:
```python
missing_from_readme = set(tools) - set(readme_names)
# set(tools) == {'@mcp.tool'} -- a single entry, the literal match text
# '@mcp.tool' does not appear in the README backtick table
```

**Result:** `AssertionError: Tools in server.py but not in README: {'@mcp.tool'}`

**Root cause:** `re.findall(r'@mcp\.tool', ...)` returns the matched text itself, not a
capture group. For counting this works (len is correct), but for cross-referencing it
breaks the name-comparison test.

**Correct fix:** `_server_tool_names()` should handle both decorator forms without breaking
the cross-reference logic. Options:
1. Extract explicit names with `re.findall(r'@mcp\.tool\(.*?name\s*=\s*"(\w+)"', src)` for
   explicit-name decorators, then separately handle implicit-name tools by extracting the
   function name after `@mcp.tool()` (no-arg form). Then verify both are in the README.
2. Simpler: skip the cross-reference test for the one implicit-name tool, or add
   `get_license_tier` explicitly to the README table (which it should be anyway -- it is a
   user-visible tool).

Note: The README tool table does not currently include `get_license_tier`. That is also a
doc gap worth fixing (MEG-047 below).

**Action for Ron:** Fix `_server_tool_names()` so it returns actual tool names (explicit or
inferred). Ensure `get_license_tier` appears in the README tool table.

---

### MEG-043b -- test_generate_license_key.py roundtrip tests still fail after partial fix

**Severity:** YELLOW
**Status:** PARTIALLY RESOLVED (regression remains)
**File:** `tests/scripts/test_generate_license_key.py`
**Previous finding:** MEG-043

Ron's staged fix corrects `_SCRIPT_PATH` (the script location), and `test_migrate_lore.py`
is now fully passing (12/12). However, the `TestRoundTrip` class has a second path bug that
Ron's fix did not address:

```python
def _get_loreconvo_path(self):
    return str(Path(__file__).parent.parent / "ron_skills" / "loreconvo" / "src")
```

When `__file__` is `tests/scripts/test_generate_license_key.py`:
- `parent` = `tests/scripts/`
- `parent.parent` = `tests/`
- Computed path: `tests/ron_skills/loreconvo/src` -- **does not exist**

Correct path needs `parent.parent.parent` (the repo root) before `ron_skills/...`:
```python
return str(Path(__file__).resolve().parent.parent.parent / "ron_skills" / "loreconvo" / "src")
```

**Tests still failing (3):**
- `TestRoundTrip::test_roundtrip_loreconvo`
- `TestRoundTrip::test_roundtrip_lore_suite_accepted_by_loreconvo`
- `TestRoundTrip::test_roundtrip_loreconvo_key_rejected_by_production_pubkey`

All fail with: `ModuleNotFoundError: No module named 'core'`

**Action for Ron:** Fix `_get_loreconvo_path()` to use `.parent.parent.parent` (3 levels
up from the test file, not 2).

---

### MEG-047 -- get_license_tier not listed in LoreDocs README tool table (doc gap)

**Severity:** YELLOW (advisory)
**Status:** NEW
**File:** `ron_skills/loredocs/README.md`

`get_license_tier` is the 35th MCP tool added by the GINA-001/SEC-017 fix. The LoreDocs
README tool table lists 35 tools in the "Tier Management" section header count but the
actual backtick-formatted table entry for `get_license_tier` is absent. This caused the
`test_readme_table_lists_all_tools` test failure (once Ron's MEG-046 fix is applied, this
is what would remain failing).

**Action for Ron:** Add `get_license_tier` to the README tool table in the Tier Management
section, with a brief description.

---

## Items Verified as RESOLVED

| Finding | Status | Evidence |
|---------|--------|----------|
| MEG-041 (lore-onboard skill missing from plugin) | RESOLVED | loreconvo-v0.3.0.plugin confirmed built; all plugin tests pass |
| MEG-043 (test_migrate_lore.py path bug) | RESOLVED | 12 passed, 0 failed |
| MEG-044 (test_readme_tools.py count) | PARTIALLY RESOLVED | Count test passes (35), but cross-ref test regressed (see MEG-046) |
| MEG-045 (doc tool counts stale: 12->13, 34->35) | RESOLVED | README, mcp_tool_catalog, marketplace README all read 13 / 35 |

---

## Code Review Notes

### Stability Mandate Status

Debbie worked through the Cowork plugin install flow end-to-end today (LoreConvo session
37457620, 18:19:12). Three bugs were fixed and the install flow is confirmed working. This
resolves the primary goal of the Stability Mandate (Cowork MCP tool access). Low QA risk
from these changes as they are install-path/venv fixes, not server logic changes.

### pipeline_tracker.py -- 'enhancement' type added (commit 1e5d882)

Low-risk addition. Three lines changed: VALID_TYPES list, TYPE_PREFIX dict, and cmd_types
description. Logic is consistent with existing type patterns. No tests cover pipeline_tracker.py
directly (no `tests/scripts/test_pipeline_tracker.py` exists). Advisory only -- the change
is simple enough that manual review is sufficient, but a basic test file would be valuable.

**No new tests written this session** (turn budget: approaching 20 tool calls; skipping new
test authoring to ensure report + commit + LoreConvo save complete within budget).

---

## Documentation Summary

| Location | LoreConvo count | LoreDocs count | Status |
|----------|----------------|----------------|--------|
| Product README | 13 | 35 | CORRECT |
| mcp_tool_catalog.md | 13 | 35 | CORRECT |
| marketplace/claude-plugins/README.md | 13 | 35 | CORRECT |
| loredocs-plugin/README.md | -- | 35 | CORRECT |
| SKILL.md | not checked (low risk) | not checked | N/A |

---

## Summary Table

| Finding | Severity | Status |
|---------|----------|--------|
| MEG-041 (lore-onboard in plugin) | RED | RESOLVED |
| MEG-043b (roundtrip test path -- _get_loreconvo_path) | YELLOW | Still open |
| MEG-046 (test_readme_tools regression from MEG-044 fix) | YELLOW | NEW -- needs Ron fix |
| MEG-047 (get_license_tier missing from README tool table) | YELLOW | NEW -- advisory |

**Next for Ron (in priority order):**
1. Fix MEG-043b: patch `_get_loreconvo_path()` in `tests/scripts/test_generate_license_key.py`
   to use `.parent.parent.parent` instead of `.parent.parent`
2. Fix MEG-046: rework `_server_tool_names()` in `test_readme_tools.py` to return actual tool
   names. Extract explicit names with the existing regex AND extract function name after
   bare `@mcp.tool()` decorators. Then also add `get_license_tier` to README table (MEG-047).
3. After both fixes: run full test suite -- target 0 failures across all suites.
