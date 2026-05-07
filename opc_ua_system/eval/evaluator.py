import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .metrics import EvaluationMetrics, compute_metrics, compute_ranking_metrics

logger = logging.getLogger(__name__)


class PipelineEvaluator:
    """整体流水线评估器

    评估各阶段的性能：
    1. 设备类型识别：P(精确率)、R(召回率)、F1Score
    2. 知识补全：MRR、Hit@1、Hit@3
    3. 端到端：从设备数据帧到Nodeset XML的完整流程
    """

    def __init__(
        self,
        output_dir: str = "output/eval/",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._results: Dict[str, dict] = {}

    def evaluate_classification(
        self,
        identifier,
        test_frames: List[Dict],
        true_labels: List[str],
    ) -> EvaluationMetrics:
        """评估设备类型识别"""
        y_true = []
        y_pred = []
        label_map = {v: k for k, v in identifier.labels.items()}

        for frame, true_label in zip(test_frames, true_labels):
            result = identifier.identify_from_frame(frame)
            pred_label = result.get("device_type", "Unknown")
            true_label_idx = label_map.get(true_label, -1)
            pred_label_idx = label_map.get(pred_label, -1)

            if true_label_idx >= 0 and pred_label_idx >= 0:
                y_true.append(true_label_idx)
                y_pred.append(pred_label_idx)

        if y_true:
            metrics = EvaluationMetrics.from_raw(y_true, y_pred)
        else:
            metrics = EvaluationMetrics()

        self._results["classification"] = metrics.to_dict()
        logger.info(
            f"设备识别评估: P={metrics.precision:.4f}, "
            f"R={metrics.recall:.4f}, F1={metrics.f1_score:.4f}"
        )
        return metrics

    def evaluate_completion(
        self,
        linker,
        test_samples: List[Dict],
    ) -> Dict[str, float]:
        """评估知识补全的MRR和Hit@{1,3}

        对每个测试样本，记真实头实体的排名倒数取平均

        Args:
            linker: KnowledgeLinker实例
            test_samples: [{"unknown": "field_name", "true_head": "expected_entity"}, ...]
        Returns:
            排序评估指标
        """
        ranks = []
        hits_1 = 0
        hits_3 = 0

        for sample in test_samples:
            unknown = sample.get("unknown", "")
            true_head = sample.get("true_head", "")
            if not unknown or not true_head:
                continue

            results = linker.link_entity(unknown, top_k=50)

            rank = None
            for i, r in enumerate(results):
                if r["head_name"] == true_head:
                    rank = i + 1
                    break

            if rank is not None:
                ranks.append(rank)
                if rank == 1:
                    hits_1 += 1
                if rank <= 3:
                    hits_3 += 1
            else:
                ranks.append(1000)

        n = len(ranks) if ranks else 1
        ranking_metrics = compute_ranking_metrics(ranks)

        self._results["completion"] = {
            "mrr": ranking_metrics["mrr"],
            "hit@1": ranking_metrics["hit@1"],
            "hit@3": ranking_metrics["hit@3"],
        }

        logger.info(
            f"知识补全评估: MRR={ranking_metrics['mrr']:.4f}, "
            f"Hit@1={ranking_metrics['hit@1']:.4f}, Hit@3={ranking_metrics['hit@3']:.4f}"
        )
        return ranking_metrics

    def evaluate_pipeline(
        self,
        frames: List[Dict],
        identifier,
        kg_builder,
        linker,
        true_entity_mapping: Dict[str, str] = None,
    ) -> Dict[str, Dict]:
        """端到端流水线评估"""
        results = {
            "classification": {},
            "completion": {},
            "end_to_end": {},
        }

        y_true = []
        y_pred = []

        for frame in frames:
            label = frame.get("device_type_label", "")
            result = identifier.identify_from_frame(frame)
            pred = result.get("device_type", "")

            label_map = {v: k for k, v in identifier.labels.items()}
            true_idx = label_map.get(label, -1)
            pred_idx = label_map.get(pred, -1)
            if true_idx >= 0 and pred_idx >= 0:
                y_true.append(true_idx)
                y_pred.append(pred_idx)

        if y_true:
            classification_metrics = EvaluationMetrics.from_raw(y_true, y_pred)
            results["classification"] = classification_metrics.to_dict()

        results["end_to_end"]["frame_count"] = len(frames)
        results["end_to_end"]["evaluated_at"] = str(self.output_dir)

        self._results["pipeline"] = results
        return results

    def save_report(self, filename: str = "") -> str:
        """保存评估报告"""
        if not filename:
            filename = "evaluation_report.json"

        filepath = self.output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self._results, f, ensure_ascii=False, indent=2)

        logger.info(f"评估报告已保存: {filepath}")
        return str(filepath)

    @staticmethod
    def generate_sample_data(num_samples: int = 100) -> List[Dict]:
        """生成评估用的样本数据"""
        import random

        device_types = ["IR", "CNC", "SOM", "SCM", "PM", "PW"]
        samples = []

        device_fields = {
            "IR": ["RobotArm", "Controller", "EndEffector", "DriveSystem", "AxisCount", "Payload", "MoveJ"],
            "CNC": ["Spindle", "ToolChanger", "Worktable", "CoolantSystem", "SpindleSpeed", "FeedRate", "CycleStart"],
            "SOM": ["Feeder", "Conveyor", "VisionSystem", "SortingActuator", "Throughput", "SortCount", "StartSorting"],
            "SCM": ["ScribingHead", "XYTable", "LaserSystem", "VisionAlign", "ScribingForce", "LaserPower"],
            "PM": ["PickHead", "PlacementHead", "FeederBank", "NozzleChanger", "PlacementAccuracy", "CycleTime"],
            "PW": ["WeldingHead", "PressureSystem", "PowerSupply", "CoolingSystem", "ElectrodeForce", "WeldStart"],
        }

        for i in range(num_samples):
            device_type = random.choice(device_types)
            fields = device_fields.get(device_type, ["Unknown"])

            num_fields = random.randint(3, min(len(fields), 8))
            selected_fields = random.sample(fields, num_fields)

            metadata = [
                {
                    "field_name": f,
                    "browse_name": f,
                    "value": str(random.randint(0, 10000)),
                    "data_type": random.choice(["Integer", "Double", "String"]),
                    "node_class": random.choice(["Variable", "Object", "Variable"]),
                }
                for f in selected_fields
            ]

            samples.append({
                "device_metadata": metadata,
                "device_type_label": device_type,
                "expected_entities": selected_fields,
            })

        return samples
