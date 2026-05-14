from typing import Any, Dict, List, Optional, Tuple

from .report import VerificationResult

TYPE_TO_PROP_TYPE = {
    "Integer": "number", "UInt16": "number", "UInt32": "number",
    "Int16": "number", "Int32": "number", "Int64": "number",
    "Double": "number", "Float": "number", "Boolean": "bool",
    "String": "string", "ByteString": "string",
}


class DataConsistencyChecker:
    """⑤ 数据一致性层 — 验证 Frame 中的运行时数据正确写入 Schema"""

    def check(
        self,
        schema: Dict[str, Any],
        frame: Optional[Dict[str, Any]] = None,
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

        if frame is None:
            return VerificationResult(
                layer="数据一致性",
                passed=True,
                score=1.0,
                checks=[{"name": "无需验证", "passed": True, "value": "无输入数据帧"}],
                issues=[],
                details={"frame_provided": False},
            )

        nodes = frame.get("nodes", {})

        frame_vars: Dict[str, Dict[str, Any]] = {}
        for nid, node in nodes.items():
            if node.get("node_class") == "Variable":
                dn = node.get("display_name", "")
                bn = node.get("browse_name", "")
                entry = {
                    "value": node.get("value"),
                    "data_type": node.get("data_type", "String"),
                    "node_id": node.get("node_id", ""),
                }
                if dn:
                    frame_vars[dn] = entry
                if bn and bn != dn:
                    frame_vars[bn] = entry

        matched = 0
        mismatched_value = []
        mismatched_type = []
        schema_vars_found = 0

        page = self._get_page_node(schema)

        def traverse(node: Dict):
            nonlocal matched, schema_vars_found
            cn = node.get("componentName", "")
            props = node.get("props", {})

            if cn in ("NumberPicker", "Input", "Switch"):
                label = props.get("label", "")
                schema_vars_found += 1

                if label in frame_vars:
                    matched += 1
                    fv = frame_vars[label]

                    # 值对比
                    schema_val = props.get("value") or props.get("checked")
                    frame_val = fv["value"]
                    if not self._values_match(schema_val, frame_val, cn):
                        mismatched_value.append({
                            "name": label,
                            "expected": frame_val,
                            "actual": schema_val,
                            "component": cn,
                        })

                    # 类型对比
                    frame_type = fv.get("data_type", "String")
                    expected_pt = TYPE_TO_PROP_TYPE.get(frame_type, "string")
                    if cn == "NumberPicker" and expected_pt != "number":
                        mismatched_type.append({
                            "name": label,
                            "frame_type": frame_type,
                            "component": cn,
                            "expected_prop_type": expected_pt,
                        })
                    elif cn == "Switch" and expected_pt != "bool":
                        mismatched_type.append({
                            "name": label,
                            "frame_type": frame_type,
                            "component": cn,
                            "expected_prop_type": expected_pt,
                        })

            for child in node.get("children", []):
                traverse(child)

        traverse(page)

        # 覆盖率
        var_coverage = matched / max(schema_vars_found, 1)

        add_check(
            "Variable 值与 Frame 一致",
            len(mismatched_value) == 0,
            f"不一致: {len(mismatched_value)}" if mismatched_value else "全部一致",
        )
        for mv in mismatched_value:
            issues.append({
                "severity": "error",
                "message": (
                    f"值不一致: '{mv['name']}' — "
                    f"Frame值={mv['expected']}, Schema值={mv['actual']}"
                ),
            })

        add_check(
            "data_type → 组件类型映射正确",
            len(mismatched_type) == 0,
            f"映射错误: {len(mismatched_type)}" if mismatched_type else "全部正确",
        )
        for mt in mismatched_type:
            issues.append({
                "severity": "warning",
                "message": (
                    f"类型映射可能不当: '{mt['name']}' — "
                    f"Frame data_type={mt['frame_type']}, 使用了 {mt['component']}"
                ),
            })

        # 元信息一致性
        frame_server = frame.get("server_url", "")
        constants_server = (schema.get("constants") or {}).get("SERVER_URL", "")
        meta_ok = (
            (not frame_server or constants_server == frame_server)
        )
        add_check(
            "Frame 元信息正确注入",
            meta_ok,
            f"server_url: {constants_server[:30]}..." if constants_server else "无",
        )
        if not meta_ok and frame_server:
            issues.append({
                "severity": "warning",
                "message": (
                    f"SERVER_URL 不一致: Frame={frame_server}, Schema={constants_server}"
                ),
            })

        frame_frame_id = frame.get("frame_id", "")
        constants_fid = (schema.get("constants") or {}).get("FRAME_ID", "")
        fid_ok = (not frame_frame_id or constants_fid == frame_frame_id)
        add_check("FRAME_ID 正确注入", fid_ok, str(constants_fid))

        val_score = 1.0 if len(mismatched_value) == 0 else 0.5
        type_score = 1.0 if len(mismatched_type) == 0 else 0.7
        score = (val_score + type_score + (1.0 if meta_ok else 0.5)) / 3

        details = {
            "frame_variables_total": len(frame_vars),
            "schema_variables_found": schema_vars_found,
            "matched_variables": matched,
            "coverage": var_coverage,
            "value_mismatches": len(mismatched_value),
            "type_mismatches": len(mismatched_type),
            "mismatched_details": {
                "value": mismatched_value,
                "type": mismatched_type,
            },
        }

        return VerificationResult(
            layer="数据一致性",
            passed=score >= 0.90,
            score=score,
            checks=checks,
            issues=issues,
            details=details,
        )

    @staticmethod
    def _values_match(schema_val: Any, frame_val: Any, component: str) -> bool:
        if schema_val is None and frame_val is None:
            return True
        if schema_val is None or frame_val is None:
            return False
        try:
            if component == "NumberPicker":
                sv = float(str(schema_val))
                fv = float(str(frame_val))
                return abs(sv - fv) < 1e-6
            elif component == "Switch":
                sv = str(schema_val).lower() in ("true", "1", "yes")
                fv = str(frame_val).lower() in ("true", "1", "yes")
                return sv == fv
            return str(schema_val) == str(frame_val)
        except (ValueError, TypeError):
            return str(schema_val) == str(frame_val)

    @staticmethod
    def _get_page_node(schema: Dict[str, Any]) -> Dict[str, Any]:
        trees = schema.get("componentsTree", [])
        return trees[0] if trees else {}
