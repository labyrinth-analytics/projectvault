# Product Architecture Review - 2026-04-05

**Agent:** Gina (Enterprise Architect)
**Run type:** Scheduled (Sunday product review)
**Products reviewed:** LoreConvo v0.3.0, LoreDocs v0.1.0
**Git range:** Commits since 2026-04-04 product review (primarily aecf64a)
**Overall Assessment:** YELLOW

---

## Executive Summary

This session reviewed whether Ron's recent commits correctly addressed the findings from
the 2026-04-04 product review (GINA-001, GINA-002, SEC-014) and the Stability Mandate
progress. One finding is fully resolved (SEC-014), one is correctly completed (Stability
Mandate TODO #2 get_tier tool), and two remain open (GINA-001/SEC-017, GINA-002/MEG-041).

The four BROCK-REVIEW items from Gina's 2026-04-04 report have now been assessed by Brock
(security_report_2026_04_04.md). Gina's architectural assessment of those items is included
below. No new architectural regressions were introduced by the recent commits.

YELLOW rating is driven by two open pre-marketplace issues (GINA-001 and GINA-002) that
remain unaddressed. These must be fixed before any paying customer installs either product.

---

## Findings Verification (Prior Review Items)

### SEC-014: cryptography missing from pyproject.toml

**Prior finding:** Both pyproject.toml files were missing `cryptography` as a declared
dependency. Fresh uvx installs would fail at server startup with ImportError in license.py.

**Status: RESOLVED (commit aecf64a, 2026-04-04)**

Both files now correctly declare:
- ron_skills/loreconvo/pyproject.toml: `"cryptography>=41.0.0"`
- ron_skills/loredocs/pyproject.toml: `"cryptography>=41.0.0"`

The fix is correct and consistent. This closes the install flow blocker for Pro license
validation.

---

### Stability Mandate TODO #2: get_tier MCP tool

**Prior requirement:** Expose get_license_status() as a callable MCP tool in both products
so Debbie (and future users) can verify their license tier is loaded.

**Status: DONE (commit aecf64a, 2026-04-04)**

**LoreConvo:** `get_tier()` added at server.py line 339. Decorated with `@mcp.tool()`.
Delegates entirely to `get_license_status()`. Returns is_pro, mode, product, exp, email,
and error fields. Correct.

**LoreDocs:** `get_license_tier()` added at server.py line 1427. Named differently from
LoreConvo to avoid shadowing the imported `get_tier` from .tiers. Delegates to
`get_license_status()`. Same return fields. Correct.

**Architectural note:** The naming divergence (get_tier vs get_license_tier) is a minor
inconsistency between products. The docstring difference is negligible for the intended
diagnostic use. This is acceptable for the current version but worth standardizing in a
future cross-product API consistency pass.

**Brock review:** Confirmed PASS. Read-only tool, no license bypass risk, no information
leakage of private key material.

---

### GINA-001 / SEC-017: vault_set_tier bypasses license validation (LoreDocs)

**Prior finding:** vault_set_tier() in loredocs/server.py writes "pro" to config.json
without checking whether a valid LOREDOCS_PRO license key is present. Any user who calls
this MCP tool can unlock Pro tier without purchasing a license.

**Status: STILL OPEN. Not fixed.**

Code review confirms server.py lines 1391-1419 are unchanged. The function body calls
`set_tier(storage.root, params.tier)` directly, with no license validation. The docstring
still reads: "In a future release this will verify a license key. For now it trusts the
caller."

This is the most important fix before any marketplace distribution. A user who reads the
MCP tool list will find vault_set_tier and can trivially bypass the paywall. This is not
a theoretical concern -- it is a concrete, low-effort exploit path for any user who
installs LoreDocs and inspects its tools.

**Recommended fix (unchanged from GINA-001):**

```python
async def vault_set_tier(params: VaultSetTierInput, ctx: Context) -> str:
    if params.tier == TIER_PRO:
        pro_env = os.environ.get("LOREDOCS_PRO", "").strip()
        if not pro_env:
            return (
                "Error: Set the LOREDOCS_PRO environment variable to your "
                "Labyrinth Analytics license key to activate Pro tier."
            )
        from .license import is_pro_licensed
        if not is_pro_licensed(pro_env):
            return "Error: The provided license key is invalid or expired."
    storage = _get_storage(ctx)
    try:
        set_tier(storage.root, params.tier)
    except ValueError as exc:
        return f"Error: {exc}"
    ...
```

**Priority:** HIGH. Must fix before marketplace launch.

---

### GINA-002 / MEG-041: lore-onboard skill not in plugin bundle (LoreConvo)

**Prior finding:** The /lore-onboard skill was built and committed to the LoreConvo source
tree (ron_skills/loreconvo/skills/lore-onboard/) but was not added to the plugin bundle
(ron_skills/loreconvo-plugin/skills/). Users installing from the marketplace do not get
the onboarding command.

**Status: STILL OPEN. Not fixed.**

Directory listing confirms:
- ron_skills/loreconvo/skills/: lore-onboard, loreconvo, recall, save (skill exists)
- ron_skills/loreconvo-plugin/skills/: recall, save ONLY (lore-onboard missing)

Meg's MEG-041 tests (test_plugin_skills_sync.py) continue to fail on this exact gap.
This has been open since the lore-onboard skill was committed (9e6060f, 2026-04-03).

The fix is a one-step operation: copy the skill directory into the plugin bundle and
rebuild the .plugin zip. This is Ron's simplest outstanding TODO but it continues to
block the Stability Mandate from being fully resolved.

**Priority:** HIGH. Blocks Stability Mandate completion.

---

## BROCK-REVIEW Item Assessment (from security_report_2026_04_04.md)

Brock assessed four GINA-REVIEW items from the 2026-04-04 product review. Gina's
architectural assessment of each follows.

### SEC-016: auto_save hook bypasses session limit (LoreConvo)

**Brock severity:** LOW (local single-user context)
**Gina assessment:** Agree with Brock. The auto_save.py hook writes to SQLite directly
via its own save_to_db() function, bypassing the session limit check in
SessionDatabase.save_session(). In a public distribution, free-tier users using Claude
Code CLI could accumulate unlimited sessions via the hook while Cowork sessions are capped.

**Architectural note:** The dedup guard in auto_save.py (checking session UUID before
insert) is correctly implemented. The issue is specifically the missing limit check, not
the save mechanism itself.

**Fix complexity:** LOW. Add a COUNT(*) check before inserting in auto_save.py::save_to_db():
if count >= session_limit and not pro mode, skip the insert and log a warning. The session
limit value should be read from the same source as SessionDatabase (config or env var
LORECONVO_SESSION_LIMIT, default 50).

**Priority:** Fix before marketplace launch. Not urgent for current single-user setup.

---

### SEC-017: vault_set_tier has no license validation (LoreDocs)

**Same as GINA-001 above. See that section.**

---

### SEC-018: vault_import_dir / vault_export accept arbitrary paths (LoreDocs)

**Brock severity:** INFO (local); MEDIUM (multi-user/cloud)
**Gina assessment:** Agree with Brock's classification. This is an intentional design
choice for a local personal tool -- the user should be able to import from ~/Documents or
export to /tmp freely. No architectural change warranted at this time.

**For cloud/team deployment:** Will need an allowed_roots configuration pattern. The right
approach is a default_allowed_roots list in config (defaulting to home directory) with
user-configurable overrides. This should be a formal ADR when cloud sync work begins.

**Priority:** Defer until cloud sync or multi-user deployment planning.

---

### SEC-019: Duplicated license.py across both products (same public key)

**Brock severity:** LOW
**Gina assessment:** The duplication is the correct current approach. Both products are
distributed as separate .plugin files targeting separate PyPI packages. A shared library
(`labyrinth_licensing`) is the right long-term solution but adds distribution complexity
now (third package to maintain, version pin across both products).

**Confirmed:** Public key constants are identical across both files:
  `_LAB_PUBLIC_KEY_B64 = "2Y++SKM6ZVAz1T8f0EGinoLWlQ9wdZFwEelAYDb1hT0="`

**Minimum acceptable fix now:** Add a test that asserts both public key constants are
equal. This prevents drift if one file is updated without the other. Suggested test file:
tests/test_license_key_consistency.py.

**Priority:** LOW. Add consistency test in next Ron session that touches either license.py.

---

## Cross-Product Consistency Check

| Dimension | LoreConvo | LoreDocs | Status |
|-----------|-----------|----------|--------|
| pyproject.toml deps | cryptography>=41.0.0 | cryptography>=41.0.0 | CONSISTENT |
| license.py public key | 2Y++SKM... (same) | 2Y++SKM... (same) | CONSISTENT |
| license.py imports | clean (no unused) | clean (no unused) | CONSISTENT |
| Dev bypass pattern | LAB_DEV_MODE + non-LAB- value | LAB_DEV_MODE + non-LAB- value | CONSISTENT |
| Diagnostic MCP tool | get_tier() | get_license_tier() | MINOR DIVERGENCE |
| Tier enforcement | Config.is_pro property | get_tier() + set_tier() | ARCHITECTURAL DIVERGENCE |
| Plugin bundle completeness | INCOMPLETE (missing lore-onboard) | N/A | NEEDS FIX |
| Free-tier limit enforcement | SessionDatabase.save_session() | TierEnforcer.check_*() | CONSISTENT |
| Auto-save bypass gap | auto_save.py uncapped | N/A | NEEDS FIX |

**Key architectural divergence to note:** LoreDocs has a `vault_set_tier` MCP tool that
allows writing tier to config.json, while LoreConvo has no equivalent. LoreConvo's tier
is determined exclusively by env var + license key on every check. LoreDocs has a hybrid
model (license key OR config.json). Once vault_set_tier is fixed to require license
validation, the two models become equivalent in security posture. No change to the
LoreConvo side is needed.

---

## New Findings

### GINA-003 (LOW): Diagnostic tool naming divergence between products

LoreConvo exposes `get_tier()` while LoreDocs exposes `get_license_tier()`. Both do
the same thing. Users or agents working across both products who learn the tool name from
one will not find it by the same name in the other.

**Recommendation:** Standardize both to `get_license_tier()` in a future version bump.
The LoreConvo version is also named `get_tier()`, which could collide with a future
tier-management tool of the same name. LoreDocs chose `get_license_tier()` precisely to
avoid this collision with the imported `get_tier` from .tiers. LoreConvo should follow suit.

**Priority:** LOW. Address in next minor version bump for either product.

---

### GINA-004 (LOW): SEC-019 consistency test missing

No test currently asserts that both license.py files use the same public key. If one file
is updated during a key rotation and the other is forgotten, the products silently use
different keys and one stops validating correctly.

**Recommended test:** tests/test_license_key_consistency.py with one assertion:
assert loreconvo_key == loredocs_key, "Public key mismatch between products"

**Priority:** LOW. Add before next key rotation event or within the next two Ron sessions.

---

## Open Findings Tracker (All Products)

| ID | Source | Severity | Status | Description |
|----|--------|----------|--------|-------------|
| GINA-001 | Gina | MEDIUM | **OPEN** | LoreDocs vault_set_tier bypasses license validation |
| GINA-002 | Gina | MEDIUM | **OPEN** | lore-onboard skill not in LoreConvo plugin bundle |
| GINA-003 | Gina | LOW | **OPEN** | Diagnostic tool name divergence (get_tier vs get_license_tier) |
| GINA-004 | Gina | LOW | **OPEN** | No consistency test for public key across both license.py files |
| MEG-036 | Meg | YELLOW | Open | SQL Optimizer concurrency race (product on hold) |
| MEG-041 | Meg | RED | **OPEN** | lore-onboard not in plugin bundle (same as GINA-002) |
| MEG-042 | Meg | LOW | Open | SQL API tests not collectable from repo root |
| MEG-043 | Meg | LOW | Open | pipeline_tracker.py f-string SQL pattern (advisory) |
| SEC-011 | Brock | MEDIUM | Open | TOCTOU race in LoreDocs export |
| SEC-016 | Brock | LOW | Open | auto_save hook bypasses session limit |
| SEC-017 | Brock | MEDIUM | Open | vault_set_tier no license validation (same as GINA-001) |
| SEC-018 | Brock | INFO | Open | vault_import_dir/export: no path restriction (deferred) |
| SEC-019 | Brock | LOW | Open | Duplicated license.py (consistency test needed) |

**Resolved this session:** 0
**Closed from prior reviews:** SEC-014 (RESOLVED by Ron in aecf64a)

---

## Recommendation for Next Ron Session

Priority order:

1. **Fix GINA-002 / MEG-041 (HIGH - Stability Mandate blocker):** Copy
   ron_skills/loreconvo/skills/lore-onboard/ into ron_skills/loreconvo-plugin/skills/
   and rebuild the .plugin zip. This is a one-step fix and closes the Stability Mandate.

2. **Fix GINA-001 / SEC-017 (HIGH - marketplace blocker):** Add license key validation
   to vault_set_tier() in loredocs/server.py before accepting tier='pro'. See code
   recommendation in GINA-001 section above.

3. **Fix SEC-016 (MEDIUM - marketplace blocker):** Add session count check to
   auto_save.py::save_to_db() before inserting, consistent with SessionDatabase behavior.

4. **Add GINA-004 consistency test (LOW):** tests/test_license_key_consistency.py
   asserting both license.py public key constants are equal.

5. **Address MEG-042 (LOW):** Add conftest.py to ron_skills/sql_query_optimizer/api/tests/
   for standard pytest collection from repo root.

Items 1 and 2 are the minimum for Stability Mandate completion and marketplace readiness.
All others are lower-priority cleanup.

---

*Report generated by Gina (Enterprise Architect) - 2026-04-05*
*Next scheduled product review: Wednesday 2026-04-08*
