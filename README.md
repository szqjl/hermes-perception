# hermes-perception: Hermes Agent Memory Awareness Pipeline

**Memory awareness for LLM agents** — enabling Hermes Agent to automatically recall relevant context at the start of every session, transforming passive retrieval into proactive memory emergence.

> Built on ADR-0001 (v1→v6,评审迭代). Integrates with Hermes Agent as a non-invasive subprocess module.

## What It Does

```
Session Start
    ↓
perceive-memory.py (perception pipeline)
    ↓
Retrieves from 5 memory layers → assembles structured summary (≤1500 chars)
    ↓
Injects into system prompt memory block
    ↓
Agent naturally recalls relevant context
```

**Current MVP:** L0 (MEMORY.md) + L1 (Palace SessionDB). L2 (Obsidian wiki) and L3 (gbrain graph) expansion planned.

## Background & Pain Points

Even with a 5-layer memory infrastructure in place:

1. **Memory layers are siloed** — searching L1 finds nothing in L2; searching L2 ignores L3 graph connections
2. **Passive retrieval only** — the agent only knows what it explicitly retrieves; it doesn't naturally recall context during conversation
3. **No session-to-session continuity** — every new session starts blank unless context is manually written to MEMORY.md

## Key Features

| Feature | Detail |
|---------|--------|
| **Non-invasive** | Subprocess call + file write; injection logic stays outside agent core |
| **Cross-platform** | Windows + Linux developed separately, merged with one `sys.executable` fix |
| **ADR-driven iteration** | v1→v6, each review round surfaced previously unconsidered edge cases |
| **Graceful degradation** | Timeout/failure silently skipped; agent starts normally regardless |
| **Fast** | ~630ms per run, built-in cache, 3s timeout fallback |
| **Idempotent** | `.injected` marker + content deduplication prevents double injection |

## Quick Start

**Automatic (no user action required):** Every new session (`/new` or first Feishu message) triggers the pipeline automatically.

**Manual trigger:**
```bash
python ~/.hermes/scripts/perceive-memory.py <session_id> summary
```

**View cache:**
```bash
ls ~/.hermes/perception_cache/
# {session_id}.summary   # perception summary
# {session_id}.injected  # idempotency marker
```

**Force regeneration (debug):**
```bash
rm ~/.hermes/perception_cache/{session_id}.summary
rm ~/.hermes/perception_cache/{session_id}.injected
# then start a new session
```

**Run integration tests:**
```bash
cd ~/.hermes/hermes-agent
python -m pytest tests/run_agent/test_perceive_memory_integration.py -v
```

## Project Structure

```
hermes-perception/
├── README.md        # This file — English version
├── README_CN.md    # 中文版
├── SKILL.md         # Hermes skill format (for agent loading)
└── ADR-0001.md      # Full architecture decision record
```

## Roadmap

- **L2 wiki/Sources retrieval** — connect so the agent can recall conclusions organized in the wiki
- **L3 gbrain graph retrieval** — connect so the agent knows the full association chain
- **Golden Set test cases** — end-to-end recall quality validation
- **Recall quality annotation** — `[high/medium/low]` reliability labels

## Related

[Hermes Agent](https://github.com/NousResearch/hermes-agent) — the perception pipeline is a memory-enhancement module for Hermes Agent.

---

**Topics:** hermes-agent ai-agent memory-awareness llm-memory context-injection perception-system agent-framework conversation-memory session-management retrieval-augmented
