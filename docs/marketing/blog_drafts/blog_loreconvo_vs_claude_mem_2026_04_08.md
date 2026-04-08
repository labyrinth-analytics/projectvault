---
title: "No Chroma, No RAM Spikes, No Headaches: How LoreConvo Approaches Claude Memory Differently"
author: Debbie Shapiro
date: 2026-04-08
status: draft
tags: [loreconvo, claude-mem, claude-plugins, memory, mcp, comparison]
---

# No Chroma, No RAM Spikes, No Headaches: How LoreConvo Approaches Claude Memory Differently

If you have spent any real time using claude-mem on a serious project, you have probably watched your laptop fans spin up at some point and thought, "wait, what is eating 30 gigs of RAM right now?" You check Activity Monitor, and there it is: a Chroma vector store happily indexing your entire conversation history into memory. It is not a bug. It is the architecture working exactly as designed. It is also the reason I ended up building something different.

This post is about that different thing, LoreConvo, and how it stacks up against claude-mem, the giant of the Claude memory plugin space. I want to be upfront before we go any further: claude-mem is a great project. Forty-five thousand GitHub stars do not happen by accident. The team behind it solved a real problem and shipped it before anyone else did, and a lot of what LoreConvo does at all is downstream of the trail they blazed. So this is not a takedown. It is a comparison from someone who tried claude-mem, hit the edges of it on her own workflow, and decided to build a tool that makes a different set of trade-offs.

## What claude-mem gets right

Let me give credit where it is due. claude-mem nailed a few things that are genuinely hard.

The first is zero-friction capture. You install it, you keep working, and your conversations get remembered. You do not have to think about it. For a lot of users, especially solo developers who just want Claude to "remember the thing we figured out last Tuesday," that automatic behavior is exactly right. The lift is invisible.

The second is semantic recall. Because claude-mem uses ChromaDB under the hood, it can do real vector similarity search across everything you have ever said. Ask "what did we decide about caching last month" and it will pull up sessions even if you used totally different words at the time. That is powerful, and it is the kind of thing a pure keyword search cannot give you.

The third is community. Forty-five thousand stars, a Discord, regular releases, integration guides for every major IDE. It is a real ecosystem, and you do not get that overnight.

If claude-mem is working for you, this post is not trying to talk you out of it. Keep using it. The rest of this post is for the people who hit a wall with it, and for the people who never tried it because the architecture made them nervous in the first place.

## Where it starts to hurt

Here is the thing about ChromaDB. It is a great vector store. It is also a heavyweight dependency. On a small project with a few dozen sessions, you will never notice. But once you start indexing thousands of conversation chunks, and once those chunks include long code blocks and stack traces and full file contents, the memory profile gets ugly fast. I have seen reports of claude-mem holding 30 to 35 gigabytes of resident memory on power users with deep history. That is not a typo. Thirty-five gigabytes.

For someone like me, working out of a Mac with 32 gigs total, that is a non-starter. I am usually running Postgres, a couple of dev servers, a browser with too many tabs, and Claude itself. I do not have 35 gigs to spare for a memory plugin.

The Chroma dependency causes a few other smaller paper cuts too. Installation is more complicated than it needs to be. Upgrades sometimes require you to rebuild your index. If something goes wrong with the vector store, debugging it means learning Chroma internals, which is a whole second project you did not sign up for.

And then there is the auto-capture-everything design. It is a feature most of the time, but it is also noise. Every "let me try that again" and "wait, never mind" gets indexed alongside the actual decisions. When you go to recall something later, you are wading through a lot of conversational sediment to find the thing you actually wanted. Some users love this. Others find it gets in the way.

Last thing on the limits side: claude-mem is Claude Code only. If you do half your work in Claude Code, half in Cowork, and occasionally drop into Claude Chat to brainstorm something on your phone, claude-mem can only see the Code half. The other surfaces are dark to it.

## The architectural choice behind LoreConvo

When I sat down to build LoreConvo, the very first decision was: no vector database. SQLite only. Full text search through SQLite FTS5, which is built into the SQLite binary you already have on every Mac and Linux box on earth.

