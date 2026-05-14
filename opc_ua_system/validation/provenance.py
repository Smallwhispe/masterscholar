from typing import Any, Dict, List, Optional, Tuple

from .report import VerificationResult


class ProvenanceChecker:
    """① 溯源追溯层 — 验证每个输出元素可追溯到源数据

    核心思想:
    生成的 Schema 中每个节点 (Card/ NumberPicker/ Button) 都应该能
    反向追溯到原始的 KG 三元组 或 OPC UA 帧节点。
    不能追溯的节点 = 幻影 (phantom), 不可信。
    """

    def check(
        self,
        schema: Dict[str, Any],
        kg_store: "TripleStore",
        frame: Optional[Dict[str, Any]] = None,
    ) -> VerificationResult:
        checks = []
        issues = []

        page = self._get_page_node(schema)
        if page is None:
            return VerificationResult(
                layer="溯源追溯",
                passed=False,
                score=0.0,
                checks=checks,
                issues=[{"severity": "fatal", "message": "未找到 Page 节点"}],
            )

        kg_triples_list = list(kg_store._triples)
        kg_entity_set = set()
        kg_property_pairs = set()
        kg_method_pairs = set()
        kg_component_pairs = set()

        for t in kg_triples_list:
            kg_entity_set.add(t.head)
            kg_entity_set.add(t.tail)
            if t.relation == "hasProperty":
                kg_property_pairs.add((t.head, t.tail))
            elif t.relation == "hasOperation":
                kg_method_pairs.add((t.head, t.tail))
            elif t.relation == "hasComponent":
                kg_component_pairs.add((t.head, t.tail))

        frame_var_names = set()
        frame_var_vals: Dict[str, Any] = {}
        if frame:
            for nid, node in frame.get("nodes", {}).items():
                if node.get("node_class") == "Variable":
                    dn = node.get("display_name", "")
                    bn = node.get("browse_name", "")
                    frame_var_names.add(dn)
                    frame_var_names.add(bn)
                    val = node.get("value")
                    if val is not None:
                        frame_var_vals[dn] = val
                        frame_var_vals[bn] = val

        traceable = 0
        phantom = []
        phantom_nodes = []

        def traverse(node: Dict, parent_title: str = ""):
            nonlocal traceable

            comp_name = node.get("componentName", "")
            props = node.get("props", {})
            node_title = ""
            sources = []

            if comp_name == "Card":
                node_title = props.get("title", "")
                # 溯源: title 应该匹配 KG 中的某个 Object 实体
                if node_title in kg_entity_set:
                    sources.append(f"KG.entity:{node_title}")

            elif comp_name in ("NumberPicker", "Input", "Switch"):
                label = props.get("label", "")
                node_title = label
                # 优先溯源到 Frame 中的 Variable
                if label in frame_var_names:
                    sources.append(f"Frame.variable:{label}")
                # 也溯源到 KG 中的 Property
                if parent_title and (parent_title, label) in kg_property_pairs:
                    sources.append(f"KG.property:{parent_title}->{label}")
                elif not sources:
                    # 尝试模糊匹配
                    for hp, tp in kg_property_pairs:
                        if label == tp or label.lower() in tp.lower():
                            sources.append(f"KG.property:{hp}->{tp}")
                            break

            elif comp_name == "Button":
                children = props.get("children", "")
                node_title = children
                if parent_title and (parent_title, children) in kg_method_pairs:
                    sources.append(f"KG.method:{parent_title}->{children}")

            elif comp_name == "Typography":
                node_title = props.get("children", "")

            if comp_name not in ("Page",):
                if sources:
                    traceable += 1
                else:
                    phantom.append(node_title or comp_name)
                    phantom_nodes.append({
                        "component": comp_name,
                        "title": node_title,
                        "parent": parent_title,
                    })

            for child in node.get("children", []):
                traverse(child, node_title)

        traverse(page)

        total_nodes = max(traceable + len(phantom), 1)
        covered = traceable
        score = covered / total_nodes if total_nodes > 0 else 0.0

        checks.append({
            "name": "可溯源节点覆盖率",
            "passed": score >= 0.90,
            "value": f"{covered}/{total_nodes} ({score:.0%})",
            "threshold": ">= 90%",
        })

        if phantom:
            for p in phantom_nodes:
                issues.append({
                    "severity": "warning",
                    "message": (
                        f"幻影节点: {p['component']} '{p['title']}' "
                        f"(父: {p['parent']}) — 无法追溯到 KG 或 Frame"
                    ),
                })

        detail_kg_entities = len(kg_entity_set)
        detail_frame_vars = len(frame_var_names) if frame else 0
        details = {
            "traceable_nodes": traceable,
            "phantom_nodes": len(phantom),
            "phantom_list": phantom_nodes,
            "kg_entities_available": detail_kg_entities,
            "frame_variables_available": detail_frame_vars,
            "source_breakdown": {
                "kg_only": traceable,
                "frame_only": 0,
                "both": 0,
            },
        }

        return VerificationResult(
            layer="溯源追溯",
            passed=len(phantom) == 0,
            score=score,
            checks=checks,
            issues=issues,
            details=details,
        )

    @staticmethod
    def _get_page_node(schema: Dict[str, Any]) -> Optional[Dict]:
        trees = schema.get("componentsTree", [])
        if not trees:
            return None
        return trees[0]
