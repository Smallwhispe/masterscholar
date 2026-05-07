import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AddressSpaceBuilder:
    """OPC UA地址空间构建器

    功能:
    1. 加载生成的Nodeset XML信息模型
    2. 将节点集合加载到OPC UA服务器
    3. 构建完整的地址空间

    流程:
    1. 从IMKG生成OWL语义本体
    2. OWL转换为Nodeset XML
    3. 将节点集合加载到UA服务器构建地址空间
    """

    def __init__(
        self,
        namespace_uri: str = "http://example.org/UA/",
        namespace_index: int = 2,
    ):
        self.namespace_uri = namespace_uri
        self.namespace_index = namespace_index
        self._nodes: Dict[str, Dict] = {}
        self._address_space: Dict[str, Any] = {
            "objects": {},
            "variables": {},
            "methods": {},
            "references": [],
            "views": {},
        }

    def load_nodeset_xml(self, nodeset_path: str) -> Dict[str, Any]:
        """加载Nodeset XML文件并解析"""
        try:
            from lxml import etree
        except ImportError:
            logger.error("需要安装lxml: pip install lxml")
            return {}

        path = Path(nodeset_path)
        if not path.exists():
            logger.error(f"Nodeset XML文件不存在: {nodeset_path}")
            return {}

        try:
            tree = etree.parse(str(path))
            root = tree.getroot()

            nsmap = {
                "ua": "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd",
            }

            objects = root.findall(".//ua:UAObject", nsmap)
            variables = root.findall(".//ua:UAVariable", nsmap)
            methods = root.findall(".//ua:UAMethod", nsmap)
            references = root.findall(".//ua:UAReference", nsmap)

            for obj in objects:
                node_id = obj.get("NodeId", "")
                self._address_space["objects"][node_id] = {
                    "node_id": node_id,
                    "browse_name": obj.get("BrowseName", ""),
                    "display_name": obj.get("DisplayName", ""),
                    "node_class": "Object",
                    "children": [],
                }

            for var in variables:
                node_id = var.get("NodeId", "")
                value_elem = var.find("ua:Value", nsmap)
                self._address_space["variables"][node_id] = {
                    "node_id": node_id,
                    "browse_name": var.get("BrowseName", ""),
                    "display_name": var.get("DisplayName", ""),
                    "data_type": var.get("DataType", "String"),
                    "value": value_elem.text if value_elem is not None else None,
                    "node_class": "Variable",
                }

            for method in methods:
                node_id = method.get("NodeId", "")
                self._address_space["methods"][node_id] = {
                    "node_id": node_id,
                    "browse_name": method.get("BrowseName", ""),
                    "display_name": method.get("DisplayName", ""),
                    "node_class": "Method",
                }

            for ref in references:
                self._address_space["references"].append({
                    "type": ref.get("ReferenceType", ""),
                    "source": ref.get("SourceNodeId", ""),
                    "target": ref.get("TargetNodeId", ""),
                })

            for ref in self._address_space["references"]:
                parent = ref["source"]
                child = ref["target"]
                if parent in self._address_space["objects"]:
                    self._address_space["objects"][parent]["children"].append(child)

            logger.info(
                f"地址空间已加载: {len(self._address_space['objects'])}个Object, "
                f"{len(self._address_space['variables'])}个Variable, "
                f"{len(self._address_space['methods'])}个Method, "
                f"{len(self._address_space['references'])}个Reference"
            )
            return self._address_space

        except Exception as e:
            logger.error(f"解析Nodeset XML失败: {e}")
            return {}

    def build_from_kg(
        self,
        triple_store,
        device_type: str = "",
    ) -> Dict[str, Any]:
        """从知识图谱构建地址空间"""
        from .owl_to_nodeset import OWLToNodesetXML

        converter = OWLToNodesetXML(
            namespace_uri=self.namespace_uri,
            namespace_index=self.namespace_index,
        )

        nodeset_xml = converter.convert_from_kg(
            triple_store, device_type=device_type
        )

        temp_path = Path("output/temp_nodeset.xml")
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(nodeset_xml)

        address_space = self.load_nodeset_xml(str(temp_path))
        return address_space

    def query_node(self, node_id: str) -> Optional[Dict]:
        """查询地址空间中的节点"""
        for space_name in ("objects", "variables", "methods"):
            if node_id in self._address_space.get(space_name, {}):
                return self._address_space[space_name][node_id]
        return None

    def get_hierarchy(
        self, root_node_id: str
    ) -> Dict[str, Any]:
        """获取节点层次结构"""
        root = self.query_node(root_node_id)
        if root is None:
            return {}

        def build_tree(node_id: str, visited=None):
            if visited is None:
                visited = set()
            if node_id in visited:
                return None
            visited.add(node_id)

            node = self.query_node(node_id)
            if node is None:
                return None

            children = []
            if node["node_class"] == "Object":
                for child_id in node.get("children", []):
                    child_tree = build_tree(child_id, visited)
                    if child_tree:
                        children.append(child_tree)

            return {
                "node_id": node_id,
                "display_name": node.get("display_name", ""),
                "node_class": node["node_class"],
                "children": children,
            }

        return build_tree(root_node_id) or {}

    def export_address_space(self, output_path: str) -> str:
        """导出地址空间到JSON"""
        import json

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        space = {
            "namespace_uri": self.namespace_uri,
            "object_count": len(self._address_space["objects"]),
            "variable_count": len(self._address_space["variables"]),
            "method_count": len(self._address_space["methods"]),
            "reference_count": len(self._address_space["references"]),
            "objects": {
                k: v
                for k, v in self._address_space["objects"].items()
            },
            "variables": {
                k: v
                for k, v in self._address_space["variables"].items()
            },
            "methods": {
                k: v
                for k, v in self._address_space["methods"].items()
            },
            "references": self._address_space["references"],
            "hierarchy": self.get_hierarchy(
                list(self._address_space["objects"].keys())[0]
            )
            if self._address_space["objects"]
            else {},
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(space, f, ensure_ascii=False, indent=2)

        logger.info(f"地址空间已导出: {output_path}")
        return str(path)
