output/
├── owl/
│   └── IR_ontology.owl               ← IMKGToOWL.convert() 输出
├── nodeset/
│   └── IR_nodeset.xml                ← OWLToNodesetXML.convert_from_kg()
├── lowcode/
│   └── IR_page.schema.json            ← LowcodeGenerator.convert()
└── verify/
    └── IR_verification_report.json    ← TrustVerifier.verify_all()