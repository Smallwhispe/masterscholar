import logging
from pathlib import Path
from typing import Dict, List, Optional
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from knowledge_graph.triple_store import Triple, TripleStore

logger = logging.getLogger(__name__)


class OWLToNodesetXML:
    """OWL语义本体到OPC UA Nodeset XML转换器

    根据OWL中定义的节点类型、继承关系、引用语义，生成合法的OPC UA信息模型。
    """

    NODESET_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<UANodeSet xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
           xmlns:xsd="http://www.w3.org/2001/XMLSchema"
           xmlns="http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"
           LastModified="{last_modified}">
    <NamespaceUris>
        <Uri>{namespace_uri}</Uri>
    </NamespaceUris>
    <Models>
        <Model ModelUri="{namespace_uri}" PublicationDate="{pub_date}" Version="1.0">
            <RequiredModel ModelUri="http://opcfoundation.org/UA/" Version="1.04" />
        </Model>
    </Models>
    {nodes}
</UANodeSet>"""

    def __init__(
        self,
        namespace_uri: str = "http://example.org/UA/",
        namespace_index: int = 2,
    ):
        self.namespace_uri = namespace_uri
        self.namespace_index = namespace_index

    def convert_from_kg(
        self,
        triple_store: TripleStore,
        device_type: str = "",
        device_name: str = "",
    ) -> str:
        """从知识图谱三元组生成Nodeset XML

        规则:
        - Object → UAObject节点
        - Variable → UAVariable节点
        - Method → UAMethod节点
        - hasComponent/connectedTo → Organizes引用
        - hasProperty → HasProperty引用
        - hasOperation → HasComponent引用
        """
        from datetime import datetime
        import xml.etree.ElementTree as ET

        root = ET.Element(
            "UANodeSet",
            {
                "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
                "xmlns": "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd",
                "LastModified": datetime.now().isoformat(),
            },
        )

        namespace_uris = ET.SubElement(root, "NamespaceUris")
        ET.SubElement(namespace_uris, "Uri").text = self.namespace_uri

        models = ET.SubElement(root, "Models")
        model = ET.SubElement(
            models,
            "Model",
            {
                "ModelUri": self.namespace_uri,
                "PublicationDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "Version": "1.0",
            },
        )
        ET.SubElement(
            model,
            "RequiredModel",
            {
                "ModelUri": "http://opcfoundation.org/UA/",
                "Version": "1.04",
            },
        )

        node_counter = [5000]
        node_id_map: Dict[str, str] = {}

        entities = triple_store.get_all_entities()
        for entity in entities:
            entity_type = triple_store.get_entity_type(entity) or "Object"
            node_id = f"ns={self.namespace_index};i={node_counter[0]}"
            node_counter[0] += 1
            node_id_map[entity] = node_id

            if entity_type == "Variable":
                node = ET.SubElement(
                    root,
                    "UAVariable",
                    {
                        "NodeId": node_id,
                        "BrowseName": f"{self.namespace_index}:{entity}",
                        "DisplayName": entity,
                        "DataType": "String",
                        "ParentNodeId": self._find_parent(
                            entity, triple_store, node_id_map
                        ),
                    },
                )
            elif entity_type == "Method":
                node = ET.SubElement(
                    root,
                    "UAMethod",
                    {
                        "NodeId": node_id,
                        "BrowseName": f"{self.namespace_index}:{entity}",
                        "DisplayName": entity,
                        "ParentNodeId": self._find_parent(
                            entity, triple_store, node_id_map
                        ),
                    },
                )
            else:
                node = ET.SubElement(
                    root,
                    "UAObject",
                    {
                        "NodeId": node_id,
                        "BrowseName": f"{self.namespace_index}:{entity}",
                        "DisplayName": entity,
                        "EventNotifier": "SubscribeToEvents",
                    },
                )

        for triple in triple_store._triples:
            if triple.relation in ("hasComponent", "connectedTo", "controlledBy"):
                head_id = node_id_map.get(triple.head)
                tail_id = node_id_map.get(triple.tail)
                if head_id and tail_id:
                    ref = ET.SubElement(
                        root,
                        "UAReference",
                        {
                            "ReferenceType": "Organizes",
                            "SourceNodeId": head_id,
                            "TargetNodeId": tail_id,
                        },
                    )
            elif triple.relation == "hasProperty":
                head_id = node_id_map.get(triple.head)
                tail_id = node_id_map.get(triple.tail)
                if head_id and tail_id:
                    ref = ET.SubElement(
                        root,
                        "UAReference",
                        {
                            "ReferenceType": "HasProperty",
                            "SourceNodeId": head_id,
                            "TargetNodeId": tail_id,
                        },
                    )
            elif triple.relation == "hasOperation":
                head_id = node_id_map.get(triple.head)
                tail_id = node_id_map.get(triple.tail)
                if head_id and tail_id:
                    ref = ET.SubElement(
                        root,
                        "UAReference",
                        {
                            "ReferenceType": "HasComponent",
                            "SourceNodeId": head_id,
                            "TargetNodeId": tail_id,
                        },
                    )
            elif triple.relation == "subtypeOf":
                head_id = node_id_map.get(triple.head)
                tail_id = node_id_map.get(triple.tail)
                if head_id and tail_id:
                    ref = ET.SubElement(
                        root,
                        "UAReference",
                        {
                            "ReferenceType": "HasSubtype",
                            "SourceNodeId": tail_id,
                            "TargetNodeId": head_id,
                        },
                    )

        raw_xml = ET.tostring(root, encoding="unicode")
        try:
            dom = minidom.parseString(raw_xml)
            pretty_xml = dom.toprettyxml(indent="  ")
        except Exception:
            pretty_xml = raw_xml

        logger.info(
            f"Nodeset XML生成完成: {triple_store.entity_count}个节点, "
            f"{triple_store.triple_count}个三元组"
        )
        return pretty_xml

    def _find_parent(
        self,
        entity: str,
        triple_store: TripleStore,
        node_id_map: Dict[str, str],
    ) -> str:
        """找实体的父节点ID"""
        for triple in triple_store._triples:
            if triple.tail == entity:
                return node_id_map.get(triple.head, "")
        return ""

    def save(
        self,
        nodeset_xml: str,
        output_path: str,
    ) -> str:
        """保存Nodeset XML文件"""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(nodeset_xml)

        logger.info(f"Nodeset XML已保存: {output_path}")
        return str(path)
