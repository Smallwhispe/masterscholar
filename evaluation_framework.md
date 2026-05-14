# 生成代码质量与验证框架可信度 — 全方面评价指标体系

> 适用对象：OPC UA 知识图谱自动建模系统中低代码 Schema 的生成质量评价与验证框架的元评估

---

## 目录

- [第一部分：生成代码质量评价指标](#第一部分生成代码质量评价指标)
  - [A. 结构质量](#a-结构质量)
  - [B. 语义质量](#b-语义质量)
  - [C. 数据质量](#c-数据质量)
  - [D. 运行质量](#d-运行质量)
  - [E. 可维护质量](#e-可维护质量)
  - [F. 溯源质量](#f-溯源质量)
- [第二部分：验证框架可信度评价指标](#第二部分验证框架可信度评价指标)
  - [G. 覆盖全面性](#g-覆盖全面性)
  - [H. 检测有效性](#h-检测有效性)
  - [I. 一致性与可复现性](#i-一致性与可复现性)
  - [J. 可解释性](#j-可解释性)
  - [K. 工程实用性](#k-工程实用性)
- [第三部分：综合评分计算](#第三部分综合评分计算)
- [第四部分：阈值建议与告警策略](#第四部分阈值建议与告警策略)

---

# 第一部分：生成代码质量评价指标

> 评价对象：`LowcodeGenerator.convert(kg_store, frame)` 输出的 `ProjectSchema JSON`

## A. 结构质量

### A.1 节点完整性 (Node Completeness)

| 指标 | 公式 | 阈值 | 当前来源 |
|------|------|:--:|----------|
| 根节点正确率 | `1 if root.componentName=='Page' else 0` | = 1.00 | `structure_checker` |
| ID 唯一率 | `unique_ids / total_ids` | = 1.00 | `structure_checker` |
| 嵌套深度合规率 | `nodes_with_depth≤20 / total_nodes` | = 1.00 | `structure_checker` |
| children 类型正确率 | `nodes_with_valid_children_type / total_nodes_with_children` | = 1.00 | `structure_checker` |

### A.2 拓扑合理性 (Topology Soundness)

| 指标 | 公式 | 阈值 |
|------|------|:--:|
| 无孤立 Variable 率 | `1 - orphan_vars / total_vars` | ≥ 0.95 |
| 无空 Card 率 | `1 - empty_cards / total_cards` | ≥ 0.90 |
| 无环路 | 树深度遍历无重复节点 | = 1.00 |
| 叶节点类型合法率 | 叶节点中 Variable/Method/Button 占比 | — （参考值） |

### A.3 协议合规性 (Protocol Conformance)

| 指标 | 公式 | 阈值 | 当前来源 |
|------|------|:--:|----------|
| 必填字段完整率 | `present_required / total_required` | = 1.00 | `schema_validator` |
| 组件注册覆盖率 | `registered_components / used_components` | = 1.00 | `schema_validator` |
| 命名规范合规率 | `valid_names / total_names` | = 1.00 | `schema_validator` |
| 特殊类型格式正确率 | `valid_expressions / total_expressions` | = 1.00 | `schema_validator` + `render_checker` |

---

## B. 语义质量

### B.1 语义覆盖率 (Semantic Coverage)

| 指标 | 公式 | 阈值 | 当前来源 |
|------|------|:--:|----------|
| hasComponent 映射率 | `mapped_hasComponent / total_kg_hasComponent` | ≥ 0.90 | `semantic_checker` |
| hasProperty 映射率 | `mapped_hasProperty / total_kg_hasProperty` | ≥ 0.80 | `semantic_checker` |
| hasOperation 映射率 | `mapped_hasOperation / total_kg_hasOperation` | ≥ 0.80 | `semantic_checker` |
| **总体语义覆盖率** | `total_mapped / total_mappable_kg_triples` | ≥ 0.85 | `semantic_checker` |

### B.2 语义准确率 (Semantic Precision)

| 指标 | 公式 | 阈值 |
|------|------|:--:|
| 关系映射正确率 | `correct_relation_maps / total_mapped_relations` | ≥ 0.95 |
| 伪影率（Phantom Rate） | `phantom_relations / total_output_relations` | ≤ 0.10 |
| known-gap 记录率 | 已知但未映射的关系类型是否被标记 | = 1.00（检查 known_gaps 字段） |

**关键定义**：
- **伪影（Phantom）**：输出中存在的组件关系，但在 KG 中找不到对应的三元组。例如输出了一个 `Card(Spindle) > children 包含 NumberPicker(XYZ)`，但 KG 中没有 `Spindle → hasProperty → XYZ`
- **漏映射**：KG 中存在的三元组，在输出中找不到对应表示

### B.3 语义保真度分层

| 层级 | 含义 | 测量方法 |
|------|------|----------|
| L1 实体映射 | KG 实体名是否出现为 Card.title 或 Typography.children | 字符串精确匹配 |
| L2 关系映射 | hasComponent/hasProperty/hasOperation 是否映射为正确的组件关系 | 父子关系比对 |
| L3 属性类型映射 | Variable.type → propType + 对应 setter | 类型映射表比对 |
| L4 操作语义映射 | Method → Button + onClick 事件绑定 | JSExpression 引用检查 |

---

## C. 数据质量

### C.1 数值精确性 (Value Accuracy)

| 指标 | 公式 | 阈值 | 当前来源 |
|------|------|:--:|----------|
| **值精确一致率** | `matched_values / total_variable_nodes` | ≥ 0.95 | `data_consistency` |
| 数值型误差容忍率 | `abs(schema_val - frame_val) < 1e-6` 的 Variable 占比 | = 1.00 | `data_consistency` |
| 布尔型精确率 | Switch.checked 与 Frame.bool_value 一致 | = 1.00 | `data_consistency` |
| 字符串型精确率 | Input.value 与 Frame.string_value 一致 | = 1.00 | `data_consistency` |

### C.2 类型映射正确性 (Type Mapping)

| 指标 | 公式 | 阈值 |
|------|------|:--:|
| data_type → prop_type 正确率 | `correct_type_maps / total_variables` | ≥ 0.95 |
| data_type → 组件类型正确率 | UInt32→NumberPicker, Boolean→Switch, String→Input | ≥ 0.95 |

当前映射表：
```
Integer/UInt16/UInt32/Int*/Double/Float → NumberPicker
Boolean → Switch
String/ByteString → Input
```

### C.3 元信息一致率 (Metadata Consistency)

| 指标 | 检查项 | 阈值 |
|------|------|:--:|
| SERVER_URL 一致性 | `schema.constants.SERVER_URL == frame.server_url` | = 1.00 |
| FRAME_ID 一致性 | `schema.constants.FRAME_ID == frame.frame_id` | = 1.00 |
| 设备类型一致性 | `schema.constants.DEVICE_TYPE == device_type` | = 1.00 |
| 时间戳存在性 | `schema.meta.gmt_create` 非空 | = 1.00 |

---

## D. 运行质量

### D.1 静态可渲染性 (Static Renderability)

| 指标 | 公式 | 阈值 | 当前来源 |
|------|------|:--:|----------|
| 组件名全部可解析 | `all_used_in_map` | = 1.00 | `render_checker` |
| 事件方法引用全部存在 | `all_method_refs_exist` | = 1.00 | `render_checker` |
| JSExpression/JSFunction 格式有效 | `valid_special_types / total_special_types` | = 1.00 | `render_checker` |

### D.2 动态渲染质量（需沙箱环境）

| 指标 | 公式 | 阈值 |
|------|------|:--:|
| 无 React 渲染异常 | `1 if no render error else 0` | = 1.00 |
| 首次渲染时间 | 从 schema 注入到首屏绘制的时长 | — （参考值） |
| 组件实例化成功率 | `instantiated / attempted` | = 1.00 |

### D.3 功能可用性

| 指标 | 检查项 |
|------|------|
| 数据绑定可用 | `{{变量}}` 或 `JSExpression` 能否正确解析 |
| 事件响应可用 | Button.onClick 能否触发对应 method |
| 状态管理可用 | Page.state 能否被 children 引用 |

---

## E. 可维护质量

### E.1 可读性

| 指标 | 说明 |
|------|------|
| 缩进格式 | JSON 是否 pretty-print（indent=2） |
| 组件深度 | 最大嵌套深度 ≤ 10（推荐值） |
| 命名一致性 | Card.title 与源 KG 实体名一致 |
| 注释/描述 | `description` 字段是否包含生成来源信息 |

### E.2 可修改性

| 指标 | 说明 |
|------|------|
| 组件粒度 | 单 Card 单职责（不合并多个 Object） |
| 属性分组 | NumberPicker 是否按父 Object 组织在对应 Card 下 |
| 事件解耦 | Button.onClick 引用 `this.methods.xxx` 而非内联大段代码 |

### E.3 可扩展性

| 指标 | 说明 |
|------|------|
| componentsMap 扩展性 | 新增组件只需添加一条 Map 条目 |
| 资产包兼容性 | 生成的 schema 是否可直接放入 assets.json |

---

## F. 溯源质量

### F.1 溯源覆盖率 (Provenance Coverage)

| 指标 | 公式 | 阈值 | 当前来源 |
|------|------|:--:|----------|
| **节点可溯源率** | `traceable_nodes / total_nodes` | ≥ 0.90 | `provenance` |
| 幻影节点率 | `phantom_nodes / total_nodes` | ≤ 0.10 | `provenance` |
| 溯源来源丰富度 | 同时有 KG + Frame 双重来源的节点占比 | — （越高越好） |

### F.2 溯源信息完整性

| 指标 | 说明 |
|------|------|
| 源三元组可定位 | 每个输出节点能反向找到对应的 `Triple(head, relation, tail)` |
| 源帧节点可定位 | 每个 Variable 输出能反向找到对应的 `frame.nodes[node_id]` |
| source 字段标记 | 输出 Schema 中是否携带 source 元信息（`kg` / `frame` / `merged`） |

---

# 第二部分：验证框架可信度评价指标

> 评价对象：`TrustVerifier.verify_all()` 的验证过程与结果

## G. 覆盖全面性

### G.1 维度覆盖

| 指标 | 当前状态 | 理想值 |
|------|:--:|:--:|
| 验证层级数 | 6 层 | 6+ |
| 每层检查项数 | 4~6 项/层 | 5~10 项/层 |
| 覆盖问题类型 | fatal / error / warning / info 四类 | 四类 + hint |
| KG 三元组关系类型覆盖 | hasComponent / hasProperty / hasOperation / connectedTo / controlledBy / subtypeOf | 全部 IMKG 定义的关系 |

### G.2 缺失覆盖识别

| 潜在缺失 | 严重程度 | 建议 |
|----------|:--:|------|
| subtypeOf 语义验证 | 中 | 当前已知 gap，已记录在 known_gaps |
| 数据源 API 可达性验证 | 低 | 需网络环境，当前为静态检查 |
| 样式（className/css）渲染验证 | 低 | 需浏览器沙箱 |
| 国际化（i18n）验证 | 低 | 当前场景不涉及多语言 |
| 访问性（a11y）验证 | 低 | WCAG 合规检查 |
| OPC UA 实时值轮询一致性 | 中 | 需模拟 OPC UA 服务器 |

---

## H. 检测有效性

### H.1 检测能力指标（类混淆矩阵）

| 术语 | 定义 | 示例 |
|------|------|------|
| **TP** (真阳性) | 确实有问题，验证也报了 | Card 缺少 children → ⚠️ issue |
| **TN** (真阴性) | 确实没问题，验证也没报 | 所有 ID 唯一 → ✅ passed |
| **FP** (假阳性/误报) | 实际上没问题，验证报了 | 合法的新组件名被误判为"未注册" |
| **FN** (假阴性/漏报) | 确实有问题，验证没报 | 环形引用未被检测到 |

由此导出：

| 指标 | 公式 | 含义 |
|------|------|------|
| **精确率 (Precision)** | `TP / (TP + FP)` | 报了的问题中有多少是真问题 |
| **召回率 (Recall)** | `TP / (TP + FN)` | 真实问题中被检测出的比例 |
| **F1 分数** | `2 * P * R / (P + R)` | 精确率与召回率的调和平均 |
| **误报率** | `FP / (TP + FP)` | 验证报错但实际无问题的比例 |

### H.2 各层误报/漏报风险评估

| 验证层 | 误报风险 | 漏报风险 | 缓解措施 |
|--------|:--:|:--:|----------|
| ① 溯源追溯 | 中 — 模糊匹配可能错误关联 | 低 — 精确匹配失败即报告 | 仅做精确匹配 |
| ② Schema合规 | 极低 — 基于规则检查 | 低 — 规则覆盖完整协议 | — |
| ③ 结构完整性 | 中 — "空 Card"可能是合法的 | 低 — 无环路检测已实现 | 允许空 Card 为 warning |
| ④ 语义保真度 | 中 — 补全三元组可能被误判为 phantom | 低 — 反向枚举覆盖全面 | 区分 source=imkg 和 source=knowledge_completion |
| ⑤ 数据一致性 | 极低 — 精确值比对 | 中 — 单位转换/精度差异可能遗漏 | 容忍浮点误差 1e-6 |
| ⑥ 运行时验证 | 低 — 静态规则检查 | 中 — 无法检测运行时异步错误 | 标注为 "静态检查" |

### H.3 验证结果可靠性（类置信度）

| 指标 | 计算方式 |
|------|----------|
| **单层置信度** | `层 score × (1 - 该层FP率)` |
| **综合置信度** | `Π(层置信度)` 或 `mean(层置信度)` |
| **issue severity 分布** | fatal/error/warning/info 比例 |

---

## I. 一致性与可复现性

### I.1 输入确定下的结果稳定性

| 指标 | 测试方法 | 期望 |
|------|----------|:--:|
| 重复运行一致性 | 相同 (schema, kg_store, frame) 运行 N 次 | 结果完全一致 |
| 输入顺序无关性 | 交换 componentsTree 中 children 顺序 | 语义覆盖率不变（不应因顺序浮动） |
| 时间戳无关性 | 不同时间运行 | 除 meta.gmt_create 外完全相同 |

### I.2 边界条件鲁棒性

| 场景 | 期望行为 |
|------|----------|
| `frame=None`（仅 KG 模式） | 数据一致性层返回 score=1.0, skipped |
| `kg_store` 为空 | 语义保真度返回 score=0.0，明确报 fatal |
| `schema.componentsTree` 为空 | 全部层返回失败，报告 fatal |
| 嵌套深度极大（>100） | 结构完整性层捕获并报告 |
| 组件名包含特殊字符 | Schema合规层捕获命名规范违规 |

### I.3 版本兼容性

| 指标 | 说明 |
|------|------|
| Schema 协议版本兼容 | 当前验证 v1.0.0，支持声明式版本号检查 |
| LowCodeEngine SDK 兼容 | 当前适配 ReactRenderer 1.0.x |

---

## J. 可解释性

### J.1 报告可读性

| 指标 | 说明 | 当前状态 |
|------|------|:--:|
| 分级摘要 | 顶层展示综合评分 + 通过/未通过 | ✅ `summary()` |
| 逐层详情 | 每层独立阅读 | ✅ `report.to_dict()` |
| 问题定位 | 每个 issue 包含组件名、属性名、期望值/实际值 | ✅ `message` 字段 |
| 严重性分级 | fatal/error/warning/info 四类 | ✅ `severity` 字段 |
| 可操作建议 | 每个 issue 附带修复建议 | ⚠️ 部分有，建议增强 |

### J.2 可视化友好度

| 指标 | 说明 |
|------|------|
| JSON 结构化输出 | ✅ `report.to_dict()` |
| 文本摘要输出 | ✅ `report.summary()` |
| 图层评分雷达图数据 | ✅ `layer_scores` 字典 |

### J.3 决策支持

| 指标 | 说明 |
|------|------|
| 整体通过/失败判定 | ✅ `report.all_passed` |
| 分层通过阈值 | ✅ 每层独立 passed 字段 |
| 综合可信分数 | ✅ `report.overall_score` (0~1) |

---

## K. 工程实用性

### K.1 集成便利性

| 指标 | 说明 | 当前状态 |
|------|------|:--:|
| 单行调用 | 一行代码完成全量验证 | ✅ `verifier.verify_all()` |
| Pipeline 自动集成 | 在 phase_3 中自动触发 | ✅ |
| CLI 参数控制 | `--no-lowcode` 跳过 | ✅ |
| 独立使用 | 不依赖 Pipeline，单模块可调 | ✅ `TrustVerifier` |

### K.2 性能效率

| 指标 | 说明 |
|------|------|
| 时间复杂度 | 每层 O(n)，n = 节点数。总体 O(6n) |
| 内存开销 | 遍历时不复制大对象，仅构建 Set/Dict 索引 |
| 可并行性 | 6 层检查无依赖，可并行化 |

### K.3 输出格式

| 格式 | 用途 |
|------|------|
| JSON (`.json`) | 程序消费 / 存入数据库 / 趋势分析 |
| 文本 (`.summary()`) | 人工阅读 / CI 日志 |
| Dict (`report.to_dict()`) | 内嵌到 PipelineResults 中 |

---

# 第三部分：综合评分计算

## 3.1 生成代码质量综合分 (Code Quality Score, CQS)

```
CQS = w₁ × 结构质量 + w₂ × 语义质量 + w₃ × 数据质量 + w₄ × 运行质量 + w₅ × 溯源质量
```

| 维度 | 权重 w | 理由 |
|------|:--:|------|
| 结构质量 | 0.25 | 结构错误导致渲染崩溃 |
| 语义质量 | 0.30 | 语义是 KG 系统核心价值 |
| 数据质量 | 0.20 | 数据准确是工业监控底线 |
| 运行质量 | 0.15 | 确保可用性 |
| 溯源质量 | 0.10 | 可信的基石 |

每个维度分由该维度下各指标加权平均计算。

## 3.2 验证框架可信分 (Verifier Trust Score, VTS)

```
VTS = w_g × 覆盖全面性 + w_h × 检测有效性 + w_i × 一致性 + w_j × 可解释性
```

| 维度 | 权重 w | 理由 |
|------|:--:|------|
| 覆盖全面性 | 0.30 | 是否覆盖所有故障模式 |
| 检测有效性 | 0.35 | 检测是否准确（P/R/F1） |
| 一致性与可复现性 | 0.20 | 结果是否可复现 |
| 可解释性 | 0.15 | 结果是否可理解 |

## 3.3 最终可信度评分 (Final Trust Score, FTS)

```
FTS = CQS × VTS
```

含义：**生成代码质量 × 验证框架可信度 = 最终可信任程度**

| FTS 范围 | 评级 | 建议动作 |
|----------|:--:|----------|
| ≥ 0.90 | 🟢 A 级 — 高度可信 | 可直接发布 |
| 0.75 ~ 0.90 | 🟡 B 级 — 基本可信 | 人工复核 issue 后发布 |
| 0.60 ~ 0.75 | 🟠 C 级 — 需关注 | 修复关键 issue 后重新生成 |
| < 0.60 | 🔴 D 级 — 不可信 | 排查生成流程异常 |

---

# 第四部分：阈值建议与告警策略

## 4.1 各级阈值

| 层级 | 指标 | 🟢 通过 | 🟡 警告 | 🔴 失败 |
|------|------|:--:|:--:|:--:|
| ① 溯源 | 可溯源覆盖率 | ≥ 0.95 | 0.85~0.95 | < 0.85 |
| ② 协议 | 必填字段完整率 | = 1.00 | — | < 1.00 |
| ② 协议 | 组件注册覆盖率 | = 1.00 | — | < 1.00 |
| ③ 结构 | ID 唯一率 | = 1.00 | — | < 1.00 |
| ③ 结构 | 无孤立 Variable 率 | ≥ 0.95 | 0.80~0.95 | < 0.80 |
| ④ 语义 | 总体语义覆盖率 | ≥ 0.90 | 0.75~0.90 | < 0.75 |
| ④ 语义 | 伪影率 | ≤ 0.05 | 0.05~0.15 | > 0.15 |
| ⑤ 数据 | 值精确一致率 | ≥ 0.98 | 0.90~0.98 | < 0.90 |
| ⑤ 数据 | 类型映射正确率 | = 1.00 | 0.95~1.00 | < 0.95 |
| ⑥ 运行 | 组件名可解析率 | = 1.00 | — | < 1.00 |
| ⑥ 运行 | 方法引用一致率 | = 1.00 | — | < 1.00 |

## 4.2 告警升级策略

```
1 个 fatal  → 直接判定为 D 级，阻断后续
1 个 error  → 所在层未通过 (passed=false)
3+ warning → 所在层评分降 0.15
5+ info    → 仅记录，不影响评分
```

## 4.3 持续改进回路

```
生成 Schema → 六层验证 → 验证报告
    ↑                        ↓
    ├──── 修复策略 ←── 问题分类 ←──
    │
    └── 重新生成 → 再次验证 → 对比两次报告 → 确认修复生效
```

---

## 附录：当前验证框架指标速查

| 层 | 检查项数 | 评分方式 | 通过条件 |
|---|:--:|------|------|
| ① 溯源追溯 | 1 项 | 可溯源覆盖率 | 无幻影节点 |
| ② Schema协议合规 | 6 项 | 检查项得分平均 | 无 fatal/error |
| ③ 结构完整性 | 6 项 | 检查项得分平均 | 无致命结构问题 |
| ④ 语义保真度 | 4 项 | 总体覆盖率 | coverage ≥ 0.85 |
| ⑤ 数据一致性 | 4 项 | 值+类型+元信息综合 | score ≥ 0.90 |
| ⑥ 运行时验证 | 4 项 | 检查项得分平均 | 无 fatal/error |

## 附录：当前验证框架已知限制（Known Limitations）

| 限制 | 类型 | 影响 |
|------|:--:|------|
| subtypeOf 语义未映射 | 功能 gap | 类继承关系在低代码组件中未体现 |
| 无真实渲染沙箱 | 技术限制 | 第⑥层为静态检查，无法发现运行时异步错误 |
| 无 OPC UA 实时轮询验证 | 环境限制 | 无法验证数据源 API 的实际可达性 |
| 模糊匹配可能误关联 | 算法限制 | `_find_in_frame()` 的模糊回退可能匹配错误节点 |
| 补全三元组 vs 原始三元组未区分来源 | 数据限制 | 语义保真度层未区分 `source=imkg` 和 `source=knowledge_completion` |
