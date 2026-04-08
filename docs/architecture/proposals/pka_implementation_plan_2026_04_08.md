# Personal Knowledge Architecture (PKA) Implementation Plan

**Author:** Gina (Enterprise Architect)
**Date:** 2026-04-08
**Status:** Proposal — awaiting Debbie's review
**Inspired by:** myicor "Claude and a folder. that's it." + Perplexity competitive analysis flagging three-inbox model as Lore differentiator
**Scope:** Internal reorganization of `side_hustle/docs/` AND dogfooding case study for LoreDocs/LoreConvo marketing

---

## 0. TL;DR

Replace the current sprawling `docs/` tree with a three-inbox Personal Knowledge Architecture (PKA):

```
knowledge/
  raw/          <- agents write here; unfiltered, timestamped, append-only
  processing/   <- Debbie promotes here; decisions/specs/ADRs in draft
  archive/      <- stabilized conclusions; feeds tool instructions and roadmap
```

Mirror the same three-inbox model as LoreDocs vaults (`lore-raw`, `lore-processing`, `lore-archive`) so we prove the pattern works on both filesystem and vault surfaces. Agents deposit reports into `raw/`, Debbie reviews and promotes, stabilized outputs land in `archive/` and become the source of truth for tool instructions, CLAUDE.md, and the public roadmap.

Core principle (from myicor): **store conclusions, not inputs.** Raw agent chatter is cheap; the scarce asset is the decision that came out of it. PKA makes the decision promotion explicit.

---

## 1. PKA Core Model

### 1.1 The three inboxes

