---
name: hermes-memory
description: Hermes 记忆感知系统 — 让 agent 在每次会话开头自动想起相关上下文
---

# Hermes 记忆感知系统（ADR-0001）

让 Hermes Agent 在每次会话开头**自动想起**相关记忆，而不是被动搜索。

## 背景与痛点

**现有基础设施：**

良总已经搭建了五层记忆体系：
- **Obsidian wiki** — L2 wiki 层，82 个文件，系统整理过项目结论和技术决策
- **LLM Wiki** — 基于 wiki 的语义检索层
- **Palace SessionDB** — L1 会话历史，744 sessions，22,292 条消息
- **MEMORY.md** — L0 全局索引

基础设施已经很完整了。

**但仍存在的问题：**

1. **记忆各层孤立** — L0~L4 各自为政，agent 搜 L1 搜不到 L2 的东西，搜 L2 不知道 L3 的关联。没有跨层联动。

2. **被动等待检索** — agent 只能靠用户触发或主动调用工具才能拿到上下文，正常对话时不会自然想起相关记忆。

3. **会话间没有记忆延续** — 每次新 session 都是白板。上一周做的东西，除非手动写进 MEMORY.md，否则 agent 完全不记得。

感知管线的目标：把"被动搜索"变成"主动浮现"。

## 核心机制

```
Session Start
    ↓
感知管线（perceive-memory.py）
    ↓
从五层检索 → 拼装摘要（≤1500 字符）
    ↓
注入 system prompt
    ↓
Agent 自然想起
```

## 怎么运行

**对用户：**

无需任何操作。每次新会话开始（`/new` 或飞书发来第一条消息），感知管线自动运行，摘要自动注入。

**手动触发感知管线：**

```bash
python ~/.hermes/scripts/perceive-memory.py <session_id> summary
```

**查看缓存文件：**

```bash
ls ~/.hermes/perception_cache/
# {session_id}.summary   感知摘要内容
# {session_id}.injected 幂等标记
```

**调试（强制重新生成）：**

```bash
rm ~/.hermes/perception_cache/{session_id}.summary
rm ~/.hermes/perception_cache/{session_id}.injected
# 再开一个新 session
```

**运行测试：**

```bash
cd ~/.hermes/hermes-agent
python -m pytest tests/run_agent/test_perceive_memory_integration.py -v
```

## 项目亮点

1. **不侵入核心代码** — subprocess 调用，写入文件，注入函数独立于 agent 核心逻辑
2. **跨平台** — Windows + Linux 各自开发后合并，只修了一个 `sys.executable`
3. **ADR + 评审驱动迭代** — v1→v6，每轮评审都发现之前没考虑到的问题
4. **优雅降级** — 超时/失败静默跳过，agent 正常启动
5. **双层幂等性保障** — `{session_id}.injected` 标记 + 内容去重
6. **快** — 630ms/次，内置缓存，3s 超时兜底
7. **共享核心，独立部署** — `perceive-memory.py` 唯一共享脚本，双端各自注入

## 今后展望

- **L2 wiki/Sources 检索扩展** — 接进来让 agent 能想起 wiki 里整理过的结论
- **L3 gbrain 图谱检索扩展** — 接进来让 agent 知道关联链条
- **Golden Set 测试用例** — 端到端验证召回质量
- **召回质量评估** — `[high/medium/low]` 可靠性标注

## 项目文档

- **ADR-0001 完整文档**：`wiki/projects/hermes-memory-awareness/ADR-0001.md`
- **完整 README**：`wiki/projects/hermes-memory-awareness/README.md`
- **感知管线脚本**：`~/.hermes/scripts/perceive-memory.py`
- **注入代码**：`agent/conversation_loop.py`（`_inject_perception_summary` + `_inject_into_system_prompt`）

## 状态

**✅ MVP + run_agent.py 双端集成完成**（2026-05-19）

- `perceive-memory.py` v1.4，8/8 集成测试通过
- pingshen（CLI）✅ 8/8
- hermes-win（Windows）✅ 8/8
