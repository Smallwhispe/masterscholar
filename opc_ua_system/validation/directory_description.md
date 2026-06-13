# validation — 低代码 Schema 可信验证框架

## 目录结构

```
validation/
├── __init__.py              # 公开导出 TrustVerifier / VerificationReport / VerificationResult
├── verifier.py              # 中央编排器 TrustVerifier，调度六层验证并聚合报告
├── provenance.py            # ① 溯源追溯层 ProvenanceChecker
├── schema_validator.py      # ② Schema 协议合规层 SchemaValidator
├── structure_checker.py     # ③ 结构完整性层 StructureChecker
├── semantic_checker.py      # ④ 语义保真度层 SemanticChecker
├── data_consistency.py      # ⑤ 数据一致性层 DataConsistencyChecker
├── render_checker.py        # ⑥ 运行时验证层 RenderChecker
└── report.py                # 统一报告与结果数据结构
```

## 整体架构

```
TrustVerifier (中央编排器)
├── ① ProvenanceChecker       — 溯源追溯层
├── ② SchemaValidator          — Schema 协议合规层
├── ③ StructureChecker         — 结构完整性层
├── ④ SemanticChecker          — 语义保真度层
├── ⑤ DataConsistencyChecker   — 数据一致性层
└── ⑥ RenderChecker            — 运行时验证层

输出: VerificationReport (汇总六层评分与问题)
```

`TrustVerifier` 作为门面（Facade），一次调用 `verify_all()` 即可串行执行全部六层验证并汇总。框架的"可信"并非简单的二值判断，而是基于**分数量化** + **阈值判定** + **错误分级（fatal/error/warning/info）** 的多维度度量体系。

---

## 六层验证详解

### ① 溯源追溯层 (`ProvenanceChecker`)

**可信定义**：每个生成的 Schema 节点都必须能反向追溯到原始知识源（KG 三元组或 OPC UA Frame 节点）。

> 不能追溯的节点 = **幻影（phantom）**，不可信。

| 步骤 | 机制 | 可信保障 |
|------|------|----------|
| 构建源数据索引 | 从 KG TripleStore 提取所有实体名和关系对；从 Frame 提取所有 Variable 的 display_name / browse_name 和值 | 建立完整的「可溯源空间」 |
| 双源追溯 | 优先匹配 Frame Variable；再匹配 KG Property；对 Button 匹配 KG Method；对 Card 匹配 KG Entity | 交叉验证：Frame 和 KG 互为补充，任一匹配即可溯源 |
| 模糊匹配兜底 | 当精确匹配失败时，尝试子串模糊匹配（`label.lower() in tp.lower()`） | 容错机制，避免因命名细微差异误判 |
| 覆盖率阈值 | 可溯源覆盖率 ≥ 90% | 量化标准，不给模糊空间 |

**评分公式**：

```
score  = traceable_nodes / max(traceable + phantom, 1)
passed = len(phantom) == 0  （零幻影节点才算通过）
```

---

### ② Schema 协议合规层 (`SchemaValidator`)

**可信定义**：生成的 JSON 必须严格符合 LowCodeEngine 搭建协议规范。

| 检查项 | 可信机制 |
|--------|----------|
| 顶层必填字段 | 必须包含 `version`、`componentsMap`、`componentsTree`——缺失任一直接 `fatal` |
| 版本号有效性 | `version` 必须非空且包含 `.`（如 `1.0.0`）——防止版本缺失导致引擎无法解析 |
| 组件注册一致性 | `componentsTree` 中引用的每个组件名都必须在 `componentsMap` 中有注册——交叉引用检查，杜绝悬空引用 |
| 命名规范 | 组件名必须以大写字母开头——符合 React/LowCodeEngine 的组件命名协议 |
| JSExpression/JSFunction 格式 | 每个 `type=JSExpression/JSFunction` 的对象必须包含 `value` 字段 |
| 根节点类型 | `componentsTree` 根节点必须是 `Page` / `Block` / `Component` 之一 |

**评分公式**：

```
score  = Σ(passed_checks) / total_checks  （等权算术平均）
passed = len(issues) == 0  （零问题才算通过）
```

---

### ③ 结构完整性层 (`StructureChecker`)

**可信定义**：组件树必须是合法的、无缺陷的树形数据结构。

| 检查项 | 为什么这很重要 |
|--------|---------------|
| 根节点必须为 `Page` | Page 是 LowCodeEngine 的标准页面容器，非 Page 根节点无法正确渲染 |
| ID 唯一性 | 重复 ID 会导致 React reconciliation 失败、事件绑定错乱 |
| 无孤立 Variable | NumberPicker / Input / Switch 的父组件必须是 Card，否则无法正确关联 OPC UA Object 语义上下文 |
| 无空 Card | 空 Card 意味着 KG Object 属性全部丢失，是严重的信息丢失 |
| 嵌套深度 ≤ 20 | 过深嵌套导致渲染性能问题、用户体验差、可能是无限递归生成 bug |
| children 类型为 list | 非 list 的 children 会导致 LowCodeEngine 遍历崩溃 |

**评分公式**：

```
score = Σ(6项检查passed) / 6
```

---

### ④ 语义保真度层 (`SemanticChecker`)

**可信定义**：知识图谱中的语义关系必须被**完整地**映射到生成的 Schema 中。这是六层中最核心的可信层，直接衡量「KG 理解 → 代码生成」的信息保真度。

**映射关系表**：

