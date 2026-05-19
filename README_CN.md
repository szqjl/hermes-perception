# hermes-perception：Hermes Agent 记忆感知管线

**LLM Agent 记忆感知系统** — 让 Hermes Agent 在每次会话开头自动想起相关上下文，把"被动搜索"变成"主动浮现"。

> 基于 ADR-0001 架构决策（v1→v6 评审迭代），作为非侵入式子进程模块与 Hermes Agent 无缝集成。

## 核心机制

```
Session Start
    ↓
感知管线（perceive-memory.py）
    ↓
从五层记忆检索 → 拼装结构化摘要（≤1500 字符）
    ↓
注入 system prompt 记忆区块
    ↓
Agent 自然想起相关上下文
```

**当前 MVP：** L0（MEMORY.md）+ L1（Palace SessionDB）。L2（Obsidian wiki）、L3（gbrain 图谱）扩展规划中。

## 背景与痛点

即使已有五层记忆体系，仍存在三个问题：

1. **记忆各层孤立** — 搜 L1 搜不到 L2，搜 L2 不知道 L3 关联，没有跨层联动
2. **被动等待检索** — agent 不会主动想起，必须靠用户触发或主动调用工具
3. **会话间没有记忆延续** — 每次新 session 都是白板，上周做的事 agent 完全不记得

## 项目亮点

| 亮点 | 说明 |
|------|------|
| **不侵入核心代码** | subprocess 调用，写入文件，注入函数独立于 agent 核心逻辑 |
| **跨平台** | Windows + Linux 各自开发后合并，只修了一个 `sys.executable` |
| **ADR + 评审驱动迭代** | v1→v6，每轮评审都发现之前没考虑到的问题 |
| **优雅降级** | 超时/失败静默跳过，agent 正常启动 |
| **快** | ~630ms/次，内置缓存，3s 超时兜底 |
| **双层幂等性保障** | `.injected` 标记 + 内容去重，防止重复注入 |
| **共享核心，独立部署** | `perceive-memory.py` 唯一共享脚本，双端各自注入 |

## 怎么运行

**对用户无感使用：** 无需任何操作，每次新会话自动运行。

**手动触发：**
```bash
python ~/.hermes/scripts/perceive-memory.py <session_id> summary
```

**查看缓存：**
```bash
ls ~/.hermes/perception_cache/
# {session_id}.summary   # 感知摘要
# {session_id}.injected # 幂等标记
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

## 项目文档

```
hermes-perception/
├── README.md        # 英文版（SEO 优化）
├── README_CN.md      # 本文件 — 中文版
├── SKILL.md          # Hermes skill 格式，供 agent 加载使用
└── ADR-0001.md       # 完整架构决策记录（含接口契约、注入机制、L0-L4 设计）
```

## 今后展望

- **L2 wiki/Sources 检索扩展** — 接进来让 agent 能想起 wiki 里整理过的结论
- **L3 gbrain 图谱检索扩展** — 接进来让 agent 知道关联链条
- **Golden Set 测试用例** — 端到端验证召回质量
- **召回质量评估** — `[high/medium/low]` 可靠性标注

## 当前状态

**✅ MVP + run_agent.py 双端集成完成**（2026-05-19）

| 组件 | 状态 |
|------|------|
| `perceive-memory.py` v1.4 | ✅ 8/8 集成测试通过 |
| run_agent.py 注入（pingshen CLI） | ✅ |
| run_agent.py 注入（hermes-win Windows） | ✅ |
| ADR-0001 v6 | ✅ 双评通过 |

---

**关联项目：** [hermes-agent](https://github.com/NousResearch/hermes-agent) — 本感知管线是 Hermes Agent 的记忆增强模块
