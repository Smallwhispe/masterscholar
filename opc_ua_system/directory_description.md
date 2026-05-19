Phase 2: build_models()
① 确保词表存在
   ├── 读 data/training/device_classification/char_vocab.json
   └── 不存在？用 DEVICE_TYPE_FIELDS 中 6 类设备的所有字段名构建字符词表

② 构建 TextCNN (设备分类器)
   ├── 输入: char_vocab_size, num_classes=6
   ├── 包装为 DeviceIdentifier
   └── 保存 textcnn.pt

③ 构建 CBOW (字符嵌入模型)
   ├── 输入: char_vocab_size, embedding_dim=64, window=3
   └── 作用: 把"Spindle"等设备字段名变成向量

④ 构建 ComplEx (知识图谱嵌入)
   ├── 输入: 实体数, 关系数, embedding_dim=256
   ├── 先调用 kg_builder.build_from_device_type("CNC") 获取实体/关系索引
   └── 作用: 对 (head, relation, tail) 三元组打分

⑤ 构建 SpaceTransformer (空间对齐)
   ├── 输入: cbow_dim=64, kg_dim=512, hidden_dim=128
   └── 作用: 把 CBOW 的字符向量映射到 ComplEx 的 KG 向量空间

⑥ 组装 KnowledgeLinker
   └── 把 CBOW + ComplEx + Transformer 串起来，一个调用完成未知实体补全

⑦ 保存所有权重
   ├── complex/cbow.pt
   ├── complex/complex.pt
   ├── complex/transformer.pt
   └── device_classification/textcnn.pt

Phase 3: query_by_device_type(frame)
① 自动加载或生成模型 (_ensure_models_ready)
   ├── textcnn.pt + complex.pt 存在 → torch.load() 直接加载权重到内存
   └── 不存在 → 自动调用 init_training_data() + build_models() 生成

② 设备类型识别
   ├── 调用: DeviceIdentifier.identify_from_frame(frame)
   ├── 提取帧中所有 browse_name 拼接成文本序列
   │   "Spindle SpindleSpeed SpindleLoad ToolNumber ..."
   ├── CharPreprocessor → 字符 → 索引序列 (padding 到 128)
   ├── TextCNN 前向推理 → 6 类 logits
   └── softmax → 最高概率类 = "CNC" (置信度 0.92)

③ IMKG 构建
   ├── 调用: kg_builder.build_from_device_type(device_type)
   └── 生成该设备类型的全部三元组 (device_type 在 6 个 IMKG 中查表)
       (CNC, hasComponent, Spindle)
       (Spindle, hasProperty, SpindleSpeed)
       (Spindle, hasOperation, StartSpindle)
       ... (共 24 条)

④ 知识补全 (如果帧中有 KG 不认识的实体)
   ├── 调用: KnowledgeLinker.complete_unknown_entities()
   ├── CBOW 把未知实体名变成字符向量
   ├── SpaceTransformer 映射到 ComplEx 的 KG 嵌入空间
   ├── ComplEx 对候选 (head, relation, tail) 三元组打分
   └── 将高置信度补全三元组注入 kg_builder

⑤ Neo4j 同步 (如果 config.yaml 中 db_type=neo4j 且服务已启动)
   ├── 调用: Neo4jConnector.import_triples()
   ├── 全部三元组 → Cypher CREATE 语句 → 图数据库
   └── Neo4j 未启动 → 打印 warning，跳过 (不影响后续流程)

⑥ KG → OWL 本体
   ├── 调用: IMKGToOWL.convert(kg_store, device_type)
   ├── 三元组 → OWL/RDF XML 本体文件
   └── 输出: output/owl/CNC_ontology.owl

⑦ OWL → Nodeset XML
   ├── 调用: OWLToNodesetXML.convert_from_kg()
   ├── OWL → OPC UA 标准 Nodeset XML (符合 OPC UA 信息模型规范)
   │   含 UAObject、UAVariable、UAReferenceType 等标准节点
   └── 输出: output/nodeset/CNC_nodeset.xml

⑧ 低代码 Schema 生成
   ├── 调用: LowcodeGenerator.convert(kg_store, frame)
   ├── ① 从 KG 提取语义骨架 (hasComponent → children 嵌套)
   │   CNCMachine (Page 根节点)
   │   ├── Card("Spindle")
   │   │   ├── NumberPicker("SpindleSpeed")   ← KG: hasProperty
   │   │   ├── NumberPicker("SpindleLoad")    ← KG: hasProperty
   │   │   ├── Button("StartSpindle")          ← KG: hasOperation
   │   │   └── Button("StopSpindle")           ← KG: hasOperation
   │   ├── Card("ToolChanger")
   │   │   ├── NumberPicker("ToolNumber")
   │   │   └── Button("ChangeTool")
   │   └── Card("Worktable")
   │       ├── NumberPicker("XPosition")
   │       └── NumberPicker("YPosition")
   ├── ② 从 Frame 注入实时值 (value: 10234 → NumberPicker 的 defaultValue)
   ├── ③ 注入全局常量 (componentsTree[0].constants: SERVER_URL, FRAME_ID 等)
   └── 输出: output/lowcode/CNC_page.schema.json

⑨ 可信验证 (6 层框架)
   ├── 调用: TrustVerifier.verify_all(schema, kg_store, frame)
   ├── ① 溯源追溯: 每个输出节点能否映射回 KG 三元组或 Frame 节点
   ├── ② Schema协议合规: JSON 是否符合 LowCodeEngine 搭建协议
   ├── ③ 结构完整性: 组件树是否合法 (ID 唯一/无孤立/深度合理)
   ├── ④ 语义保真度: hasComponent / hasProperty / hasOperation 映射覆盖率
   ├── ⑤ 数据一致性: Frame 运行时值与输出控件值是否一致
   ├── ⑥ 运行时验证: 组件名是否可解析 / 方法引用是否一致 / 表达式是否有效
   └── 输出: output/verify/CNC_verification_report.json

返回结果
   └── {
         "device_type": "CNC",
         "confidence": 0.92,
         "kg_entity_count": 15,
         "kg_triple_count": 24,
         "completed_triples": 3,
         "neo4j_synced": 24,
         "owl_path": "output/owl/CNC_ontology.owl",
         "nodeset_path": "output/nodeset/CNC_nodeset.xml",
         "lowcode_schema_path": "output/lowcode/CNC_page.schema.json",
         "verification": { "overall_score": 0.98, "all_passed": true, ... },
         "address_space": { "objects": 4, "variables": 8, "methods": 5, "references": 32 },
         "status": "completed"
       }   