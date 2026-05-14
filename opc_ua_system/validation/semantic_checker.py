from typing import Any, Dict, List, Set, Tuple

from .report import VerificationResult


class SemanticChecker:
    """④ 语义保真度层 — 验证 KG 语义关系完整映射到输出"""

    RELATION_MAP = {
        "hasComponent": "children嵌套",
        "hasProperty": "FormItem/控件",
        "hasOperation": "Button/事件",
        "connectedTo": "children嵌套",
        "controlledBy": "children嵌套",
        "subtypeOf": "prop分组",
    }

    def check(
        self,
        schema: Dict[str, Any],
        kg_store: "TripleStore",
    ) -> VerificationResult:
        checks = []
        issues = []
        score_total = 0.0
        score_count = 0

        def add_check(name: str, passed: bool, value: str = ""):
            nonlocal score_total, score_count
            checks.append({"name": name, "passed": passed, "value": value})
            score_total += 1.0 if passed else 0.0
            score_count += 1

        kg_triples = list(kg_store._triples)

        # 按 relation 分类 KG 三元组
        kg_has_component: Set[Tuple[str, str]] = set()
        kg_has_property: Set[Tuple[str, str]] = set()
        kg_has_operation: Set[Tuple[str, str]] = set()
        kg_subtype_of: Set[Tuple[str, str]] = set()
        kg_other: List[str] = []

        for t in kg_triples:
            pair = (t.head, t.tail)
            if t.relation == "hasComponent":
                kg_has_component.add(pair)
            elif t.relation == "hasProperty":
                kg_has_property.add(pair)
            elif t.relation == "hasOperation":
                kg_has_operation.add(pair)
            elif t.relation == "subtypeOf":
                kg_subtype_of.add(pair)
            elif t.relation == "connectedTo" or t.relation == "controlledBy":
                kg_has_component.add(pair)
            else:
                kg_other.append(f"{t.head}-{t.relation}->{t.tail}")

        total_kg_triples = len(kg_triples)

        # 遍历输出找到已映射的语义
        mapped_component: Set[Tuple[str, str]] = set()
        mapped_property: Set[Tuple[str, str]] = set()
        mapped_operation: Set[Tuple[str, str]] = set()

        page = self._get_page_node(schema)

        def traverse(node: Dict, parent_title: str = ""):
            cn = node.get("componentName", "")
            props = node.get("props", {})
            title = props.get("title", "") if cn == "Card" else ""

            if cn == "Card":
                for child in node.get("children", []):
                    child_cn = child.get("componentName", "")
                    child_props = child.get("props", {})
                    child_title = ""

                    if child_cn == "Card":
                        child_title = child_props.get("title", "")
                        if parent_title:
                            mapped_component.add((parent_title, child_title))
                        elif title:
                            mapped_component.add((title, child_title))

                    elif child_cn in ("NumberPicker", "Input", "Switch"):
                        label = child_props.get("label", "")
                        mapped_property.add((title, label))

                    elif child_cn == "Button":
                        btn_text = child_props.get("children", "")
                        mapped_operation.add((title, btn_text))

                    traverse(child, child_title or title)

            elif cn == "NumberPicker" or cn == "Input" or cn == "Switch":
                label = props.get("label", "")
                if parent_title:
                    mapped_property.add((parent_title, label))

            elif cn == "Button":
                btn_text = props.get("children", "")
                if parent_title:
                    mapped_operation.add((parent_title, btn_text))

            for child in node.get("children", []):
                traverse(child, title)

        traverse(page)

        # 覆盖率计算
        comp_cov = (
            len(mapped_component & kg_has_component) / max(len(kg_has_component), 1)
        )
        prop_cov = (
            len(mapped_property & kg_has_property) / max(len(kg_has_property), 1)
        )
        op_cov = (
            len(mapped_operation & kg_has_operation) / max(len(kg_has_operation), 1)
        )

        # 总体覆盖率 (subtypeOf 不计入，因为当前未映射)
        mappable = len(kg_has_component) + len(kg_has_property) + len(kg_has_operation)
        mapped = (
            len(mapped_component & kg_has_component)
            + len(mapped_property & kg_has_property)
            + len(mapped_operation & kg_has_operation)
        )
        overall_coverage = mapped / max(mappable, 1)

        add_check(
            "hasComponent → children 映射覆盖率",
            comp_cov >= 0.90,
            f"{len(mapped_component & kg_has_component)}/{len(kg_has_component)} ({comp_cov:.0%})",
        )
        add_check(
            "hasProperty → 控件映射覆盖率",
            prop_cov >= 0.80,
            f"{len(mapped_property & kg_has_property)}/{len(kg_has_property)} ({prop_cov:.0%})",
        )
        add_check(
            "hasOperation → Button 映射覆盖率",
            op_cov >= 0.80,
            f"{len(mapped_operation & kg_has_operation)}/{len(kg_has_operation)} ({op_cov:.0%})",
        )
        add_check(
            "总体语义覆盖率",
            overall_coverage >= 0.85,
            f"{mapped}/{mappable} ({overall_coverage:.0%})",
        )

        # 未映射的三元组
        unmapped_component = kg_has_component - mapped_component
        unmapped_property = kg_has_property - mapped_property
        unmapped_operation = kg_has_operation - mapped_operation

        for h, t in unmapped_component:
            issues.append({
                "severity": "warning",
                "message": f"KG 三元组未映射到输出: {h} → hasComponent → {t}",
            })
        for h, t in unmapped_property:
            issues.append({
                "severity": "warning",
                "message": f"KG 三元组未映射到输出: {h} → hasProperty → {t}",
            })
        for h, t in unmapped_operation:
            issues.append({
                "severity": "warning",
                "message": f"KG 三元组未映射到输出: {h} → hasOperation → {t}",
            })

        # 伪影: 输出中存在但 KG 中没有的映射
        phantom_component = mapped_component - kg_has_component
        phantom_property = mapped_property - kg_has_property
        phantom_operation = mapped_operation - kg_has_operation

        for h, t in phantom_component:
            if h and t:
                issues.append({
                    "severity": "info",
                    "message": f"输出中存在 KG 未定义的组件关系: {h} 包含 {t}",
                })

        known_gaps = []
        if kg_subtype_of:
            known_gaps.append(
                f"subtypeOf 关系 ({len(kg_subtype_of)}条) 当前未映射到 prop 分组"
            )

        score = overall_coverage

        details = {
            "kg_total_triples": total_kg_triples,
            "kg_has_component": len(kg_has_component),
            "kg_has_property": len(kg_has_property),
            "kg_has_operation": len(kg_has_operation),
            "kg_subtype_of": len(kg_subtype_of),
            "overall_coverage": overall_coverage,
            "coverage_breakdown": {
                "hasComponent": comp_cov,
                "hasProperty": prop_cov,
                "hasOperation": op_cov,
            },
            "unmapped_count": (
                len(unmapped_component)
                + len(unmapped_property)
                + len(unmapped_operation)
            ),
            "phantom_count": (
                len(phantom_component) + len(phantom_property) + len(phantom_operation)
            ),
            "known_gaps": known_gaps,
        }

        return VerificationResult(
            layer="语义保真度",
            passed=score >= 0.85,
            score=score,
            checks=checks,
            issues=issues,
            details=details,
        )

    @staticmethod
    def _get_page_node(schema: Dict[str, Any]) -> Dict[str, Any]:
        trees = schema.get("componentsTree", [])
        return trees[0] if trees else {}
