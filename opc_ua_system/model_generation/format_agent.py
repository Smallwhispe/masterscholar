import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FormatTransformationAgent:
    """格式转换Agent (FTA)

    将SA (Structured Annotation) 或 IEA (Information Extraction Annotation)
    的JSON结构转换为OPC UA Nodeset XML。

    处理流程:
    1. 文本层次化标注 - 对非结构化工业文本标注设备名、特征、属性值三级标签
    2. 结构化节点生成 - 设备→Object, 属性→Variable, 操作→Method, 保持父子关系
    3. 规范数据格式 - 转换为符合OPC UA节点规范的数据格式
    """

    def __init__(
        self,
        namespace_uri: str = "http://example.org/UA/",
        namespace_index: int = 2,
    ):
        self.namespace_uri = namespace_uri
        self.namespace_index = namespace_index

    def convert_from_sa(
        self,
        sa_json: Dict[str, Any],
        device_type: str = "",
        device_name: str = "",
    ) -> Dict[str, Any]:
        """从SA(结构化标注) JSON转换为UA节点结构

        SA JSON 格式:
        {
            "device_name": "CNC Machine",
            "objects": [
                {"name": "Spindle", "variables": [...], "methods": [...]},
            ],
            "variables": [
                {"name": "SpindleSpeed", "value": "1000", "data_type": "Double"},
            ],
            "methods": [
                {"name": "StartSpindle", "params": [...]},
            ],
            "hierarchy": {...}
        }
        """
        node_id_counter = [5000]
        nodes: Dict[str, Dict] = {}
        references: List[Dict] = []

        device_node_id = f"ns={self.namespace_index};i={node_id_counter[0]}"
        node_id_counter[0] += 1
        nodes[device_node_id] = {
            "node_class": "Object",
            "display_name": device_name or sa_json.get("device_name", "Device"),
            "browse_name": device_name or "Device",
        }

        for obj in sa_json.get("objects", []):
            obj_id = f"ns={self.namespace_index};i={node_id_counter[0]}"
            node_id_counter[0] += 1
            obj_name = obj.get("name", "UnknownObject")
            nodes[obj_id] = {
                "node_class": "Object",
                "display_name": obj_name,
                "browse_name": obj_name,
                "parent_node_id": device_node_id,
            }
            references.append({
                "type": "Organizes",
                "source": device_node_id,
                "target": obj_id,
            })

            for var in obj.get("variables", []):
                var_id = f"ns={self.namespace_index};i={node_id_counter[0]}"
                node_id_counter[0] += 1
                var_name = var.get("name", "UnknownVar")
                nodes[var_id] = {
                    "node_class": "Variable",
                    "display_name": var_name,
                    "browse_name": var_name,
                    "value": var.get("value"),
                    "data_type": var.get("data_type", "String"),
                    "parent_node_id": obj_id,
                }
                references.append({
                    "type": "HasProperty",
                    "source": obj_id,
                    "target": var_id,
                })

            for method in obj.get("methods", []):
                method_id = f"ns={self.namespace_index};i={node_id_counter[0]}"
                node_id_counter[0] += 1
                method_name = method.get("name", "UnknownMethod")
                nodes[method_id] = {
                    "node_class": "Method",
                    "display_name": method_name,
                    "browse_name": method_name,
                    "parent_node_id": obj_id,
                    "parameters": method.get("params", []),
                }
                references.append({
                    "type": "HasComponent",
                    "source": obj_id,
                    "target": method_id,
                })

        for var in sa_json.get("variables", []):
            var_id = f"ns={self.namespace_index};i={node_id_counter[0]}"
            node_id_counter[0] += 1
            var_name = var.get("name", "UnknownVar")
            nodes[var_id] = {
                "node_class": "Variable",
                "display_name": var_name,
                "browse_name": var_name,
                "value": var.get("value"),
                "data_type": var.get("data_type", "String"),
                "parent_node_id": device_node_id,
            }
            references.append({
                "type": "HasProperty",
                "source": device_node_id,
                "target": var_id,
            })

        for method in sa_json.get("methods", []):
            method_id = f"ns={self.namespace_index};i={node_id_counter[0]}"
            node_id_counter[0] += 1
            method_name = method.get("name", "UnknownMethod")
            nodes[method_id] = {
                "node_class": "Method",
                "display_name": method_name,
                "browse_name": method_name,
                "parent_node_id": device_node_id,
            }
            references.append({
                "type": "HasComponent",
                "source": device_node_id,
                "target": method_id,
            })

        return {
            "namespace_uri": self.namespace_uri,
            "device_type": device_type,
            "device_name": device_name or sa_json.get("device_name", ""),
            "nodes": nodes,
            "references": references,
            "node_count": len(nodes),
        }

    def convert_from_iea(
        self,
        iea_json: Dict[str, Any],
        device_type: str = "",
    ) -> Dict[str, Any]:
        """从IEA(信息提取标注) JSON转换为UA节点结构

        IEA JSON 格式:
        {
            "text": "...",
            "annotations": [
                {"entity": "Spindle", "type": "DeviceName", "relations": [...], "attributes": [...]},
            ],
            "hierarchy": {...}
        }
        """
        sa_json = {
            "device_name": "",
            "objects": [],
            "variables": [],
            "methods": [],
        }

        for ann in iea_json.get("annotations", []):
            entity = ann.get("entity", "")
            ann_type = ann.get("type", "")

            if ann_type == "DeviceName":
                sa_json["device_name"] = entity
                sa_json["objects"].append({
                    "name": entity,
                    "variables": [
                        {"name": attr.get("name", ""), "value": attr.get("value", "")}
                        for attr in ann.get("attributes", [])
                    ],
                    "methods": [
                        {"name": op.get("name", "")}
                        for op in ann.get("operations", [])
                    ],
                })

            elif ann_type == "Feature":
                sa_json["objects"].append({
                    "name": entity,
                    "variables": [
                        {"name": attr.get("name", ""), "value": attr.get("value", "")}
                        for attr in ann.get("attributes", [])
                    ],
                })

            elif ann_type == "Attribute":
                sa_json["variables"].append({
                    "name": entity,
                    "value": ann.get("value"),
                    "data_type": ann.get("data_type", "String"),
                })

            elif ann_type == "Operation":
                sa_json["methods"].append({
                    "name": entity,
                    "params": ann.get("parameters", []),
                })

        hierarchy = iea_json.get("hierarchy", {})
        if hierarchy:
            sa_json["hierarchy"] = hierarchy

        return self.convert_from_sa(
            sa_json, device_type=device_type
        )

    def to_nodeset_xml(
        self, ua_structure: Dict[str, Any]
    ) -> str:
        """将UA节点结构转换为Nodeset XML字符串"""
        from xml.etree.ElementTree import Element, SubElement, tostring
        from xml.dom import minidom
        from datetime import datetime

        root = Element(
            "UANodeSet",
            {
                "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
                "xmlns": "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd",
                "LastModified": datetime.now().isoformat(),
            },
        )

        namespace_uris = SubElement(root, "NamespaceUris")
        SubElement(namespace_uris, "Uri").text = self.namespace_uri

        models = SubElement(root, "Models")
        model = SubElement(
            models,
            "Model",
            {
                "ModelUri": self.namespace_uri,
                "PublicationDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "Version": "1.0",
            },
        )
        SubElement(
            model,
            "RequiredModel",
            {
                "ModelUri": "http://opcfoundation.org/UA/",
                "Version": "1.04",
            },
        )

        nodes = ua_structure.get("nodes", {})
        for node_id, node_info in nodes.items():
            node_class = node_info.get("node_class", "Object")
            if node_class == "Variable":
                node_elem = SubElement(
                    root,
                    "UAVariable",
                    {
                        "NodeId": node_id,
                        "BrowseName": f"{self.namespace_index}:{node_info.get('browse_name', '')}",
                        "DisplayName": node_info.get("display_name", ""),
                        "DataType": node_info.get("data_type", "String"),
                        "ParentNodeId": node_info.get("parent_node_id", ""),
                    },
                )
                if node_info.get("value") is not None:
                    SubElement(node_elem, "Value").text = str(node_info["value"])
            elif node_class == "Method":
                SubElement(
                    root,
                    "UAMethod",
                    {
                        "NodeId": node_id,
                        "BrowseName": f"{self.namespace_index}:{node_info.get('browse_name', '')}",
                        "DisplayName": node_info.get("display_name", ""),
                        "ParentNodeId": node_info.get("parent_node_id", ""),
                    },
                )
            else:
                SubElement(
                    root,
                    "UAObject",
                    {
                        "NodeId": node_id,
                        "BrowseName": f"{self.namespace_index}:{node_info.get('browse_name', '')}",
                        "DisplayName": node_info.get("display_name", ""),
                        "EventNotifier": "SubscribeToEvents",
                    },
                )

        for ref in ua_structure.get("references", []):
            SubElement(
                root,
                "UAReference",
                {
                    "ReferenceType": ref.get("type", "Organizes"),
                    "SourceNodeId": ref.get("source", ""),
                    "TargetNodeId": ref.get("target", ""),
                },
            )

        raw_xml = tostring(root, encoding="unicode")
        try:
            return minidom.parseString(raw_xml).toprettyxml(indent="  ")
        except Exception:
            return raw_xml

    def save(
        self,
        ua_structure: Dict[str, Any],
        output_dir: str = "output/nodeset/",
    ) -> Dict[str, str]:
        """保存UA结构和Nodeset XML"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        device_name = ua_structure.get("device_name", "Device")
        safe_name = device_name.replace(" ", "_").lower()

        json_path = output_path / f"{safe_name}_structure.json"
        xml_path = output_path / f"{safe_name}_nodeset.xml"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(ua_structure, f, ensure_ascii=False, indent=2)

        nodeset_xml = self.to_nodeset_xml(ua_structure)
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(nodeset_xml)

        logger.info(f"UA结构已保存: {json_path}")
        logger.info(f"Nodeset XML已保存: {xml_path}")

        return {"json_path": str(json_path), "xml_path": str(xml_path)}
