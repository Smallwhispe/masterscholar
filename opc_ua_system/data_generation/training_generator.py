import json
import logging
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TrainingDataGenerator:
    """训练数据生成器

    为各个训练阶段生成格式规范的训练数据:
    1. data/training/device_classification/ - TextCNN分类器训练数据
    2. data/training/cbow/ - CBOW字符嵌入训练数据
    3. data/training/complex/ - ComplEx KG嵌入训练数据
    4. data/training/ner/ - NER实体识别训练数据
    """

    DEVICE_TYPE_FIELDS = {
        "IR": [
            "RobotArm", "Controller", "EndEffector", "DriveSystem",
            "AxisCount", "Reach", "Payload", "Repeatability",
            "MoveJ", "MoveL", "ControlMode", "ProgramNumber",
            "SpeedOverride", "GripperType", "GrippingForce",
            "MotorSpeed", "MotorCurrent", "JointTemperature",
            "RobotStatus", "EmergencyStop", "StartProgram", "StopProgram", "ResetAlarm",
        ],
        "CNC": [
            "CNCMachine", "Spindle", "ToolChanger", "Worktable",
            "CoolantSystem", "CNCController", "SpindleSpeed",
            "SpindleLoad", "SpindleOrientation", "ToolNumber",
            "ToolOffset", "XPosition", "YPosition", "ZPosition",
            "FeedRate", "CoolantLevel", "CoolantPressure",
            "ProgramName", "ExecutionMode", "MachineStatus",
            "AlarmCode", "LoadProgram", "CycleStart", "EmergencyStop",
        ],
        "SOM": [
            "SortingMachine", "Feeder", "Conveyor", "VisionSystem",
            "SortingActuator", "FeedRate", "FeederStatus",
            "BeltSpeed", "BeltDirection", "RecognitionRate",
            "CameraResolution", "SortCount", "SortCategory",
            "Throughput", "ErrorCount", "StartSorting", "PauseSorting",
        ],
        "SCM": [
            "ScribingMachine", "ScribingHead", "XYTable",
            "LaserSystem", "VisionAlign", "ScribingForce",
            "ScribingSpeed", "ToolWear", "XPosition", "YPosition",
            "TableAccuracy", "LaserPower", "PulseFrequency",
            "AlignmentAccuracy", "SubstrateSize", "ProcessingTime",
            "LoadPattern", "StartProcess",
        ],
        "PM": [
            "PickPlaceMachine", "PickHead", "PlacementHead",
            "FeederBank", "NozzleChanger", "PCBConveyor",
            "PickAccuracy", "PickSpeed", "VacuumPressure",
            "PlacementAccuracy", "PlacementForce", "RotationAngle",
            "FeederCount", "ComponentType", "NozzleType",
            "BoardPosition", "CycleTime", "ComponentCount",
            "StartPlacement", "StopPlacement",
        ],
        "PW": [
            "PressWelder", "WeldingHead", "PressureSystem",
            "PowerSupply", "CoolingSystem", "WorkHolder",
            "ElectrodeForce", "ElectrodeDisplacement", "WeldCount",
            "CylinderPressure", "ClampingForce", "WeldingCurrent",
            "WeldingVoltage", "PowerFactor", "WaterTemperature",
            "WaterFlow", "ClampStatus", "WeldingMode",
            "TotalWeldCount", "EmergencyStop", "ResetCounter",
        ],
    }

    LABEL_MAP = {"IR": 0, "CNC": 1, "SOM": 2, "SCM": 3, "PM": 4, "PW": 5}

    def __init__(self, base_dir: str = "data/training/"):
        self.base_dir = Path(base_dir)
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for sub in ["device_classification", "cbow", "complex", "ner"]:
            (self.base_dir / sub).mkdir(parents=True, exist_ok=True)

    def generate_classification_data(
        self, samples_per_class: int = 300
    ) -> Tuple[List[List[int]], List[int]]:
        """生成设备类型分类训练数据 (字符级)

        模拟来自飞机制造和电子制造两个行业的28台典型设备产生的样本。
        总共生成 ~6类 × 300 = 1800+ 个样本（论文中为1870个样本）
        """
        from device_identification.preprocessor import CharPreprocessor

        preprocessor = CharPreprocessor(max_sequence_length=128)

        all_texts = []
        all_labels = []

        for device_type, fields in self.DEVICE_TYPE_FIELDS.items():
            text_variants = []
            for field in fields:
                text_variants.append(field)
                text_variants.append(field.lower())
                text_variants.append(f"ns={random.randint(1,6)};{field}")
                text_variants.append(f"{field}{random.randint(1,999)}")
                text_variants.append(f"{field}_Status")
                text_variants.append(f"{field}Value")
                text_variants.append(f"Current{field}")

            text_variants = list(set(text_variants))
            while len(text_variants) < samples_per_class:
                base = random.choice(fields)
                suffix = random.choice([
                    f"_{random.randint(1,1000)}",
                    f"Ch{random.randint(1,99)}",
                    f"-{random.choice(['A','B','C','X','Y','Z'])}",
                    f"{random.choice(['Set','Get','Read','Write','Cmd','Ctrl'])}",
                ])
                text_variants.append(f"{base}{suffix}")

            selected = random.sample(text_variants, samples_per_class)
            label = self.LABEL_MAP[device_type]

            all_texts.extend(selected)
            all_labels.extend([label] * samples_per_class)

        preprocessor.build_vocab(all_texts)
        encoded = preprocessor.encode_batch(all_texts)

        data_path = self.base_dir / "device_classification"
        preprocessor.save(str(data_path / "char_vocab.json"))
        with open(data_path / "label_map.json", "w") as f:
            json.dump(
                {v: k for k, v in self.LABEL_MAP.items()}, f, indent=2
            )

        with open(data_path / "training_data.json", "w", encoding="utf-8") as f:
            json.dump({
                "texts": all_texts,
                "labels": all_labels,
                "label_map": self.LABEL_MAP,
            }, f, ensure_ascii=False, indent=2)

        logger.info(
            f"分类训练数据生成完成: {len(all_texts)} 个样本, "
            f"{len(set(all_labels))} 个类别"
        )
        return encoded, all_labels

    def generate_cbow_data(self) -> Dict:
        """生成CBOW字符嵌入训练数据

        从所有设备字段名称构建字符序列，用于训练字符级CBOW模型
        """
        from collections import defaultdict

        char_to_idx = {"<PAD>": 0, "<UNK>": 1}
        next_idx = 2

        all_names = []
        for fields in self.DEVICE_TYPE_FIELDS.values():
            all_names.extend(fields)

        for name in all_names:
            for ch in name:
                if ch not in char_to_idx:
                    char_to_idx[ch] = next_idx
                    next_idx += 1

        contexts = []
        targets = []
        window_size = 3

        for name in all_names:
            indices = [char_to_idx.get(c, 1) for c in name]
            for i in range(len(indices)):
                ctx = []
                for j in range(
                    max(0, i - window_size), min(len(indices), i + window_size + 1)
                ):
                    if j != i:
                        ctx.append(indices[j])

                while len(ctx) < 2 * window_size:
                    ctx.append(0)

                contexts.append(ctx[:2 * window_size])
                targets.append(indices[i])

        data_path = self.base_dir / "cbow"
        with open(data_path / "vocab.json", "w") as f:
            json.dump({"char_to_idx": char_to_idx, "vocab_size": next_idx}, f, indent=2)

        with open(data_path / "cbow_data.json", "w", encoding="utf-8") as f:
            json.dump({
                "entity_names": all_names,
                "contexts": contexts,
                "targets": targets,
                "window_size": window_size,
            }, f, ensure_ascii=False)

        logger.info(
            f"CBOW训练数据生成完成: {len(all_names)} 个实体名, "
            f"{len(contexts)} 个训练样本"
        )
        return {
            "entity_names": all_names,
            "contexts": contexts,
            "targets": targets,
            "char_to_idx": char_to_idx,
            "vocab_size": next_idx,
        }

    def generate_complex_data(
        self, imkg_triples: List[Dict]
    ) -> Dict:
        """生成ComplEx训练数据

        从IMKG的所有三元组生成(head, relation, tail)索引表示
        """
        entities = set()
        relations = set()
        triples = []

        for t in imkg_triples:
            head = t.get("head", "")
            relation = t.get("relation", "")
            tail = t.get("tail", "")
            if head and relation and tail:
                entities.add(head)
                entities.add(tail)
                relations.add(relation)
                triples.append((head, relation, tail))

        entity_to_idx = {e: i for i, e in enumerate(sorted(entities))}
        relation_to_idx = {r: i for i, r in enumerate(sorted(relations))}

        triple_indices = [
            [entity_to_idx[h], relation_to_idx[r], entity_to_idx[t]]
            for h, r, t in triples
        ]

        data_path = self.base_dir / "complex"
        with open(data_path / "entity_map.json", "w") as f:
            json.dump(
                {"entity_to_idx": entity_to_idx, "num_entities": len(entities)},
                f,
                indent=2,
            )
        with open(data_path / "relation_map.json", "w") as f:
            json.dump(
                {"relation_to_idx": relation_to_idx, "num_relations": len(relations)},
                f,
                indent=2,
            )
        with open(data_path / "triples.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "triples": triples,
                    "triple_indices": triple_indices,
                    "num_triples": len(triple_indices),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info(
            f"ComplEx训练数据生成完成: {len(entities)} 个实体, "
            f"{len(relations)} 种关系, {len(triple_indices)} 个三元组"
        )
        return {
            "entity_to_idx": entity_to_idx,
            "relation_to_idx": relation_to_idx,
            "triple_indices": triple_indices,
        }

    def generate_ner_data(self) -> Dict:
        ner_samples = []
        all_tags = set(["O"])

        bio_map = {"DeviceName": "DeviceName", "Feature": "Feature",
                   "Attribute": "Attribute", "Operation": "Operation"}

        for device_type, fields in self.DEVICE_TYPE_FIELDS.items():
            for field in fields:
                tokens = list(field)
                tags = []
                for i, t in enumerate(tokens):
                    if i == 0:
                        tag = f"B-{bio_map.get(bio_map.get('Feature', 'Feature'), 'O')}"
                    else:
                        tag = "I-Feature"
                    tags.append(tag)
                    all_tags.add(tag)
                ner_samples.append({"tokens": tokens, "tags": tags})

        from device_identification.ner import build_tag_mapping
        idx_to_tag, num_tags = build_tag_mapping(list(all_tags))

        data_path = self.base_dir / "ner"
        with open(data_path / "ner_data.json", "w", encoding="utf-8") as f:
            json.dump({
                "samples": ner_samples,
                "num_samples": len(ner_samples),
                "idx_to_tag": {str(k): v for k, v in idx_to_tag.items()},
                "num_tags": num_tags,
            }, f, ensure_ascii=False, indent=2)

        logger.info(f"NER训练数据生成完成: {len(ner_samples)} 个样本, {num_tags} 种标签")
        return {"samples": ner_samples, "num_samples": len(ner_samples)}

    def get_all_imkg_triples(self) -> List[Dict]:
        """获取所有IMKG三元组 (用于ComplEx训练)"""
        from knowledge_graph.imkg.device_kgs import IMKG_BUILDERS

        all_triples = []
        for device_type, builder in IMKG_BUILDERS.items():
            triples = builder()
            for t in triples:
                all_triples.append({
                    "head": t.head,
                    "relation": t.relation,
                    "tail": t.tail,
                    "head_type": t.head_type,
                    "tail_type": t.tail_type,
                    "device_type": device_type,
                })

        logger.info(f"所有IMKG三元组总数: {len(all_triples)}")
        return all_triples

    def generate_all(self) -> Dict:
        """一键生成所有训练数据"""
        logger.info("开始生成所有训练数据...")

        classification_data = self.generate_classification_data()
        cbow_data = self.generate_cbow_data()
        imkg_triples = self.get_all_imkg_triples()
        complex_data = self.generate_complex_data(imkg_triples)
        ner_data = self.generate_ner_data()

        logger.info("所有训练数据生成完毕!")
        return {
            "classification": {
                "samples": len(classification_data[1]) if classification_data else 0
            },
            "cbow": {
                "entity_names": cbow_data.get("entity_count", 0) if cbow_data else 0
            },
            "complex": {
                "triples": complex_data.get("num_triples", 0) if complex_data else 0
            },
            "ner": {
                "samples": ner_data.get("num_samples", 0) if ner_data else 0
            },
        }
