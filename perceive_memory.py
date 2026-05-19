#!/usr/bin/env python3
"""
perceive_memory.py — Simplified Educational Version
hermes-perception: Memory Awareness Pipeline for LLM Agents

Core architecture:
  Session Start
      ↓
  perceive-memory.py
      ↓
  L0 (MEMORY.md) + L1 (Palace SessionDB) retrieval
      ↓
  Assemble structured summary (≤1500 chars)
      ↓
  Inject into system prompt
      ↓
  Agent naturally recalls relevant context

Full implementation: https://github.com/szqjl/hermes-perception
ADR-0001: https://github.com/szqjl/hermes-perception/blob/main/ADR-0001.md
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sqlite3
import sys
import time
from typing import Any

# ── Paths ────────────────────────────────────────────────────────────────────
HERMES_HOME = pathlib.Path(os.path.expanduser("~/.hermes"))
MEMORY_MD = HERMES_HOME / "MEMORY.md"
PALACE_DB = HERMES_HOME / "state.db"
CACHE_DIR = HERMES_HOME / "cache" / "perception"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_CHARS = 1500        # max summary length
TIMEOUT_MS = 3000       # 3s hard timeout
L0_MAXChars = 2000      # L0: read last 2000 chars of MEMORY.md
REDACTED = "[REDACTED]"

# ── Sensitive Information Redaction (P0 security) ─────────────────────────────
SENSITIVE_PATTERNS = [
    (re.compile(r"oc_[a-z0-9]{20,}"), REDACTED),           # Feishu IDs
    (re.compile(r"10\.\d+\.\d+\.\d+"), REDACTED),           # Internal IPs
    (re.compile(r"192\.168\.\d+\.\d+"), REDACTED),          # LAN IPs
    (re.compile(r"\bsk-[a-zA-Z0-9]{20,}"), REDACTED),       # API keys
    (re.compile(r"\bghp_[a-zA-Z0-9]{36}"), REDACTED),      # GitHub PATs
    (re.compile(r"-----BEGIN (PRIVATE|RSA|EC|OPENSSH) KEY-----"), REDACTED),
    (re.compile(r"api_key\s*[=:]\s*[\"']?\S+"), REDACTED),
    (re.compile(r"password\s*[=:]\s*[\"']?\S+"), REDACTED),
    (re.compile(r"Authorization:\s*Bearer\s+\S+"), REDACTED),
]


def redact(text: str) -> tuple[str, int]:
    """
    Redact sensitive information from text.
    Returns (redacted_text, replacement_count).
    """
    count = 0
    for pattern, replacement in SENSITIVE_PATTERNS:
        new_text, n = pattern.subn(replacement, text)
        if n > 0:
            count += n
            text = new_text
    return text, count


def hash_id(value: str) -> str:
    """Return SHA256[:8] for log anonymization."""
    return hashlib.sha256(value.encode()).hexdigest()[:8]


# ── L0: MEMORY.md Reader ──────────────────────────────────────────────────────
def read_l0() -> tuple[str, str | None]:
    """
    Read L0 memory layer: MEMORY.md (last 2000 chars = most recent).
    Returns (content, last_sync_timestamp).
    """
    if not MEMORY_MD.exists():
        return "", None

    raw = MEMORY_MD.read_text(encoding="utf-8")
    if len(raw) > L0_MAXChars:
        raw = raw[-L0_MAXChars:]   # LRU: keep latest

    last_sync = None
    try:
        conn = sqlite3.connect(str(PALACE_DB))
        row = conn.execute(
            "SELECT value FROM state_meta WHERE key='sync_obsidian_to_palace_last_run'"
        ).fetchone()
        last_sync = row[0] if row else None
        conn.close()
    except Exception:
        pass

    return raw, last_sync


# ── L1: Palace SessionDB Search ─────────────────────────────────────────────
def search_l1(query: str, current_session_id: str, top_k: int = 5) -> list[dict[str, Any]]:
    """
    Search L1 memory layer: Palace SessionDB via LIKE substring matching.
    Returns top-k sessions with matching message snippets.
    """
    if not query.strip() or not PALACE_DB.exists():
        return []

    try:
        short_query = query[:50]   # avoid oversized LIKE
        conn = sqlite3.connect(str(PALACE_DB))

        # Find messages matching the query
        matched_ids = [
            row[0] for row in conn.execute(
                "SELECT id FROM messages WHERE content LIKE ? LIMIT 200",
                (f"%{short_query}%",)
            ).fetchall()
        ]
        if not matched_ids:
            return []

        # Fetch sessions + snippets for matched messages
        placeholders = ",".join("?" * len(matched_ids))
        rows = conn.execute(f"""
            SELECT s.id, s.title, s.source, s.started_at,
                   GROUP_CONCAT(substr(m.content, 1, 120), ' || ')
            FROM messages AS m
            JOIN sessions AS s ON m.session_id = s.id
            WHERE m.id IN ({placeholders})
              AND s.id != ?
            GROUP BY s.id
            ORDER BY MAX(m.timestamp) DESC
            LIMIT ?
        """, matched_ids + [current_session_id, top_k]).fetchall()
        conn.close()

        return [
            {
                "session_id": row[0],
                "title": row[1] or "(no title)",
                "source": row[2],
                "started_at": row[3],
                "snippets": row[4] or "",
            }
            for row in rows
        ]
    except Exception as e:
        print(f"L1 search failed: {e}", file=sys.stderr)
        return []


# ── Summary Builder (ADR-0001 v5 format) ────────────────────────────────────
def build_summary(
    user_message: str,
    l0_content: str,
    l0_last_sync: str | None,
    l1_results: list[dict],
    l1_last_sync: str | None,
    redacted_count: int,
) -> str:
    """
    Assemble perception summary from L0 + L1 results.
    Format follows ADR-0001: ## Facts / ### Related Entities
    """
    lines = ["## 感知记忆摘要\n"]
    lines.append("> 以下来自关键词匹配（L0-L1），可能不完整，仅作参考。\n")

    # L0 Facts
    if l0_content:
        lines.append("### Facts（L0 记忆索引）\n")
        l0_safe, _ = redact(l0_content[:800])
        lines.append(f"```\n{l0_safe.strip()}\n```\n")
        if l0_last_sync:
            lines.append(f"_L0 last_sync: {l0_last_sync}_\n")

    # L1 Facts
    if l1_results:
        lines.append("### Facts（L1 最近相关会话）\n")
        for item in l1_results[:5]:
            snippets_safe, _ = redact(item.get("snippets", "")[:250])
            lines.append(
                f"- **[{item.get('title', '(no title)')}]"
                f"(source={item.get('source', '')})**：{snippets_safe}\n"
            )
        if l1_last_sync:
            lines.append(f"_L1 last_sync: {l1_last_sync}_\n")
    else:
        lines.append("### Facts（L1 最近相关会话）\n_L1 未召回相关内容_\n")

    # Related Entities
    if l1_results:
        lines.append("### Related Entities\n")
        for item in l1_results[:3]:
            lines.append(
                f"- {item.get('title', '?')}"
                f"（session#{hash_id(item.get('session_id', ''))}）\n"
            )

    # Query metadata
    user_msg_safe, user_redacted = redact(user_message[:100])
    lines.append(f"\n_查询词: {user_msg_safe}_\n")
    if redacted_count + user_redacted > 0:
        lines.append(f"_敏感信息替换次数: {redacted_count + user_redacted}_\n")

    result = "".join(lines)
    return result[:MAX_CHARS] + "\n\n<!-- truncated -->" if len(result) > MAX_CHARS else result


# ── Idempotency ───────────────────────────────────────────────────────────────
def mark_injected(session_id: str, summary: str) -> str:
    """
    Write {session_id}.summary (the ADR contract output)
    and touch {session_id}.injected (idempotency marker).
    """
    summary_path = CACHE_DIR / f"{session_id}.summary"
    injected_path = CACHE_DIR / f"{session_id}.injected"
    summary_path.write_text(summary, encoding="utf-8")
    injected_path.touch()
    return str(summary_path)


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    t0 = time.time()

    try:
        payload = json.loads(sys.argv[1])
    except (IndexError, json.JSONDecodeError):
        print("Usage: perceive_memory.py '<json_payload>'")
        print("Example: perceive_memory.py '{\"user_message\":\"ADR-0001\",\"session_id\":\"abc123\"}'")
        sys.exit(1)

    user_message: str = payload.get("user_message", "")
    session_id: str = payload.get("session_id", "")
    timeout_ms: int = int(payload.get("timeout_ms", TIMEOUT_MS))

    if not session_id:
        print("ERROR: session_id is required", file=sys.stderr)
        sys.exit(1)

    # ── L0 ──────────────────────────────────────────────────────────────────
    if (time.time() - t0) * 1000 >= timeout_ms:
        print(json.dumps({"status": "degraded", "reason": "timeout"}))
        return

    l0_content, l0_last_sync = read_l0()

    # ── L1 ──────────────────────────────────────────────────────────────────
    l1_results = []
    l1_last_sync = None
    total_redacted = 0

    if (time.time() - t0) * 1000 < timeout_ms:
        l1_results = search_l1(user_message, session_id)
        try:
            conn = sqlite3.connect(str(PALACE_DB))
            row = conn.execute(
                "SELECT value FROM state_meta WHERE key='sync_obsidian_to_palace_last_run'"
            ).fetchone()
            l1_last_sync = row[0] if row else None
            conn.close()
        except Exception:
            pass
        for item in l1_results:
            item["snippets"], n = redact(item.get("snippets", ""))
            total_redacted += n

    # ── Assemble + Output ───────────────────────────────────────────────────
    summary = build_summary(
        user_message=user_message,
        l0_content=l0_content,
        l0_last_sync=l0_last_sync,
        l1_results=l1_results,
        l1_last_sync=l1_last_sync,
        redacted_count=total_redacted,
    )

    output_path = mark_injected(session_id, summary)
    wall_ms = round((time.time() - t0) * 1000, 1)

    print(json.dumps({
        "status": "ok",
        "path": output_path,
        "wall_time_ms": wall_ms,
        "l0_chars": len(l0_content),
        "l1_count": len(l1_results),
        "redacted_count": total_redacted,
    }))


if __name__ == "__main__":
    main()