That one decision drives almost everything else about how LoreConvo feels. Memory footprint goes from gigabytes to megabytes. Installation is `pip install` and a config file edit. There is no separate service to start, no index to rebuild on upgrade, no background process eating CPU while you sleep. The whole database is one file at `~/.loreconvo/sessions.db`. You can back it up by copying it. You can inspect it with the `sqlite3` command line tool. If you ever decide LoreConvo is not for you, you can grep your own data out of it without anyone's help.

Is FTS5 as smart as a vector store? No. It cannot do semantic similarity. If you search for "caching" it will not automatically surface a session where you talked about "memoization." That is a real trade-off, and I want to name it clearly. What you get in exchange is a tool that runs forever on a potato and never surprises you with a 35 gigabyte resident set.

The other big architectural choice was structured capture instead of auto capture. LoreConvo does not try to remember everything you said. It tries to remember the things that mattered. Each session has explicit fields for decisions, artifacts produced, open questions, and a free-form summary. You save a session at the end of a working block, and you say what was actually accomplished. It takes ten seconds and you end up with a memory that reads more like an engineering log than a conversation transcript.

The upside of this is signal density. When you recall a past session six months later, you are not scrolling through banter. You are reading "we decided X because Y, here are the files that changed, here is the question we never resolved." That is the form most people actually want when they come back to old work.

The downside is that you have to actually save sessions. There are auto-save hooks that help, but the philosophy is "the human knows what mattered, so let the human say so."

## The cross-surface bridge

Here is the thing I am proudest of. LoreConvo runs on all three Claude surfaces. Claude Code, Cowork, and Claude Chat. The same SQLite file is the source of truth for all of them.

What this means in practice is that I can be deep in Claude Code at my desk debugging something, save a session at the end of the day, and the next morning open Cowork on the couch, ask "what did we figure out about that auth bug last night," and pull up the exact decisions I made at my desk. Then later in the week I can be on my phone in a coffee shop using Claude Chat, brainstorm a follow-up idea, save that as a session, and it joins the same memory pool.

claude-mem cannot do this. It is Code only, by design. If you live entirely in Claude Code that does not matter. If you do not, it is the whole ball game.

LoreConvo also exposes 12 MCP tools versus claude-mem's 4. Some of that is just surface area, but the practical effect is that you have more ways to query and tag and link sessions to projects. You can pull "all sessions tagged loreconvo where the surface was code" and get a clean answer. The richer tool set is there for the people who want to actually shape their memory, not just feed it.

## Honest guidance: when to choose which

I am not trying to convince everyone to switch. Here is how I would actually think about it.

Choose claude-mem if you live entirely in Claude Code, you have plenty of RAM to spare, you want zero-friction automatic capture, and semantic similarity recall is important to your workflow. It is a solid, mature, well-supported tool and it will serve you well.

Choose LoreConvo if you use more than one Claude surface, you are running on a memory-constrained machine, you prefer structured logs to raw transcripts, you want a tool you can fully understand and back up by copying one file, or you are the kind of person who gets twitchy about adding heavyweight dependencies you do not strictly need. LoreConvo is also the better fit if you are building agent pipelines and need other agents to read and write the same memory store, because the SQLite design makes that trivially safe.

Honestly, you can also use both. They live in different places and they do not interfere with each other. I know a couple of people who let claude-mem do its automatic thing inside Code and use LoreConvo to write deliberate cross-surface session logs. There is no rule that says you have to pick one.

## Try it

LoreConvo is open source under BSL 1.1, free for personal use, and the install is one command after you clone the repo. The GitHub link is below. If you try it and it works for you, I would love to hear about it. If you try it and it does not, I would love to hear about that too, because every piece of feedback I have gotten so far has made the next version better.

GitHub: https://github.com/labyrinth-analytics/loreconvo

And again, real talk, thank you to the claude-mem team for proving this whole category of tool was worth building. LoreConvo only exists because they made the case first.
