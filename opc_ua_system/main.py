import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from knowledge_graph import KnowledgeGraphBuilder
from knowledge_completion import CompletionTrainer, KnowledgeLinker
from device_identification import (
    CharPreprocessor,
    CharTextCNN,
    DeviceIdentifier,
    DEVICE_TYPE_LABELS,
)
from model_generation import (
    IMKGToOWL,
    OWLToNodesetXML,
    FormatTransformationAgent,
    AddressSpaceBuilder,
    LowcodeGenerator,
)
from validation import TrustVerifier
from data import TrainingDataGenerator, SampleData

logger = logging.getLogger(__name__)


class PipelineConfig:
    """流水线运行配置"""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = os.environ.get(
                "OPCUA_CONFIG", "config/config.yaml"
            )

        if Path(config_path).exists():
            import yaml

            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = {}

    def get(self, *keys: str, default: Any = None) -> Any:
        val = self._config
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k, default)
            else:
                return default
        return val if val is not None else default


class Pipeline:
    """OPC UA知识图谱自动建模系统主流水线

    整体流程:
    1. 数据采集:     设备数据帧 → JSON
    2. 设备识别:     字符级TextCNN + NER → 设备类型(IR/CNC/SOM/SCM/PM/PW)
    3. 知识图谱:     根据设备类型构建对应的IMKG
    4. 知识补全:     CBOW + ComplEx → 未知实体补全
    5. 模型生成:     IMKG → OWL → Nodeset XML
    6. 地址空间:     加载节点集合构建OPC UA地址空间
    7. 低代码生成:   KG语义 + 帧实时值 → LowCodeEngine ProjectSchema JSON

    图示流程:
    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────┐
    │ 设备数据帧 │ → │  JSON转换  │ → │ 设备类型识别│ → │未知实体补全│ → │信息模型子图│ → │ OPC UA XML│ → │低代码Schema │
    └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────────┘
    """

    def __init__(self, config_path: str = None):
        self.config = PipelineConfig(config_path)
        self.kg_builder = KnowledgeGraphBuilder()
        self.imkg_to_owl = IMKGToOWL()
        self.owl_to_nodeset = OWLToNodesetXML()
        self.fta = FormatTransformationAgent()
        self.address_builder = AddressSpaceBuilder()
        self.lowcode_gen = LowcodeGenerator()
        self.verifier = TrustVerifier()

        self.char_preprocessor: Optional[CharPreprocessor] = None
        self.textcnn: Optional[CharTextCNN] = None
        self.identifier: Optional[DeviceIdentifier] = None
        self.linker: Optional[KnowledgeLinker] = None
        self.training_gen: Optional[TrainingDataGenerator] = None

        self._device_type: str = ""
        self._results: Dict[str, Any] = {}

    def phase_1_init_training_data(self) -> Dict:
        """第一阶段: 初始化训练数据

        在 data/training/ 下生成所有需要的训练数据
        - device_classification/ : TextCNN训练数据 + 字符词表 + 标签映射
        - cbow/                  : CBOW字符嵌入训练数据
        - complex/               : ComplEx KG嵌入训练数据
        - ner/                   : NER实体识别训练数据
        """
        logger.info("=" * 50)
        logger.info("Phase 1: 初始化训练数据")
        logger.info("=" * 50)

        self.training_gen = TrainingDataGenerator()
        data_info = self.training_gen.generate_all()

        self._results["phase_1"] = {
            "status": "completed",
            "data_info": data_info,
        }
        logger.info(f"Phase 1 完成: {data_info}")
        return data_info

    def phase_2_build_models(self, device: str = "cpu") -> Dict:
        """第二阶段: 构建并训练模型

        - 构建字符级TextCNN分类器
        - 构建CBOW字符嵌入模型
        - 构建ComplEx KG嵌入模型
        - 构建空间变换模块
        - 关联IMKG中的实体嵌入
        """
        logger.info("=" * 50)
        logger.info("Phase 2: 构建并训练模型")
        logger.info("=" * 50)

        import torch

        if self.training_gen is None:
            self.phase_1_init_training_data()

        gen = self.training_gen
        output_dir = Path("data/training/device_classification")
        vocab_path = output_dir / "char_vocab.json"

        if vocab_path.exists():
            self.char_preprocessor = CharPreprocessor.load(str(vocab_path))
        else:
            self.char_preprocessor = CharPreprocessor()
            all_texts = []
            for fields in gen.DEVICE_TYPE_FIELDS.values():
                all_texts.extend(fields)
            self.char_preprocessor.build_vocab(all_texts)

        self.textcnn = CharTextCNN(
            vocab_size=self.char_preprocessor.vocab_size,
            num_classes=6,
            dropout_rate=0.5,
        )
        self.identifier = DeviceIdentifier(
            self.textcnn, self.char_preprocessor, device=device
        )

        from knowledge_completion import CBOW, ComplEx, SpaceTransformer

        cbow_vocab = self.char_preprocessor.vocab_size

        self.cbow = CBOW(
            vocab_size=cbow_vocab,
            embedding_dim=64,
            window_size=3,
        )

        imkg_triples = gen.get_all_imkg_triples()
        self.kg_builder.build_from_device_type("CNC")

        entities = self.kg_builder._entity_to_idx
        relations = self.kg_builder._relation_to_idx

        self.complex_model = ComplEx(
            num_entities=len(entities),
            num_relations=len(relations),
            embedding_dim=256,
        )

        self.transformer = SpaceTransformer(
            cbow_dim=64,
            kg_dim=512,
            hidden_dim=128,
            transform_type="mlp",
        )

        self.linker = KnowledgeLinker(
            cbow=self.cbow,
            complex_model=self.complex_model,
            space_transformer=self.transformer,
            char_to_idx=self.char_preprocessor.char_to_idx,
            entity_to_idx=self.kg_builder._entity_to_idx,
            relation_to_idx=self.kg_builder._relation_to_idx,
            idx_to_entity=self.kg_builder._idx_to_entity,
            idx_to_relation=self.kg_builder._idx_to_relation,
            device=device,
        )

        trainer = CompletionTrainer(
            cbow=self.cbow,
            complex_model=self.complex_model,
            space_transformer=self.transformer,
            device=device,
        )

        model_dir = Path("data/training/complex/")
        model_dir.mkdir(parents=True, exist_ok=True)
        trainer.save_models(str(model_dir))

        self._results["phase_2"] = {
            "status": "completed",
            "textcnn_params": sum(
                p.numel() for p in self.textcnn.parameters()
            ),
            "cbow_params": sum(
                p.numel() for p in self.cbow.parameters()
            ),
            "complex_params": sum(
                p.numel() for p in self.complex_model.parameters()
            ),
            "transformer_params": sum(
                p.numel() for p in self.transformer.parameters()
            ),
        }
        logger.info("Phase 2 完成: 所有模型已构建")
        return self._results["phase_2"]

    def phase_3_query_by_device_type(
        self, frame: Dict, generate_lowcode: bool = True
    ) -> Dict:
        """第三阶段: 设备数据帧 → 设备类型识别 → IMKG构建 → 知识补全 → 模型生成

        核心流水线:
        1. 设备类型识别 (TextCNN + NER)
        2. 根据设备类型构建对应IMKG
        3. 开放世界知识补全 (CBOW + ComplEx)
        4. 信息模型子图抽取
        5. IMKG → OWL → Nodeset XML
        6. 地址空间构建
        7. 低代码Schema生成: KG语义骨架 + 帧实时值 → LowCodeEngine ProjectSchema JSON
        """
        logger.info("=" * 50)
        logger.info("Phase 3: 设备建模流水线")
        logger.info("=" * 50)

        result = {"device_type": "Unknown", "status": "not_started"}

        if self.identifier is None:
            logger.error("模型未初始化，请先运行 Phase 2")
            return result

        id_result = self.identifier.identify_from_frame(frame)
        device_type = id_result.get("device_type", "Unknown")
        result.update(id_result)

        if device_type == "Unknown":
            logger.warning("无法识别设备类型")
            result["status"] = "failed: unknown device type"
            return result

        self._device_type = device_type
        logger.info(f"识别到设备类型: {device_type} ({id_result.get('device_name', '')}), "
                     f"置信度: {id_result['confidence']:.4f}")

        self.kg_builder.build_from_device_type(device_type)

        unknown_entities = []
        entities = id_result.get("entities", {})
        for entity_type, entity_list in entities.items():
            for name in entity_list:
                unknown_entities.append({
                    "name": name,
                    "type": entity_type,
                })

        completed_triples = []
        if unknown_entities and self.linker:
            completed = self.linker.complete_unknown_entities(
                [{"name": e["name"], "entities": {e["type"]: [e["name"]]}}
                 for e in unknown_entities]
            )
            for comp in completed:
                from knowledge_graph.triple_store import Triple

                triple = Triple(
                    head=comp["head"],
                    relation=comp["relation"],
                    tail=comp["tail"],
                    confidence=comp.get("score", 0.5),
                    source="knowledge_completion",
                )
                self.kg_builder.add_completed_triples([triple])
                completed_triples.append(comp)

        self.imkg_to_owl = IMKGToOWL()
        owl_content = self.imkg_to_owl.convert(
            self.kg_builder.store, device_type=device_type
        )
        owl_path = Path("output/owl") / f"{device_type}_ontology.owl"
        self.imkg_to_owl.save_owl(owl_content, str(owl_path))

        nodeset_xml = self.owl_to_nodeset.convert_from_kg(
            self.kg_builder.store,
            device_type=device_type,
            device_name=id_result.get("device_name", ""),
        )
        nodeset_path = Path("output/nodeset") / f"{device_type}_nodeset.xml"
        self.owl_to_nodeset.save(nodeset_xml, str(nodeset_path))

        address_space = self.address_builder.load_nodeset_xml(
            str(nodeset_path)
        )

        lowcode_path = ""
        if generate_lowcode:
            logger.info("  → 生成低代码Schema (KG语义 + 帧实时值融合)")
            lowcode_schema = self.lowcode_gen.convert(
                kg_store=self.kg_builder.store,
                frame=frame,
                device_type=device_type,
                device_name=id_result.get("device_name", ""),
            )
            lowcode_path = Path("output/lowcode") / f"{device_type}_page.schema.json"
            self.lowcode_gen.save(lowcode_schema, str(lowcode_path))

            logger.info("  → 可信验证: 六层验证框架")
            verify_report = self.verifier.verify_all(
                schema=lowcode_schema,
                kg_store=self.kg_builder.store,
                frame=frame,
            )
            verify_path = Path("output/verify") / f"{device_type}_verification_report.json"
            self.verifier.save_report(verify_report, str(verify_path))
            result["verification"] = {
                "overall_score": verify_report.overall_score,
                "all_passed": verify_report.all_passed,
                "layer_scores": verify_report.layer_scores,
                "total_issues": verify_report.total_issues,
                "report_path": str(verify_path),
            }

        result.update({
            "kg_entity_count": self.kg_builder.store.entity_count,
            "kg_triple_count": self.kg_builder.store.triple_count,
            "completed_triples": len(completed_triples),
            "owl_path": str(owl_path),
            "nodeset_path": str(nodeset_path),
            "lowcode_schema_path": "" if lowcode_path == "" else str(lowcode_path),
            "address_space": {
                "objects": len(address_space.get("objects", {})),
                "variables": len(address_space.get("variables", {})),
                "methods": len(address_space.get("methods", {})),
                "references": len(address_space.get("references", [])),
            },
            "status": "completed",
        })

        self._results["phase_3"] = result
        logger.info(f"Phase 3 完成: 设备类型={device_type}, "
                     f"KG实体={self.kg_builder.store.entity_count}, "
                     f"补全三元组={len(completed_triples)}")
        return result

    def run_full_pipeline(
        self, frame: Dict = None, device: str = "cpu", generate_lowcode: bool = True
    ) -> Dict[str, Any]:
        """运行完整流水线

        Args:
            frame: OPC UA数据帧 (如为None则使用示例数据)
            device: 运行设备 [cpu|cuda]
            generate_lowcode: 是否生成低代码Schema (默认True)
        Returns:
            流水线执行结果
        """
        logger.info("=" * 60)
        logger.info("OPC UA知识图谱自动建模系统 - 完整流水线启动")
        logger.info("=" * 60)

        if frame is None:
            sample_gen = SampleData()
            sample_gen.create_all()
            frame = sample_gen.create_sample_frame()

        self.phase_1_init_training_data()
        self.phase_2_build_models(device=device)
        result = self.phase_3_query_by_device_type(
            frame, generate_lowcode=generate_lowcode
        )

        logger.info("=" * 60)
        logger.info("流水线执行完毕!")
        logger.info(f"设备类型: {result.get('device_type', 'Unknown')}")
        logger.info(f"KG实体数: {result.get('kg_entity_count', 0)}")
        logger.info(f"KG三元组数: {result.get('kg_triple_count', 0)}")
        logger.info(f"补全三元组: {result.get('completed_triples', 0)}")
        if result.get("lowcode_schema_path"):
            logger.info(f"低代码Schema: {result.get('lowcode_schema_path')}")
        if result.get("verification"):
            v = result["verification"]
            logger.info(
                f"可信验证: 综合评分 {v['overall_score']:.2%}, "
                f"通过 {'全' if v['all_passed'] else '未全'}部, "
                f"问题 {v['total_issues']} 个"
            )
            logger.info(f"验证报告: {v.get('report_path', '')}")
        logger.info("=" * 60)

        return {
            **self._results,
            "final_status": result.get("status", "unknown"),
        }

    def export_results(self, output_path: str = "output/pipeline_results.json") -> str:
        """导出流水线结果"""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._results, f, ensure_ascii=False, indent=2)

        logger.info(f"流水线结果已导出: {output_path}")
        return str(path)


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="OPC UA知识图谱自动建模系统"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="配置文件路径",
    )
    parser.add_argument(
        "--frame",
        type=str,
        default=None,
        help="数据帧JSON文件路径",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="运行设备 [cpu|cuda]",
    )
    parser.add_argument(
        "--export",
        type=str,
        default="output/pipeline_results.json",
        help="结果导出路径",
    )
    parser.add_argument(
        "--generate-data-only",
        action="store_true",
        help="仅生成训练数据",
    )
    parser.add_argument(
        "--no-lowcode",
        action="store_true",
        help="不生成低代码Schema (默认会生成)",
    )

    args = parser.parse_args()

    from utils.logger import setup_logging

    setup_logging()

    pipeline = Pipeline(config_path=args.config)

    if args.generate_data_only:
        pipeline.phase_1_init_training_data()
        return

    if args.frame:
        with open(args.frame, "r", encoding="utf-8") as f:
            frame = json.load(f)
    else:
        frame = None

    results = pipeline.run_full_pipeline(
        frame=frame,
        device=args.device,
        generate_lowcode=not args.no_lowcode,
    )
    pipeline.export_results(args.export)

    return results


if __name__ == "__main__":
    main()
