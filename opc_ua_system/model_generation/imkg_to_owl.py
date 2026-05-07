import logging
from pathlib import Path
from typing import Dict, List, Optional

from knowledge_graph.triple_store import Triple, TripleStore

logger = logging.getLogger(__name__)


class IMKGToOWL:
    """IMKG到OWL语义本体转换器

    OWL用于把结构图谱IMKG转换为语义本体模型，使节点类型、继承关系、
    引用语义明确化，从而为OPC UA Nodeset XML的生成提供完整的语义信息。

    没有OWL，无法正确生成合法的OPC UA信息模型。
    """

    OWL_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
         xmlns:owl="http://www.w3.org/2002/07/owl#"
         xmlns:ua="http://example.org/ua/ontology#"
         xml:base="http://example.org/ua/ontology">
    
    <owl:Ontology rdf:about="">
        <rdfs:label>OPC UA Device Ontology - {device_type}</rdfs:label>
        <rdfs:comment>Automatically generated from IMKG for {device_type} device type</rdfs:comment>
    </owl:Ontology>
    
    {declarations}
    {object_properties}
    {data_properties}
    {class_hierarchy}
    {instances}
    
</rdf:RDF>"""

    def __init__(self, namespace: str = "http://example.org/ua/ontology#"):
        self.namespace = namespace
        self._classes: Dict[str, Dict] = {}
        self._object_properties: Dict[str, Dict] = {}
        self._data_properties: Dict[str, Dict] = {}

    def convert(
        self,
        triple_store: TripleStore,
        device_type: str = "",
    ) -> str:
        """将IMKG三元组存储转换为OWL本体

        Args:
            triple_store: IMKG三元组存储
            device_type: 设备类型 (IR/CNC/SOM/SCM/PM/PW)
        Returns:
            OWL格式的XML字符串
        """
        self._classes = {}
        self._object_properties = {}
        self._data_properties = {}

        for triple in triple_store._triples:
            head_type = triple.head_type or "Object"
            tail_type = triple.tail_type or "Object"
            relation = triple.relation

            self._classes.setdefault(triple.head, {"type": head_type, "subclassOf": []})
            self._classes.setdefault(triple.tail, {"type": tail_type, "subclassOf": []})

            if relation == "subtypeOf":
                self._classes[triple.head]["subclassOf"].append(triple.tail)
            elif tail_type == "Method":
                self._object_properties.setdefault(
                    relation, {"domain": [], "range": []}
                )
                self._object_properties[relation]["domain"].append(triple.head)
                self._object_properties[relation]["range"].append(triple.tail)
            elif tail_type == "Variable":
                self._data_properties.setdefault(
                    relation, {"domain": [], "range": ["xsd:string"]}
                )
                self._data_properties[relation]["domain"].append(triple.head)
            else:
                self._object_properties.setdefault(
                    relation, {"domain": [], "range": []}
                )
                self._object_properties[relation]["domain"].append(triple.head)
                self._object_properties[relation]["range"].append(triple.tail)

        declarations = self._build_declarations()
        object_props = self._build_object_properties()
        data_props = self._build_data_properties()
        hierarchy = self._build_class_hierarchy()
        instances = self._build_instances(triple_store)

        owl_content = self.OWL_TEMPLATE.format(
            device_type=device_type or "Generic",
            declarations=declarations,
            object_properties=object_props,
            data_properties=data_props,
            class_hierarchy=hierarchy,
            instances=instances,
        )

        logger.info(
            f"OWL转换完成: {len(self._classes)}个类, "
            f"{len(self._object_properties)}个对象属性, "
            f"{len(self._data_properties)}个数据属性"
        )
        return owl_content

    def _build_declarations(self) -> str:
        """构建OWL类声明"""
        lines = []
        for cls_name in self._classes:
            lines.append(
                f'    <owl:Class rdf:about="#{cls_name}">\n'
                f'        <rdfs:label>{cls_name}</rdfs:label>\n'
                f'    </owl:Class>'
            )
        return "\n".join(lines)

    def _build_object_properties(self) -> str:
        """构建OWL对象属性"""
        lines = []
        for prop_name, info in self._object_properties.items():
            lines.append(f'    <owl:ObjectProperty rdf:about="#{prop_name}">')
            lines.append(f'        <rdfs:label>{prop_name}</rdfs:label>')
            for domain in set(info.get("domain", [])):
                lines.append(f'        <rdfs:domain rdf:resource="#{domain}"/>')
            for range_cls in set(info.get("range", [])):
                lines.append(f'        <rdfs:range rdf:resource="#{range_cls}"/>')
            lines.append(f'    </owl:ObjectProperty>')
        return "\n".join(lines)

    def _build_data_properties(self) -> str:
        """构建OWL数据属性"""
        lines = []
        for prop_name, info in self._data_properties.items():
            lines.append(f'    <owl:DatatypeProperty rdf:about="#{prop_name}">')
            lines.append(f'        <rdfs:label>{prop_name}</rdfs:label>')
            for domain in set(info.get("domain", [])):
                lines.append(f'        <rdfs:domain rdf:resource="#{domain}"/>')
            lines.append(f'        <rdfs:range rdf:resource="http://www.w3.org/2001/XMLSchema#string"/>')
            lines.append(f'    </owl:DatatypeProperty>')
        return "\n".join(lines)

    def _build_class_hierarchy(self) -> str:
        """构建类继承层次"""
        lines = []
        for cls_name, info in self._classes.items():
            for parent in info.get("subclassOf", []):
                lines.append(
                    f'    <rdfs:subClassOf rdf:resource="#{cls_name}" '
                    f'rdf:resource="#{parent}"/>'
                )
        return "\n".join(lines) if lines else "    <!-- No subclass relationships -->"

    def _build_instances(
        self, triple_store: TripleStore
    ) -> str:
        """构建实例声明"""
        lines = []
        entities = triple_store.get_all_entities()
        for entity in entities:
            entity_type = triple_store.get_entity_type(entity) or "Object"
            lines.append(
                f'    <owl:NamedIndividual rdf:about="#{entity}">\n'
                f'        <rdf:type rdf:resource="#{entity}"/>\n'
                f'    </owl:NamedIndividual>'
            )
        return "\n".join(lines)

    def save_owl(
        self,
        owl_content: str,
        output_path: str,
    ) -> str:
        """保存OWL文件"""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(owl_content)

        logger.info(f"OWL本体已保存: {output_path}")
        return str(path)