| Inbox | Purpose | Who writes | Who reads | Retention |
|---|---|---|---|---|
| **raw/** | Unfiltered agent output, daily reports, QA scans, security scans, scout findings, meeting notes | Agents (automated) + Debbie (ad hoc) | Debbie during review, Jacqueline for dashboards | Rolling 90 days, then pruned |
| **processing/** | Items Debbie has promoted from raw because they deserve a decision. Drafts of decisions, specs, ADRs, open questions | Debbie (promotes); agents may draft here only when asked | Debbie, Gina (architect review), Ron (implementation) | Until promoted or rejected |
| **archive/** | Stabilized conclusions. The authoritative record. Feeds tool instructions, CLAUDE.md, roadmap, marketing | Debbie (promotes); immutable-ish (amendments as new entries) | Everyone and everything — this is the source of truth | Permanent |

### 1.2 Promotion rules

- `raw/ -> processing/` when Debbie reads a raw item and says "this needs a decision." One-command promotion (see Section 6).
- `processing/ -> archive/` when the conclusion is stable: decision made, spec accepted, ADR signed off. Triggers a sync job that updates tool instructions (Section 6.3).
- Nothing ever writes directly to `archive/` except via the promotion path. This is the enforcement edge of "store conclusions not inputs."
- Rejected items (in processing that don't pan out) move to `processing/rejected/` with a one-line reason. Not deleted — the trail matters.

### 1.3 "Store conclusions, not inputs" applied to Debbie

Today's `docs/` tree is mostly *inputs*: daily QA reports, daily security reports, executive dashboards regenerated nightly, marketing drafts, scout opportunity dumps. They pile up. Debbie skims, acts on some, forgets most.

PKA flips that. Inputs live in `raw/` and are ephemeral. The rare, valuable output — "we decided to use BSL 1.1," "we rejected the SQL optimizer niche," "our tier gating is 50 sessions / 3 vaults" — lives in `archive/` and is *the* answer to any future question on that topic.

Rule of thumb: if an agent produces it automatically every day, it's input. If Debbie had to make a judgment call to create it, it's a conclusion.

---

## 2. Directory Structure

### 2.1 Proposed layout

```
side_hustle/
  knowledge/
    raw/
      agents/
        ron/            <- ron session summaries, commit logs
        meg/            <- QA reports
        brock/          <- security reports
        gina/           <- architecture reviews (self-deposit)
        madison/        <- blog drafts, promo copy
        jacqueline/     <- daily exec dashboards, weekly roadmaps
        john/           <- tech docs run reports
        scout/          <- opportunity discovery dumps
      inbox/            <- Debbie's hand-dropped notes, meeting transcripts
      YYYY/MM/          <- subdirs within each agent folder for time-based pruning
    processing/
      decisions/        <- decision log entries in draft
      specs/            <- product specs / PRDs in draft
      adrs/             <- architecture decision records in draft
      open-questions/   <- questions awaiting Debbie's answer
      rejected/         <- items considered and declined, with one-line reason
    archive/
      decisions/        <- stabilized decision log (chronological)
      specs/            <- accepted specs
      adrs/             <- accepted ADRs, numbered and immutable
      playbooks/        <- long-lived how-to docs promoted from decisions
      index.md          <- auto-generated table of contents for the archive
  docs/
    living/             <- SYSTEM_INVENTORY.md, DEBBIE_DASHBOARD.md, COMPLETED.md, PIPELINE_AGENT_GUIDE.md
    public/             <- user-facing docs that ship with products (README, INSTALL)
```

Living documents stay in `docs/living/`. They are continuously mutated, not promoted — the PKA model doesn't fit them.

### 2.2 Before/after mapping

| Current location | Destination | Notes |
|---|---|---|
| `docs/competitive/` | `knowledge/raw/agents/competitive-intel/` | Daily scans are raw; any conclusions (positioning decisions) get promoted to `archive/decisions/` |
| `docs/architecture/` | `knowledge/raw/agents/gina/` (reports) + `knowledge/processing/adrs/` (drafts) + `knowledge/archive/adrs/` (accepted) | Gina's product reviews become raw; pipeline proposals become processing drafts |
| `docs/qa/` | `knowledge/raw/agents/meg/` | QA reports are inputs; any "we decided to fix X by doing Y" conclusion gets promoted |
| `docs/security/` | `knowledge/raw/agents/brock/` | Same — security reports are raw; architectural guidance becomes ADRs |
| `docs/marketing/` | `knowledge/raw/agents/madison/` (drafts) + `knowledge/archive/playbooks/marketing-voice.md` (promoted voice guide) | Blog drafts raw; editorial voice, content calendar structure = archive |
| `docs/pm/` | `knowledge/raw/agents/jacqueline/` | Daily dashboards are raw; the roadmap structure/KPIs become archive playbooks |
| `docs/status/` | `knowledge/raw/agents/ron/` | Session status docs are raw; SYSTEM_INVENTORY stays in `docs/living/` |
| `docs/instructions/` | split: SYSTEM_INVENTORY to `docs/living/`, PIPELINE_AGENT_GUIDE to `docs/living/`, anything else by type | Living docs don't belong in PKA |
| `docs/internal/opportunities/` | `knowledge/raw/agents/scout/` + `knowledge/processing/specs/` (approved opps) | Scout dumps raw; Debbie-approved opps become specs |
| `docs/internal/pm/` | `knowledge/raw/agents/jacqueline/` | Same as `docs/pm/` |
| `docs/COMPLETED.md` | `docs/living/COMPLETED.md` | Living ledger |
| `docs/DEBBIE_DASHBOARD.md` | `docs/living/DEBBIE_DASHBOARD.md` | Living |
| `docs/PIPELINE_AGENT_GUIDE.md` | `docs/living/PIPELINE_AGENT_GUIDE.md` | Living |

---

## 3. LoreDocs Vault Structure

Mirror the filesystem with three vaults. This is the dogfood layer — proves the pattern works in LoreDocs itself.

| Vault | Role | What goes in | Promotion path |
|---|---|---|---|
| **lore-raw** | Inbox vault | Agent session summaries (from LoreConvo), daily reports, scout findings, drafts | `vault_add_document` with `status: raw` tag. Auto-populated by agents at session end. |
| **lore-processing** | Work vault | Decisions/specs/ADRs in draft. Debbie's working set. | `vault_move_document` from lore-raw. Promotion adds `status: processing` tag and a `promoted_from` field pointing at the raw source. |
| **lore-archive** | Conclusion vault | Stabilized decisions, accepted specs, accepted ADRs, playbooks | Promotion from lore-processing. Adds `status: archive`, `accepted_date`, and `supersedes` (if replacing a prior entry). Immutable via convention; amendments are new entries. |

### 3.1 Promotion semantics in LoreDocs

- `lore-raw -> lore-processing`: lightweight, one call, preserves document ID and adds metadata.
- `lore-processing -> lore-archive`: triggers (a) a `vault_inject_summary` regeneration for the archive, (b) a webhook/script that rewrites CLAUDE.md tool instruction blocks from archived playbooks, (c) a Jacqueline dashboard refresh.
- Cross-vault search works naturally (LoreDocs already supports multi-vault `vault_search`), so Debbie can ask "find anything about BSL licensing" and get results across all three inboxes with status markers.

### 3.2 Why three vaults and not three tags in one vault

- Clean permission/retention rules per vault (prune raw aggressively, never prune archive).
- Agents only need write access to `lore-raw`. Reduces blast radius if an agent misbehaves.
- Matches the filesystem structure 1:1 — the mental model is the same on both surfaces.
- Vault size stays manageable; FTS5 indexes stay fast.

---

## 4. Unit Types

Three first-class unit types live in `processing/` and `archive/`. All three share a base frontmatter schema with type-specific extensions.

### 4.1 Base frontmatter (all unit types)

```yaml
---
id: DEC-0042                    # or SPEC-0013, ADR-0009
type: decision                  # decision | spec | adr
title: "Adopt BSL 1.1 for Lore products"
status: archive                 # raw | processing | archive | rejected
created: 2026-03-31
promoted_to_processing: 2026-04-01
promoted_to_archive: 2026-04-03
author: debbie                  # or agent name if drafted
tags: [licensing, lore, business]
supersedes: []                  # list of IDs this replaces
related: [ADR-0005, DEC-0038]
source: knowledge/raw/agents/gina/2026-04-01_licensing_options.md
---
```

### 4.2 Type-specific additions

**Decision log entry (`type: decision`, ID `DEC-####`):**
```yaml
context: "why this came up"
options_considered: ["A", "B", "C"]
decision: "picked B"
rationale: "one-paragraph why"
consequences: "what this commits us to"
```
Filename: `DEC-0042_adopt_bsl_license.md`

**Spec / PRD (`type: spec`, ID `SPEC-####`):**
```yaml
problem: ""
goals: []
non_goals: []
success_metrics: []
acceptance_criteria: []
owner: ron
target_ship: 2026-05-15
```
Filename: `SPEC-0013_loreconvo_cli.md`

**ADR (`type: adr`, ID `ADR-####`):**
```yaml
context: ""
decision: ""
status: accepted        # proposed | accepted | superseded | deprecated
consequences: ""
alternatives: []
```
Filename: `ADR-0009_three_inbox_pka.md` (this document will become ADR-0009 upon Debbie's approval)

### 4.3 Minimal required fields (agents must provide)

When an agent drafts a unit (rare — mostly Debbie does this), they MUST include: `id`, `type`, `title`, `status`, `created`, `author`, `source`. Everything else can be filled during promotion.

---

## 5. Agent Routing

All agents deposit into `knowledge/raw/agents/<name>/YYYY/MM/`. No agent writes to `processing/` or `archive/` without explicit instruction. This is the enforcement wall.

### 5.1 Per-agent cheat sheet

| Agent | Drops into | Filename pattern | Tags for Debbie review |
|---|---|---|---|
| **Ron** | `raw/agents/ron/YYYY/MM/` | `ron_session_YYYY-MM-DD_HHMM.md` | `review:needed` if blocked, `review:decision` if Ron wants Debbie to pick between options |
| **Meg** | `raw/agents/meg/YYYY/MM/` | `qa_report_YYYY-MM-DD.md` | `severity:red` or `severity:yellow` surface to Debbie; green is ignore-safe |
| **Brock** | `raw/agents/brock/YYYY/MM/` | `security_report_YYYY-MM-DD.md` | `severity:at-risk`, `gina-review` for architectural handoffs |
| **Madison** | `raw/agents/madison/YYYY/MM/` | `blog_draft_<slug>_YYYY-MM-DD.md`, `promo_<channel>_YYYY-MM-DD.md` | `review:publish` when draft is ready for Debbie |
| **Jacqueline** | `raw/agents/jacqueline/YYYY/MM/` | `exec_dashboard_YYYY-MM-DD.html`, `roadmap_YYYY-MM-DD.html` | `posture:action-required` elevates to Debbie's inbox top |
| **Gina** | `raw/agents/gina/YYYY/MM/` | `architecture_review_YYYY-MM-DD.md`, `OPP-###_proposal.md` | `brock-review` for security architectural handoffs |
| **Scout** | `raw/agents/scout/YYYY/MM/` | `scout_report_YYYY-MM-DD.md` + per-opp files | `triage:new` default, promoted to processing if approved |
| **John** | `raw/agents/john/YYYY/MM/` | `tech_docs_report_YYYY-MM-DD.md` | rarely needs Debbie review |

### 5.2 What does NOT go in raw/

- Source code (obviously) — stays in `ron_skills/`
- Living docs — stay in `docs/living/`
- User-facing documentation — stays in `docs/public/`
- LoreConvo sessions themselves — already a separate system; agents still call `save_session`, but ALSO drop a markdown summary in raw/. The markdown is the Debbie-readable index; LoreConvo is the queryable backbone.

### 5.3 Dual-write during transition

During Phase 1 rollout, agents dual-write: their existing locations AND the new `raw/` locations. This gives us a rollback path. After Phase 2 validation, the old locations become symlinks to the new ones, then get deleted in Phase 3.

---

## 6. Promotion Workflow

Debbie's review loop should take 15 minutes a day, not 2 hours. The promotion tooling is the key to that.

### 6.1 Daily review loop (target: 15 min)

1. Open Jacqueline's exec dashboard (from `raw/agents/jacqueline/YYYY/MM/latest.html`).
2. Skim flagged items (severity:red, review:needed, posture:action-required).
3. For each flagged item, either:
   - **Ignore** — leave in raw, it'll prune in 90 days.
   - **Promote** — run `lore promote <raw_path>` which moves the file to `processing/` and opens the draft decision/spec/ADR skeleton in $EDITOR.
   - **Answer** — Debbie writes the conclusion right there, saves, the promote command flips status to `archive` on exit.

### 6.2 `promote` CLI (proposed)

A thin Python script, `scripts/promote.py`, wrapping git mv + frontmatter rewrite:

```
lore promote raw/agents/gina/2026/04/architecture_review_2026-04-08.md \
    --type decision \
    --title "Adopt three-inbox PKA"
```

Effect:
- Generates next ID (`DEC-0043`)
- Rewrites frontmatter with promoted_to_processing timestamp and source pointer
- `git mv` to `processing/decisions/DEC-0043_adopt_three_inbox_pka.md`
- Opens in editor
- On editor exit, if status was bumped to `archive`, does a second `git mv` to `archive/decisions/` and triggers the sync job.

Fallback if CLI doesn't exist yet: plain `git mv` with manual frontmatter edit. Low-friction either way.

### 6.3 Sync job: archive -> tool instructions

When a file lands in `archive/`, a post-promotion hook rewrites the relevant sections of:
- `docs/living/SYSTEM_INVENTORY.md`
- `side_hustle/CLAUDE.md` (specifically the "Active Workstreams" and "Pending Items" blocks)
- `docs/living/DEBBIE_DASHBOARD.md` (removes the action item that was just resolved)

This closes the loop: conclusions archived in PKA automatically flow back into the tool instructions every agent reads at session start. That's the payoff — no more stale CLAUDE.md drift.

---

## 7. Migration Plan

### 7.1 Phases

| Phase | Effort | Blocks on | Description |
|---|---|---|---|
| **P0: Proposal approval** | S | Debbie | This document. |
| **P1: Skeleton + living docs** | S (4 hr) | P0 | Create `knowledge/` tree, move living docs to `docs/living/`, stub `index.md` |
| **P2: Agent dual-write** | M (1-2 days) | P1 | Update all 9 agent prompts to write to `raw/agents/<name>/` in addition to current locations. Test one full agent cycle. |
| **P3: Promote CLI** | M (1 day) | P1 | Build `scripts/promote.py` with ID generation, git mv, frontmatter rewrite, sync hook |
| **P4: LoreDocs vaults** | M (1 day) | P1, requires LoreDocs install-flow fix | Create `lore-raw`, `lore-processing`, `lore-archive`. Mirror filesystem. |
| **P5: Historical migration** | L (2-3 days) | P2 stable | Walk `docs/competitive/`, `docs/qa/`, etc., and sort into raw/ (low-signal) or archive/ (high-signal conclusions). Debbie does the high-signal picks; a script does the bulk move. |
| **P6: Kill old `docs/` tree** | S | P5 complete + 2 weeks of dual-write green | Symlink, then delete. |
| **P7: Dogfood marketing** | M (1 day) | P6 | Capture metrics, write the case-study blog post |

**Total:** roughly 7-10 engineering days spread over 3-4 calendar weeks.

### 7.2 Content that should NOT move

- `docs/living/SYSTEM_INVENTORY.md` — living, mutates constantly
- `docs/living/DEBBIE_DASHBOARD.md` — living
- `docs/living/COMPLETED.md` — living ledger
- `docs/living/PIPELINE_AGENT_GUIDE.md` — living protocol doc
- `docs/public/` (future home for README/INSTALL) — user-facing, not internal knowledge

### 7.3 Content that should be promoted STRAIGHT to archive during migration

Debbie's historical judgment calls are already conclusions. They skip `processing/`:
- BSL 1.1 license decision (2026-03-31) -> `archive/decisions/DEC-0001_bsl_license.md`
- LoreConvo/LoreDocs rebrand decision (2026-03-25) -> `archive/decisions/DEC-0002_lore_rebrand.md`
- Umbrella insurance 50/50 allocation -> `archive/decisions/DEC-0003_umbrella_split.md`
- Mr. Cooper as mortgage lender (not BECU) -> `archive/decisions/DEC-0004_mortgage_lender.md`
- Three-inbox PKA adoption (this doc, assuming approval) -> `archive/adrs/ADR-0009_three_inbox_pka.md`

---

## 8. Dogfooding the Marketing Story

Lore's differentiator per Perplexity is exactly this pattern. If we adopt it internally and document the adoption, we get a case study for free.

### 8.1 Metrics to capture (baseline before migration, measure after)

- **Time spent in daily review** — before/after. Target: 30 min -> 15 min.
- **Stale CLAUDE.md drift** — count of times per month Debbie finds something in CLAUDE.md that contradicts a decision she remembers making. Target: 3/mo -> 0/mo.
- **Agent rework rate** — how often an agent redoes work another agent already did because they couldn't find the conclusion. Track via LoreConvo search queries that return nothing then are re-asked.
- **Mean time from raw report -> archived decision** — how long a flagged item sits in raw/. Target: under 48 hours.
- **Archive growth rate** — decisions per week. Healthy sign if it grows modestly and then plateaus per topic area.
- **Raw volume** — bytes/week written to raw/. Sanity check on agent chatter.

### 8.2 Blog post outline (for Madison, post P7)

Working title: **"How we organize knowledge with Lore: three inboxes, one source of truth"**

Angle: data-engineering practitioners drowning in agent output, dashboards, meeting notes, and scanning reports. Show the before (sprawling docs/), show the after (three-inbox PKA), show the metrics deltas, show the promote CLI in a 30-second screencast.

Cross-link: LoreDocs (vault implementation) and LoreConvo (the underlying session store). Natural call-to-action: install Lore, build your own PKA, "we use this every day."

### 8.3 Companion artifacts

- Public sanitized example of a `raw/` -> `processing/` -> `archive/` trail (use a non-sensitive decision like the BSL license, already public).
- A 5-minute Loom of Debbie's morning review.
- Sample `promote.py` on GitHub as a gist (marketing-friendly OSS breadcrumb).

---

## 9. Open Questions for Debbie

1. **Root directory name.** `knowledge/` vs `pka/` vs `vault/` vs keeping it under `docs/pka/`. My vote: `knowledge/` at repo root — matches the mental model and avoids confusion with `docs/living/`.
2. **Living docs inside or outside PKA?** Proposal is `docs/living/` outside the PKA tree. Alternative: a fourth directory `knowledge/living/`. Pros of outside: clearer separation. Pros of inside: single root. My vote: outside.
3. **How aggressive should raw/ pruning be?** 90 days is my default. Could be 30 or 180. Depends on how much regret you'd feel pruning a raw report you never promoted. Suggested starting point: 90 days, review after Phase 7.
4. **Should LoreConvo sessions auto-export to raw/?** Proposal is agents dual-write. Alternative: a nightly job exports all new LoreConvo sessions to raw/ as markdown, keeping agents ignorant of PKA. Pros: agents stay simple. Cons: lag of up to 24 hr, and LoreConvo becomes a dependency of PKA. My vote: start with dual-write, reconsider after Phase 2.
5. **Who owns `gina-review` / `brock-review` handoffs?** Currently tagged in reports. Should they also create a `processing/open-questions/` item automatically? Leaning yes for anything tagged `severity:at-risk` or `review:decision`.
6. **Numbering scheme.** `DEC-0001` global, or `DEC-2026-0001` per year? Global is simpler; per-year sorts better. My vote: global with four digits (`DEC-0042`).
7. **Does the promote CLI need to exist for Phase 1?** We can start with git mv + manual frontmatter and build the CLI in Phase 3. That's my plan — but if you want the CLI first, it pushes Phase 2 by a day.
8. **Does the archive -> CLAUDE.md sync need to be automatic or manual-with-diff-preview?** Auto is elegant but scary if a bad promotion leaks. Manual-with-preview is safer. My vote: manual preview for Phase 1-2, flip to auto after 2 weeks of clean runs.
9. **Public repo exposure.** `knowledge/` is in the monorepo, which is private. But some decisions (license, rebrand) are public info. Do we want a separate `knowledge/public/archive/` that syncs to an external GitHub pages site? Nice-to-have, not Phase 1.
10. **Does this replace the pipeline opportunity DB?** PipelineDB already does the Scout -> Gina -> Ron flow. PKA and PipelineDB overlap in the "approved opportunity -> spec" transition. Suggest: PipelineDB stays as the structured store for opportunity lifecycle, PKA stores the prose artifacts (Gina's proposal, the spec, the ADR). They cross-link by ID.

---

## 10. Phased Rollout (T-shirt sized)

| Phase | Size | Deliverable | Success criterion |
|---|---|---|---|
| **P0** | XS | This proposal, reviewed | Debbie says "approved with changes X, Y, Z" |
| **P1** | S | `knowledge/` skeleton exists; living docs relocated | `tree knowledge/` matches spec; agents still working against old paths |
| **P2** | M | All 9 agents dual-write to raw/ | 7 consecutive days of every agent landing files in both old and new locations |
| **P3** | M | `scripts/promote.py` works end-to-end | Debbie promotes one item raw -> processing -> archive without hand-editing |
| **P4** | M | Three LoreDocs vaults exist and mirror filesystem | `vault_search "BSL"` returns hits from archive vault |
| **P5** | L | Historical `docs/` content sorted into raw/archive | Old `docs/` tree contains only living/public, nothing else |
| **P6** | S | Old `docs/` tree removed | `git ls-files docs/` returns only `living/` and `public/` |
| **P7** | M | Marketing case study captured and drafted by Madison | Blog draft in `raw/agents/madison/` tagged `review:publish` |

**Hard stop:** if P2 (dual-write) is still broken after 10 days, roll back and reassess.

---

## 11. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Agents write to wrong location during dual-write | Med | Low | Prompts explicit; Meg adds a test that checks for file presence in raw/ |
| Promote CLI bugs corrupt frontmatter | Low | Med | Dry-run mode by default; git history as safety net |
| Debbie's review loop balloons instead of shrinking | Med | High | Measure week-over-week; if still >20 min/day by week 3, tune the severity tags downward |
| Historical migration loses context | Med | Med | Phase 5 is non-destructive (copy not move) until 2 weeks clean |
| LoreDocs vault install flow still broken (see stability mandate) | High | Blocks P4 | P4 is explicitly blocked on the current mandate; do P1-P3 in parallel with Ron's fix |
| Marketing case study leaks sensitive internal decisions | Low | High | Blog uses only already-public decisions (BSL, rebrand); no revenue numbers, no customer data |
| Scope creep into "build a full CMS" | Med | High | Cap at 10 engineering days total. Anything beyond P7 needs a new proposal. |

---

## 12. Next Steps

1. Debbie reviews this proposal and answers the 10 open questions in Section 9.
2. Based on answers, Gina revises this doc into ADR-0009 (first archive entry).
3. Ron picks up P1 implementation (after the current stability mandate is resolved).
4. Jacqueline adds a "PKA Adoption" row to the exec dashboard so progress is visible.

---

*Filed as proposal by Gina, 2026-04-08. Awaiting Debbie review. On acceptance this document becomes `knowledge/archive/adrs/ADR-0009_three_inbox_pka.md`.*
