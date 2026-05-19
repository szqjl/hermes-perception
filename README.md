# Hermes 记忆感知系统

让 Hermes Agent 在每次会话开头**自动想起**相关记忆，而不是被动搜索。

> ADR-0001 是该系统的架构决策记录，v1→v6 经过多轮评审迭代。

## 背景

即使已有五层记忆体系（Obsidian wiki、Palace SessionDB、MEMORY.md 等），agent 仍然面临三个问题：

1. **记忆各层孤立** — 搜 L1 搜不到 L2，搜 L2 不知道 L3
2. **被动等待检索** — agent 不会主动想起，必须靠用户触发
3. **会话间没有记忆延续** — 每次新 session 都是白板

感知管线的目标：**把"被动搜索"变成"主动浮现"**。Session 一起动，agent 就能知道"这个用户上周在搞 ADR-0001"。

## 核心机制

```
Session Start
    ↓
感知管线（perceive-memory.py）
    ↓
从五层记忆检索 → 拼装结构化摘要（≤1500 字符）
    ↓
注入 system prompt 的记忆区块
    ↓
Agent 自然想起相关上下文
```

**当前 MVP：L0（MEMORY.md）+ L1（Palace SessionDB）**
- L2（Obsidian wiki）、L3（gbrain 图谱）扩展规划中

## 项目亮点

- **不侵入核心代码** — subprocess 调用，写入文件，注入函数独立
- **跨平台** — Windows + Linux 各自开发后合并，只修了一个 `sys.executable`
- **ADR + 评审驱动迭代** — v1→v6，每轮评审都让方案更扎实
- **优雅降级** — 超时/失败静默跳过，agent 正常启动
- **快** — 630ms/次，内置缓存，3s 超时兜底
- **双层幂等性保障** — `.injected` 标记 + 内容去重

## 怎么运行

**用户无感使用：** 无需任何操作，每次新会话自动运行。

**手动触发：**
```bash
python ~/.hermes/scripts/perceive-memory.py <session_id> summary
```

**查看缓存：**
```bash
ls ~/.hermes/perception_cache/
# {session_id}.summary   感知摘要
# {session_id}.injected   幂等标记
```

**调试（强制重新生成）：**
```bash
rm ~/.hermes/perception_cache/{session_id}.summary
rm ~/.hermes/perception_cache/{session_id}.injected
```

**运行测试：**
```bash
cd ~/.hermes/hermes-agent
python -m pytest tests/run_agent/test_perceive_memory_integration.py -v
```

## 当前状态

**✅ MVP + run_agent.py 双端集成完成**（2026-05-19）

| 组件 | 状态 |
|------|------|
| `perceive-memory.py` v1.4 | ✅ 8/8 集成测试通过 |
| run_agent.py 注入（pingshen CLI） | ✅ |
| run_agent.py 注入（hermes-win Windows） | ✅ |
| ADR-0001 v6 | ✅ 双评通过 |

## 文档结构

```
hermes-perception/
├── README.md              # 本文件，项目概览
├── SKILL.md               # Hermes skill 格式，供 agent 加载使用
└── ADR-0001.md           # 完整架构决策记录（含接口契约、注入机制、L0-L4 设计）
```

## 今后展望

- L2 wiki/Sources 检索扩展
- L3 gbrain 图谱检索扩展
- Golden Set 测试用例（端到端验证召回质量）
- 召回质量评估（`[high/medium/low]` 可靠性标注）

---

**关联项目：** [hermes-agent](https://github.com/NousResearch/hermes-agent) — 本感知管线是 Hermes Agent 的记忆增强模块
