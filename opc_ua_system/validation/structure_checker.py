from typing import Any, Dict, List, Set

from .report import VerificationResult


class StructureChecker:
    """③ 结构完整性层 — 验证组件树是合法的树结构"""

    MAX_DEPTH = 20

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

        trees = schema.get("componentsTree", [])
        if not trees:
            return VerificationResult(
                layer="结构完整性",
                passed=False,
                score=0.0,
                checks=[{"name": "组件树存在", "passed": False, "value": "为空"}],
                issues=[{"severity": "fatal", "message": "componentsTree 为空"}],
            )

        page = trees[0]

        # 3.1 根节点类型检查
        root_cn = page.get("componentName", "")
        add_check("根节点为 Page 容器", root_cn == "Page", root_cn)
        if root_cn != "Page":
            issues.append({
                "severity": "error",
                "message": f"根节点应为 Page, 实际: {root_cn}",
            })

        # 3.2 ID 唯一性
        ids: Set[str] = set()
        dup_ids: List[str] = []

        def collect_ids(node: Dict):
            nid = node.get("id", "")
            if nid:
                if nid in ids:
                    dup_ids.append(nid)
                else:
                    ids.add(nid)
            for child in node.get("children", []):
                collect_ids(child)

        collect_ids(page)
        add_check(
            "所有节点 ID 唯一",
            len(dup_ids) == 0,
            f"重复ID: {dup_ids}" if dup_ids else f"共 {len(ids)} 个唯一ID",
        )
        for did in dup_ids:
            issues.append({"severity": "error", "message": f"重复节点 ID: {did}"})

        # 3.3 无孤立 Variable (没有父 Card 直接挂在 Page 下的 Variable)
        orphan_vars: List[str] = []

        def check_orphans(node: Dict, parent_cn: str = ""):
            cn = node.get("componentName", "")
            if cn in ("NumberPicker", "Input", "Switch"):
                if parent_cn not in ("Card",):
                    label = (node.get("props") or {}).get("label", cn)
                    orphan_vars.append(label)

            for child in node.get("children", []):
                check_orphans(child, cn)

        check_orphans(page, "Page")
        add_check(
            "无孤立 Variable 节点",
            len(orphan_vars) == 0,
            str(orphan_vars) if orphan_vars else "无",
        )
        for ov in orphan_vars:
            issues.append({
                "severity": "warning",
                "message": f"孤立 Variable '{ov}' 直接挂在非 Card 容器下",
            })

        # 3.4 无空 Card (没有 children 的 Object 容器)
        empty_cards: List[str] = []

        def check_empty_cards(node: Dict):
            cn = node.get("componentName", "")
            if cn == "Card" and len(node.get("children", [])) == 0:
                title = (node.get("props") or {}).get("title", cn)
                empty_cards.append(title)
            for child in node.get("children", []):
                check_empty_cards(child)

        check_empty_cards(page)
        add_check(
            "无空 Card 容器",
            len(empty_cards) == 0,
            str(empty_cards) if empty_cards else "无",
        )
        for ec in empty_cards:
            issues.append({
                "severity": "warning",
                "message": f"空 Card 容器 '{ec}' — 建议改为 Typography 或添加子节点",
            })

        # 3.5 无过深嵌套
        depth_issues: List[str] = []

        def check_depth(node: Dict, depth: int, path: str = ""):
            cn = node.get("componentName", "")
            current_path = f"{path}/{cn}" if path else cn
            if depth > self.MAX_DEPTH:
                depth_issues.append(f"{current_path} (深度={depth})")
                return
            for child in node.get("children", []):
                check_depth(child, depth + 1, current_path)

        check_depth(page, 1)
        add_check(
            f"嵌套深度不超过 {self.MAX_DEPTH}",
            len(depth_issues) == 0,
            str(depth_issues) if depth_issues else "合规",
        )
        for di in depth_issues:
            issues.append({
                "severity": "warning",
                "message": f"嵌套过深: {di}",
            })

        # 3.6 children 字段是 list
        bad_children: List[str] = []

        def check_children_type(node: Dict):
            cn = node.get("componentName", "?")
            ch = node.get("children")
            if ch is not None and not isinstance(ch, list):
                bad_children.append(cn)
            if isinstance(ch, list):
                for child in ch:
                    check_children_type(child)

        check_children_type(page)
        add_check(
            "children 字段均为 list",
            len(bad_children) == 0,
            str(bad_children) if bad_children else "合规",
        )

        score = score_total / max(score_count, 1)
        return VerificationResult(
            layer="结构完整性",
            passed=len(issues) == 0,
            score=score,
            checks=checks,
            issues=issues,
            details={
                "total_nodes": len(ids),
                "max_depth": self._max_depth_of(page),
                "orphan_variables": len(orphan_vars),
                "empty_cards": len(empty_cards),
                "duplicate_ids": len(dup_ids),
            },
        )

    @staticmethod
    def _max_depth_of(node: Dict, depth: int = 1) -> int:
        max_d = depth
        for child in node.get("children", []):
            max_d = max(max_d, StructureChecker._max_depth_of(child, depth + 1))
        return max_d
