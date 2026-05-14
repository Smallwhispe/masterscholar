import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .provenance import ProvenanceChecker
from .schema_validator import SchemaValidator
from .structure_checker import StructureChecker
from .semantic_checker import SemanticChecker
from .data_consistency import DataConsistencyChecker
from .render_checker import RenderChecker
from .report import VerificationReport, VerificationResult

logger = logging.getLogger(__name__)


class TrustVerifier:
    """低代码 Schema 可信验证框架 — 六层全方位验证

    验证层次:
    ① 溯源追溯      — 每个输出元素可追溯到 KG 三元组或 Frame 节点
    ② Schema协议合规 — JSON 符合 LowCodeEngine 搭建协议规范
    ③ 结构完整性    — 组件树是合法的树结构
    ④ 语义保真度    — KG 语义关系完整映射到输出
    ⑤ 数据一致性    — Frame 运行时值与输出一致
    ⑥ 运行时验证    — Schema 在 LowCodeEngine 中可渲染

    使用示例:
        verifier = TrustVerifier()
        report = verifier.verify_all(
            schema=schema,
            kg_store=kg_builder.store,
            frame=frame,
        )
        print(report.summary())
        verifier.save_report(report, "output/verify/report.json")
    """

    def __init__(self):
        self.provenance = ProvenanceChecker()
        self.schema_validator = SchemaValidator()
        self.structure = StructureChecker()
        self.semantic = SemanticChecker()
        self.data_consistency = DataConsistencyChecker()
        self.render = RenderChecker()

    def verify_all(
        self,
        schema: Dict[str, Any],
        kg_store: "TripleStore",
        frame: Optional[Dict[str, Any]] = None,
    ) -> VerificationReport:
        report = VerificationReport()

        logger.info("开始六层可信验证...")

        # ① 溯源追溯
        logger.info("  ① 溯源追溯...")
        r1 = self.provenance.check(schema, kg_store, frame)
        report.add_result(r1)

        # ② Schema协议合规
        logger.info("  ② Schema协议合规...")
        r2 = self.schema_validator.check(schema)
        report.add_result(r2)

        # ③ 结构完整性
        logger.info("  ③ 结构完整性...")
        r3 = self.structure.check(schema)
        report.add_result(r3)

        # ④ 语义保真度
        logger.info("  ④ 语义保真度...")
        r4 = self.semantic.check(schema, kg_store)
        report.add_result(r4)

        # ⑤ 数据一致性
        logger.info("  ⑤ 数据一致性...")
        r5 = self.data_consistency.check(schema, frame)
        report.add_result(r5)

        # ⑥ 运行时验证
        logger.info("  ⑥ 运行时验证...")
        r6 = self.render.check(schema)
        report.add_result(r6)

        report.set_meta(
            total_layers=6,
            layers_passed=sum(
                1 for r in report.results if r.passed
            ),
        )

        logger.info(
            f"验证完成: 综合评分 {report.overall_score:.2%}, "
            f"通过 {sum(1 for r in report.results if r.passed)}/6 层, "
            f"问题 {report.total_issues} 个"
        )
        return report

    def verify_schema_only(self, schema: Dict[str, Any]) -> VerificationReport:
        report = VerificationReport()
        report.add_result(self.schema_validator.check(schema))
        report.add_result(self.structure.check(schema))
        report.add_result(self.render.check(schema))
        return report

    def save_report(
        self,
        report: VerificationReport,
        output_path: str,
    ) -> str:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = report.to_dict()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"验证报告已保存: {output_path}")
        return str(path)

    @staticmethod
    def verify_and_print(
        schema: Dict[str, Any],
        kg_store: "TripleStore",
        frame: Optional[Dict[str, Any]] = None,
    ) -> VerificationReport:
        verifier = TrustVerifier()
        report = verifier.verify_all(schema, kg_store, frame)
        print(report.summary())
        return report
