data/
├── samples/                          ← 来源: SampleData 类
│   ├── sample_frame.json             ← OPC UA 数据帧模拟
│   ├── sample_sa.json                ← SA 格式（结构化参数）
│   └── sample_iea.json               ← IEA 格式（设备属性表）
│
└── training/                         ← 来源: TrainingDataGenerator 类
    ├── device_classification/         ← TextCNN 设备分类器用
    │   ├── char_vocab.json            ← 字符→索引 映射表
    │   ├── label_map.json             ← 数字→设备类型 映射表 (0=IR,1=CNC...)
    │   ├── test_vocab.json            ← 测试用词表（仅 test 用）
    │   ├── training_data.json         ← 训练样本 (文本序列+标签对)
    │   └── textcnn.pt                 ← ★ TextCNN 模型权重 (build_models 保存)
    │
    ├── cbow/                          ← CBOW 字符嵌入训练用
    │   ├── vocab.json                 ← 字符词表
    │   └── cbow_data.json             ← 训练数据 (实体名+上下文字符)
    │
    ├── complex/                       ← ComplEx KG 嵌入训练用
    │   ├── triples.json               ← 三元组列表 (head, relation, tail)
    │   ├── entity_map.json            ← 实体名→KG内索引 映射
    │   ├── relation_map.json          ← 关系名→KG内索引 映射
    │   ├── cbow.pt                    ← ★ CBOW 模型权重 (build_models 保存)
    │   ├── complex.pt                 ← ★ ComplEx 模型权重
    │   └── transformer.pt            ← ★ SpaceTransformer 权重
    │
    └── ner/                           ← NER 实体识别训练用
        └── ner_data.json              ← 实体标注序列