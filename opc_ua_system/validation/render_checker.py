from typing import Any, Dict, List, Set

from .report import VerificationResult


class RenderChecker:
    """⑥ 运行时验证层 — 静态检查 Schema 在 LowCodeEngine 中的可渲染性

    由于不引入实际 ReactRenderer, 采用静态检查:
    - 组件名解析: 验证每个 componentName 在 componentsMap 中有注册
    - props 可解析性: 检查 JSExpression 语法
    - events 方法引用一致性: Button.onClick 引用的方法存在于 methods 中
    """

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

        map_names: Set[str] = set()
        for cm in schema.get("componentsMap", []):
            cn = cm.get("componentName", "")
            if cn:
                map_names.add(cn)

        trees = schema.get("componentsTree", [])
        page = trees[0] if trees else {}

        # 6.1 所有组件名可解析
        unresolved: List[str] = []

        def check_component_defined(node: Dict):
            cn = node.get("componentName", "")
            if cn and cn not in map_names:
                unresolved.append(cn)
            for child in node.get("children", []):
                check_component_defined(child)

        check_component_defined(page)
        add_check(
            "所有组件名在 componentsMap 中有定义",
            len(unresolved) == 0,
            str(unresolved) if unresolved else "全部可解析",
        )
        for un in unresolved:
            issues.append({
                "severity": "error",
                "message": f"组件 '{un}' 在 componentsMap 中未定义，渲染将失败",
            })

        # 6.2 methods 引用一致性
        methods_declared = set(page.get("methods", {}).keys())
        method_refs_found: List[str] = []

        def find_method_refs(node: Dict):
            props = node.get("props", {})
            if node.get("componentName") == "Button":
                onclick = props.get("onClick", {})
                if isinstance(onclick, dict) and onclick.get("type") == "JSExpression":
                    val = onclick.get("value", "")
                    prefix = "this.methods."
                    if val.startswith(prefix):
                        ref = val[len(prefix):]
                        method_refs_found.append(ref)

            for child in node.get("children", []):
                find_method_refs(child)

        find_method_refs(page)

        dangling_refs = set(method_refs_found) - methods_declared
        add_check(
            "Button 事件引用的方法在 Page.methods 中存在",
            len(dangling_refs) == 0,
            str(sorted(dangling_refs)) if dangling_refs else "全部一致",
        )
        for dr in dangling_refs:
            issues.append({
                "severity": "error",
                "message": (
                    f"Button 引用未定义的方法 'this.methods.{dr}', "
                    "渲染时可能抛出 ReferenceError"
                ),
            })

        # 6.3 props 结构有效
        bad_props: List[str] = []

        def check_props_validity(node: Dict):
            cn = node.get("componentName", "?")
            props = node.get("props", {})
            for key, val in (props or {}).items():
                if isinstance(val, dict):
                    t = val.get("type", "")
                    v = val.get("value", "")
                    if t in ("JSExpression", "JSFunction", "JSSlot") and not v and v != "":
                        if t != "JSSlot":
                            bad_props.append(f"{cn}.{key} (type={t}, value=空)")
                elif isinstance(val, str) and val.startswith("{{") and val.endswith("}}"):
                    bad_props.append(f"{cn}.{key} (旧版表达式: {val})")

            for child in node.get("children", []):
                check_props_validity(child)

        check_props_validity(page)
        add_check(
            "props 中 JSExpression/JSFunction 格式有效",
            len(bad_props) == 0,
            str(bad_props) if bad_props else "全部有效",
        )
        for bp in bad_props:
            issues.append({
                "severity": "warning",
                "message": f"可疑 prop: {bp}",
            })

        # 6.4 必要组件已注册
        expected_builtins = {"Page", "Card", "NumberPicker", "Input", "Button", "Typography"}
        missing_expected = expected_builtins - map_names
        add_check(
            "常用内置组件已注册",
            len(missing_expected) == 0,
            f"缺失: {missing_expected}" if missing_expected else "全部注册",
        )
        for me in missing_expected:
            issues.append({
                "severity": "info",
                "message": f"建议注册组件 '{me}' 但当前未在 componentsMap 中",
            })

        score = score_total / max(score_count, 1)
        return VerificationResult(
            layer="运行时验证",
            passed=len([i for i in issues if i["severity"] in ("error", "fatal")]) == 0,
            score=score,
            checks=checks,
            issues=issues,
            details={
                "registered_components": len(map_names),
                "unresolved_components": len(unresolved),
                "dangling_method_refs": len(dangling_refs),
            },
        )
