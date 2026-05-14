from typing import Any, Dict, List, Set

from .report import VerificationResult


class SchemaValidator:
    """② Schema 协议合规层 — 验证 JSON 符合 LowCodeEngine 搭建协议"""

    REQUIRED_TOP_FIELDS = {
        "version", "componentsMap", "componentsTree",
    }
    OPTIONAL_TOP_FIELDS = {
        "utils", "i18n", "constants", "css", "config",
        "meta", "dataSource", "router", "pages",
    }
    VALID_CONTAINERS = {"Page", "Block", "Component"}
    VALID_SPECIAL_TYPES = {"JSExpression", "JSFunction", "JSSlot", "JSBlock"}

    def check(self, schema: Dict[str, Any]) -> VerificationResult:
        checks = []
        issues = []
        score_total = 0.0
        score_count = 0

        def add_check(name: str, passed: bool, value: str = ""):
            nonlocal score_total, score_count
            checks.append({"name": name, "passed": passed, "value": value})
            score_total += 1.0 if passed else 0.0
            score_count += 1

        # 2.1 顶层必填字段
        missing_top = self.REQUIRED_TOP_FIELDS - set(schema.keys())
        add_check(
            "顶层必填字段完整",
            len(missing_top) == 0,
            f"缺失: {missing_top}" if missing_top else "完整",
        )
        if missing_top:
            for mf in missing_top:
                issues.append({"severity": "fatal", "message": f"缺少顶层必填字段: {mf}"})

        # 2.2 version 有效性
        version = schema.get("version", "")
        add_check(
            "协议版本号有效",
            bool(version) and "." in str(version),
            str(version),
        )
        if not version:
            issues.append({"severity": "error", "message": "协议版本号缺失或无效"})

        # 2.3 componentsMap 与 componentsTree 一致性
        map_names = set()
        for cm in schema.get("componentsMap", []):
            cn = cm.get("componentName", "")
            if cn:
                map_names.add(cn)
        tree_names: Set[str] = set()

        def collect_names(node: Dict):
            cn = node.get("componentName", "")
            if cn:
                tree_names.add(cn)
            for child in node.get("children", []):
                collect_names(child)

        for tree in schema.get("componentsTree", []):
            collect_names(tree)

        missing_in_map = tree_names - map_names - {"Page"}
        add_check(
            "componentsMap 覆盖所有使用的组件",
            len(missing_in_map) == 0,
            f"未注册: {missing_in_map}" if missing_in_map else "全部覆盖",
        )
        for mn in missing_in_map:
            issues.append({
                "severity": "error",
                "message": f"组件 '{mn}' 在 componentsTree 中使用但未在 componentsMap 注册",
            })

        # 2.4 componentName 命名规范 (大写开头)
        bad_names = []

        def check_naming(node: Dict):
            cn = node.get("componentName", "")
            if cn and not cn[0].isupper():
                bad_names.append(cn)
            for child in node.get("children", []):
                check_naming(child)

        for tree in schema.get("componentsTree", []):
            check_naming(tree)

        add_check(
            "组件名大写字母开头",
            len(bad_names) == 0,
            str(bad_names) if bad_names else "合规",
        )
        for bn in bad_names:
            issues.append({
                "severity": "warning",
                "message": f"组件名 '{bn}' 未以大写字母开头",
            })

        # 2.5 JSExpression/JSFunction 格式
        bad_expr = []

        def check_expressions(node: Dict):
            for key, val in (node.get("props", {}) or {}).items():
                if isinstance(val, dict) and val.get("type") in self.VALID_SPECIAL_TYPES:
                    if "value" not in val:
                        bad_expr.append(f"{node.get('componentName','?')}.{key}")
            for child in node.get("children", []):
                check_expressions(child)

        for tree in schema.get("componentsTree", []):
            check_expressions(tree)

        add_check(
            "JSExpression/JSFunction 格式正确",
            len(bad_expr) == 0,
            str(bad_expr) if bad_expr else "全部正确",
        )
        for be in bad_expr:
            issues.append({
                "severity": "error",
                "message": f"特殊类型字段缺少 'value': {be}",
            })

        # 2.6 根节点是合法容器
        root_type_ok = True
        for tree in schema.get("componentsTree", []):
            cn = tree.get("componentName", "")
            if cn not in self.VALID_CONTAINERS:
                root_type_ok = False
                issues.append({
                    "severity": "error",
                    "message": f"componentsTree 根节点类型应为 Page/Block/Component, 实际: {cn}",
                })
        add_check("根节点类型合法", root_type_ok)

        score = score_total / max(score_count, 1)
        return VerificationResult(
            layer="Schema协议合规",
            passed=len(issues) == 0,
            score=score,
            checks=checks,
            issues=issues,
            details={
                "components_in_map": len(map_names),
                "components_in_tree": len(tree_names),
                "missing_in_map": sorted(missing_in_map),
                "bad_names": bad_names,
            },
        )