| KG 关系 | Schema 映射目标 | 可信阈值 |
|---------|---------------|---------|
| `hasComponent` | Card → children 嵌套的子 Card | 覆盖率 ≥ 90% |
| `hasProperty` | Card → children 中的 NumberPicker / Input / Switch | 覆盖率 ≥ 80% |
| `hasOperation` | Card → children 中的 Button | 覆盖率 ≥ 80% |
| `connectedTo` / `controlledBy` | Card → children 嵌套 | 合并到 hasComponent 统计 |
| `subtypeOf` | prop 分组（当前未映射，记录为已知缺口） | 显式声明，不作为扣分项 |

**检测两类语义缺陷**：

- **遗漏（unmapped）**：KG 中有但输出中没有 → 信息丢失
- **幻影（phantom）**：输出中有但 KG 中没有 → 信息凭空产生

**评分公式**：

```
overall_coverage = 三类关系总交集 / 总 KG 关系数
score  = overall_coverage  （直接用覆盖率作为分数）
passed = score >= 0.85
```

这是六层中最严格的一层——如果 KG 定义了 10 个属性但只映射了 7 个，语义保真度只有 70%，**不及格**。

---

### ⑤ 数据一致性层 (`DataConsistencyChecker`)

**可信定义**：Frame 中的 OPC UA 运行时数据必须被**正确地**写入 Schema 的对应字段。

| 检查项 | 机制 |
|--------|------|
| 值一致性 | 比对 Frame 中的 `value` 与 Schema 中 `props.value` / `props.checked`。NumberPicker 用浮点容差 1e-6，Switch 用布尔解析，其他用字符串比较 |
| 类型映射正确性 | 验证 `data_type → 组件类型` 映射——Integer / Double → NumberPicker，Boolean → Switch |
| 元信息注入 | 检查 `SERVER_URL`、`FRAME_ID` 等 Frame 元信息是否正确注入 Schema 的 `constants` |
| 覆盖率统计 | 计算匹配变量数 / Schema 中出现的变量数 |

**评分公式（三层加权）**：

```
val_score   = 1.0 if 零值不一致 else 0.5
type_score  = 1.0 if 零类型映射错误 else 0.7
meta_score  = 1.0 if 元信息正确 else 0.5
score       = (val_score + type_score + meta_score) / 3
passed      = score >= 0.90
```

若未提供 Frame 数据，该层默认满分通过。

---

### ⑥ 运行时验证层 (`RenderChecker`)

**可信定义**：生成的 Schema 在 LowCodeEngine 中可以被实际渲染，不会产生运行时错误。采用**静态检查**模拟引擎解析过程。

| 检查项 | 机制 | 严重度 |
|--------|------|--------|
| 组件名可解析 | 遍历所有 `componentName`，验证每个都在 `componentsMap` 中有注册 | `error` |
| 方法引用一致性 | 检查 `Button.onClick` 引用的 `this.methods.xxx` 是否在 `Page.methods` 中存在——最易导致 JS 运行时崩溃 | `error` |
| Props 格式有效 | 检测 JSExpression / JSFunction 的 value 是否为空；检测是否误用旧版 `{{}}` 表达式 | `warning` |
| 内置组件注册 | 验证 Page / Card / NumberPicker / Input / Button / Typography 是否已注册 | `info` |

**通过标准**：

```python
passed = 所有 severity 为 "error" 或 "fatal" 的问题数为 0
```

warning 和 info 级别不阻止通过，但 error/fatal 级别一票否决。

---

## 报告聚合机制

`VerificationReport` 将六层结果汇总：

| 指标 | 计算方式 |
|------|---------|
| `overall_score` | 六层 score 的算术平均值 |
| `all_passed` | 六层 passed 均为 True |
| `total_issues` | 所有层 issues 数量之和 |
| `total_checks` | 所有层 checks 数量之和 |
| `layer_scores` | 各层分数字典 |

提供 `summary()` 格式化文本报告和 `to_dict()` JSON 导出。

---

## 设计哲学

```
                  ┌──────────────────────────────────────┐
                  │          TrustVerifier               │
                  │      "可信" = 六维正交度量            │
                  └──────────────────────────────────────┘
                                    │
       ┌────────┬────────┬─────────┼─────────┬────────┬────────┐
       ▼        ▼        ▼         ▼         ▼        ▼        ▼
    ①溯源    ②协议    ③结构     ④语义     ⑤数据    ⑥运行时
    "从哪来"  "合规否" "健壮否"  "保真否"  "准确否"  "能跑否"
    ─────────────────────────────────────────────────────────────
    数据源  →  规范层  →  结构层  →  语义层  →  数据层  →  终端层
```

### 核心原则

1. **正交性**：六层各自关注不同的质量维度，互不重叠——溯源关注来源、协议关注格式、结构关注拓扑、语义关注信息保真、数据关注值准确性、运行时关注可执行性。

2. **量化度量**：每层都有明确的 0~1 评分公式和阈值，避免了粗粒度的「通过/不通过」二元判断，允许不同程度可信度量。

3. **追溯闭环**：建立从「知识源（KG + Frame）→ 生成 → 验证 → 报告」的完整闭环，每层检查项对应具体质量缺陷类型（幻影节点、悬空引用、类型映射错误等），确保问题可定位、可修复。

4. **分层错误等级**：

   | 等级 | 含义 |
   |------|------|
   | `fatal` | 协议层缺失必填字段，系统无法运行 |
   | `error` | 运行时必然崩溃（如悬空组件引用、方法未定义） |
   | `warning` | 潜在问题（如孤立 Variable、空 Card、命名不规范） |
   | `info` | 改进建议（如建议注册常用组件） |
