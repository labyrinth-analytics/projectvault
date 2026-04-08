# Social Drafts: LoreConvo vs claude-mem (2026-04-08)

Status: DRAFT for Debbie's review. Do not publish.

---

## LinkedIn Post (~200 words)

claude-mem is the dominant Claude memory plugin for a reason. 45K GitHub stars, zero-friction capture, real semantic search. The team behind it solved a hard problem and shipped it first. Genuine respect.

But if you are a power user, you have probably noticed something: ChromaDB under the hood means RAM usage that can climb past 30 gigs on deep histories. On a 32 gig laptop running Postgres, a browser, and Claude itself, that is a non-starter.

That is the gap LoreConvo fills.

LoreConvo is SQLite only. No vector store, no separate service, no rebuild-the-index upgrades. Memory footprint stays in the megabytes. The whole database is one file you can back up by copying it. Search runs through SQLite FTS5, which is built into every Mac and Linux box already.

Three more differences worth knowing:
1. Structured session capture (decisions, artifacts, open questions) instead of auto-capture-everything
2. Bridges all three Claude surfaces: Code, Cowork, and Chat. claude-mem is Code only.
3. 12 MCP tools versus claude-mem's 4

Both tools are legitimate. Pick the one that fits your machine and your workflow. Full comparison and honest guidance on the blog.

#ClaudeAI #DeveloperTools #OpenSource

---

## Twitter / X Thread (6 tweets)

**1/**
claude-mem is the king of Claude memory plugins. 45K stars, real semantic recall, zero-friction capture. Massive credit to that team for proving the category.

But there is a catch most heavy users have noticed, and it is the reason I built something different.

**2/**
The catch is ChromaDB. It is a great vector store. It is also heavy. Power users have reported claude-mem holding 30 to 35 GB of RAM on deep histories.

On a 32 GB laptop running everything else, that is the whole machine.

**3/**
LoreConvo takes the other path. SQLite only. Full text search through FTS5, which is built into the SQLite binary you already have. The entire database is one file at ~/.loreconvo/sessions.db.

Memory footprint: megabytes, not gigabytes.

**4/**
Trade-off, named clearly: FTS5 is not as smart as a vector store. No semantic similarity. If that matters more to you than RAM, claude-mem is the right call.

If you want a tool that runs forever on a potato and never surprises you, keep reading.

**5/**
Two more differences:

LoreConvo captures structured sessions (decisions, artifacts, open questions) instead of auto-capturing every line. Higher signal density when you come back six months later.

LoreConvo runs on Code, Cowork, and Chat. claude-mem is Code only.

**6/**
Both tools are legit. Use whichever fits your machine and your workflow. You can even run both.

Full honest comparison on the blog, link below. And again, thank you to the claude-mem team for going first.

GitHub: https://github.com/labyrinth-analytics/loreconvo

---

## Reddit r/ClaudeAI Comment (~150 words)

claude-mem user here too, and yeah, it is the dominant memory plugin for good reason. The team shipped it first, the semantic recall is genuinely useful, and the community around it is real.

That said, if anyone in this thread has been hitting the RAM ceiling (Chroma can hold 30+ GB on deep histories), there is a lighter-weight alternative I have been working on called LoreConvo. SQLite only, no vector store, the whole DB is one file. Trade-off is no semantic similarity, just FTS5 keyword search. Different design choice, not a better one in every situation.

It also bridges Code, Cowork, and Chat instead of being Code only, which mattered for my workflow.

Not trying to start a turf war. Both tools are valid and the comparison post I just wrote tries to be honest about when each one wins. Happy to answer questions if anyone is curious.
