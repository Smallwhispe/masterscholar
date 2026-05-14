from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class VerificationResult:
    layer: str
    passed: bool
    score: float = 0.0
    checks: List[Dict[str, Any]] = field(default_factory=list)
    issues: List[Dict[str, Any]] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class VerificationReport:
    """六层可信验证报告"""

    def __init__(self):
        self.results: List[VerificationResult] = []
        self._meta: Dict[str, Any] = {}

    def add_result(self, result: VerificationResult) -> None:
        self.results.append(result)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def overall_score(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.score for r in self.results) / len(self.results)

    @property
    def layer_scores(self) -> Dict[str, float]:
        return {r.layer: r.score for r in self.results}

    @property
    def total_issues(self) -> int:
        return sum(len(r.issues) for r in self.results)

    @property
    def total_checks(self) -> int:
        return sum(len(r.checks) for r in self.results)

    def set_meta(self, **kwargs) -> None:
        self._meta.update(kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "meta": self._meta,
            "overall_score": self.overall_score,
            "all_passed": self.all_passed,
            "total_checks": self.total_checks,
            "total_issues": self.total_issues,
            "layer_scores": self.layer_scores,
            "layers": [
                {
                    "layer": r.layer,
                    "passed": r.passed,
                    "score": r.score,
                    "check_count": len(r.checks),
                    "issue_count": len(r.issues),
                    "checks": r.checks,
                    "issues": r.issues,
                    "details": r.details,
                }
                for r in self.results
            ],
        }

    def summary(self) -> str:
        lines = ["=" * 60, "低代码生成可信验证报告", "=" * 60, ""]
        lines.append(f"综合评分: {self.overall_score:.2%}")
        lines.append(f"全部通过: {'是' if self.all_passed else '否'}")
        lines.append(f"总检查项: {self.total_checks}  总问题: {self.total_issues}")
        lines.append("")
        lines.append(f"{'层次':<20} {'评分':>8} {'结果':>6}  {'检查/问题'}")
        lines.append("-" * 50)
        for r in self.results:
            status = "通过" if r.passed else "未通过"
            lines.append(
                f"{r.layer:<20} {r.score:>7.0%}  {status:>4}  "
                f"{len(r.checks)}/{len(r.issues)}"
            )
        lines.append("-" * 50)
        for r in self.results:
            if r.issues:
                lines.append(f"\n【{r.layer}】问题详情:")
                for i, issue in enumerate(r.issues, 1):
                    lines.append(
                        f"  {i}. [{issue.get('severity', '')}] "
                        f"{issue.get('message', '')}"
                    )
        lines.append("\n" + "=" * 60)
        return "\n".join(lines)
