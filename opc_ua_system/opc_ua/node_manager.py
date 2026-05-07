import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class NodeManager:
    """OPC UA节点管理器 - 负责节点的增删改查和向服务器加载节点集合"""

    def __init__(self, namespace_uri: str = "http://example.org/UA/"):
        self.namespace_uri = namespace_uri
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._node_index: Dict[str, Dict[str, Any]] = {}

    def load_nodes_from_frame(self, frame: Dict[str, Any]) -> None:
        """从数据帧加载节点信息"""
        nodes = frame.get("nodes", {})
        self._nodes = nodes
        self._build_index()
        logger.info(f"从数据帧加载了 {len(nodes)} 个节点")

    def load_nodes_from_json(self, filepath: str) -> None:
        """从JSON文件加载节点信息"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.load_nodes_from_frame(data)

    def _build_index(self) -> None:
        """构建节点索引（按display_name和browse_name）"""
        self._node_index = {}
        for node_id, node in self._nodes.items():
            dn = node.get("display_name", "").lower()
            bn = node.get("browse_name", "").lower()
            if dn:
                self._node_index[f"name:{dn}"] = node_id
            if bn:
                self._node_index[f"browse:{bn}"] = node_id

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """根据node_id获取节点"""
        return self._nodes.get(node_id)

    def find_by_name(self, name: str) -> Optional[str]:
        """根据名称查找节点ID"""
        key = f"name:{name.lower()}"
        return self._node_index.get(key)

    def find_by_browse_name(self, browse_name: str) -> Optional[str]:
        """根据BrowseName查找节点ID"""
        key = f"browse:{browse_name.lower()}"
        return self._node_index.get(key)

    def get_node_hierarchy(
        self, node_id: str
    ) -> List[Dict[str, Any]]:
        """获取节点的完整层级路径（从根到该节点）"""
        path = []
        current_id = node_id
        visited = set()

        while current_id and current_id not in visited:
            visited.add(current_id)
            node = self._nodes.get(current_id)
            if node is None:
                break
            path.insert(0, {
                "node_id": current_id,
                "display_name": node.get("display_name", ""),
                "node_class": node.get("node_class", ""),
            })
            current_id = node.get("parent_node_id")

        return path

    def get_all_variable_nodes(self) -> List[Dict[str, Any]]:
        """获取所有Variable类型节点"""
        return [
            node
            for node in self._nodes.values()
            if "Variable" in node.get("node_class", "")
        ]

    def get_all_object_nodes(self) -> List[Dict[str, Any]]:
        """获取所有Object类型节点"""
        return [
            node
            for node in self._nodes.values()
            if "Object" in node.get("node_class", "")
        ]

    def get_all_method_nodes(self) -> List[Dict[str, Any]]:
        """获取所有Method类型节点"""
        return [
            node
            for node in self._nodes.values()
            if "Method" in node.get("node_class", "")
        ]

    def generate_nodeset(self) -> Dict[str, Any]:
        """生成节点集合（供UA服务器模块加载到服务器）"""
        return {
            "namespace_uri": self.namespace_uri,
            "node_count": len(self._nodes),
            "nodes": self._nodes,
            "objects": self.get_all_object_nodes(),
            "variables": self.get_all_variable_nodes(),
            "methods": self.get_all_method_nodes(),
        }

    def export_nodeset(self, output_path: str) -> str:
        """导出节点集合到JSON文件"""
        nodeset = self.generate_nodeset()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(nodeset, f, ensure_ascii=False, indent=2)

        logger.info(f"节点集合已导出: {output_path}")
        return str(output_path)
