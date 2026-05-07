from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class EvaluationMetrics:
    """评估指标"""
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    accuracy: float = 0.0
    mrr: float = 0.0
    hit_at_1: float = 0.0
    hit_at_3: float = 0.0
    hit_at_10: float = 0.0
    mean_rank: float = 0.0
    confusion_matrix: List[List[int]] = field(default_factory=list)
    classification_report: Dict = field(default_factory=dict)

    @classmethod
    def from_raw(
        cls,
        y_true: List[int],
        y_pred: List[int],
        labels: List[str] = None,
    ) -> "EvaluationMetrics":
        """从原始预测结果计算分类指标"""
        from sklearn.metrics import (
            accuracy_score,
            confusion_matrix,
            f1_score,
            precision_recall_fscore_support,
        )

        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average="weighted", zero_division=0
        )
        accuracy = accuracy_score(y_true, y_pred)
        cm = confusion_matrix(y_true, y_pred).tolist()

        return cls(
            precision=precision,
            recall=recall,
            f1_score=f1,
            accuracy=accuracy,
            confusion_matrix=cm,
        )

    def to_dict(self) -> Dict:
        return {
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "accuracy": self.accuracy,
            "mrr": self.mrr,
            "hit_at_1": self.hit_at_1,
            "hit_at_3": self.hit_at_3,
            "hit_at_10": self.hit_at_10,
            "mean_rank": self.mean_rank,
        }


def compute_ranking_metrics(
    ranks: List[int], 
    hits: List[bool] = None,
) -> Dict[str, float]:
    """计算排序评估指标

    Args:
        ranks: 每个测试样本中真实实体的排名列表
        hits: 每个测试样本是否命中列表
    Returns:
        {"mrr": ..., "hit@1": ..., "hit@3": ..., "hit@10": ..., "mean_rank": ...}
    """
    n = len(ranks)
    if n == 0:
        return {"mrr": 0.0, "hit@1": 0.0, "hit@3": 0.0, "hit@10": 0.0, "mean_rank": 0.0}

    mrr = sum(1.0 / max(r, 1) for r in ranks) / n

    metrics = {
        "mrr": mrr,
        "hit@1": sum(1 for r in ranks if r <= 1) / n,
        "hit@3": sum(1 for r in ranks if r <= 3) / n,
        "hit@10": sum(1 for r in ranks if r <= 10) / n,
        "mean_rank": sum(ranks) / n,
    }
    return metrics


def compute_metrics(
    y_true: List[int],
    y_pred: List[int],
    labels: List[str] = None,
    ranks: List[int] = None,
) -> EvaluationMetrics:
    """综合计算所有评估指标"""
    metrics = EvaluationMetrics.from_raw(y_true, y_pred, labels)
    if ranks:
        ranking = compute_ranking_metrics(ranks)
        metrics.mrr = ranking["mrr"]
        metrics.hit_at_1 = ranking["hit@1"]
        metrics.hit_at_3 = ranking["hit@3"]
        metrics.hit_at_10 = ranking["hit@10"]
        metrics.mean_rank = ranking["mean_rank"]
    return metrics
