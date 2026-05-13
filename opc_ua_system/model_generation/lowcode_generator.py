import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

TYPE_TO_PROP_TYPE = {
    "Integer": "number",
    "UInt16": "number",
    "UInt32": "number",
    "Int16": "number",
    "Int32": "number",
    "Int64": "number",
    "Double": "number",
    "Float": "number",
    "Boolean": "bool",
    "String": "string",
    "ByteString": "string",
}

TYPE_TO_SETTER = {
    "number": "NumberSetter",
    "bool": "BoolSetter",
    "string": "StringSetter",
}

TYPE_TO_LOWCODE_COMPONENT = {
    "number": "NumberPicker",
    "bool": "Switch",
    "string": "Input",
}


class LowcodeGenerator:
    """KG 语义结构 + OPC UA 帧运行时数据 → 低代码页面 Schema (统一融合版本)

    核心设计:
    - 知识图谱 (TripleStore) 提供语义骨架
        → Object 容器层级、Variable 的归属父节点、Method 是否为"操作"
        → hasComponent/hasProperty/hasOperation 等语义关系
    - OPC UA 数据帧 (frame) 提供运行时数据
        → Variable 的 data_type (UInt32/Double/String) 和实时 value
        → server_url、timestamp、frame_id 等元信息

    三种输入模式:
    | 模式 | 输入 | 语义 | 值 |
    |------|------|:--:|:--:|
    | merge  | KG + Frame  | KG | Frame |
    | kg     | 仅 KG       | KG | 无  |
    | frame  | 仅 Frame    | 推断 | Frame |

    使用示例:
        gen = LowcodeGenerator()
        schema = gen.convert(kg_store, frame, device_type="CNC")
        gen.save(schema, "output/lowcode/cnc_page.schema.json")
    """

    def __init__(self):
        self._frame_nodes: Dict[str, Dict] = {}
        self._frame_parent_map: Dict[str, str] = {}
        self._kg_property_map: Dict[str, List[Tuple[str, str]]] = {}
        self._kg_method_map: Dict[str, List[str]] = {}
        self._kg_parent_map: Dict[str, str] = {}
        self._kg_root_objects: List[str] = []

    def convert(
        self,
        kg_store: "TripleStore" = None,
        frame: Dict[str, Any] = None,
        device_type: str = "",
        device_name: str = "",
    ) -> Dict[str, Any]:
        if kg_store is not None and frame is not None:
            return self._convert_merged(kg_store, frame, device_type, device_name)
        elif kg_store is not None:
            return self._convert_kg_only(kg_store, device_type, device_name)
        elif frame is not None:
            return self._convert_frame_only(frame, device_type, device_name)
        else:
            raise ValueError("至少需要提供 kg_store 或 frame 之一")

    def _convert_merged(
        self,
        kg_store: "TripleStore",
        frame: Dict[str, Any],
        device_type: str,
        device_name: str,
    ) -> Dict[str, Any]:
        self._parse_kg(kg_store)
        self._parse_frame(frame)

        from device_identification.textcnn import DEVICE_TYPE_NAMES
        frame_name = device_name or self._find_root_name_from_frame()
        title = frame_name or DEVICE_TYPE_NAMES.get(device_type, device_type)

        component_map = self._build_merged_component_map()

        page_children = self._build_merged_children(kg_store)

        page_node = self._build_page_node(
            device_type,
            title,
            page_children,
            frame,
            source="merged",
        )

        return self._build_project_schema(
            device_type,
            component_map,
            page_node,
            title,
            frame,
            source="merged",
        )

    def _parse_kg(self, kg_store: "TripleStore") -> None:
        all_triples = kg_store._triples

        entity_type: Dict[str, str] = {}
        for t in all_triples:
            if t.head_type:
                entity_type[t.head] = t.head_type
            if t.tail_type:
                entity_type[t.tail] = t.tail_type

        for t in all_triples:
            if t.relation == "hasComponent":
                self._kg_parent_map[t.tail] = t.head
            elif t.relation == "hasProperty":
                self._kg_property_map.setdefault(t.head, []).append(
                    (t.tail, entity_type.get(t.tail, "Variable"))
                )
            elif t.relation == "hasOperation":
                self._kg_method_map.setdefault(t.head, []).append(t.tail)

        all_entities = kg_store.get_all_entities()
        for e in all_entities:
            if e not in self._kg_parent_map and entity_type.get(e) == "Object":
                self._kg_root_objects.append(e)

    def _parse_frame(self, frame: Dict[str, Any]) -> None:
        nodes = frame.get("nodes", {})
        self._frame_nodes = nodes
        for node_id, node in nodes.items():
            parent = node.get("parent_node_id")
            if parent:
                self._frame_parent_map[node_id] = parent

    def _build_merged_children(
        self, kg_store: "TripleStore"
    ) -> List[Dict[str, Any]]:
        children = []
        for root in self._kg_root_objects:
            children.append(self._build_node_merged(root, kg_store))
        return children

    def _build_node_merged(
        self, entity: str, kg_store: "TripleStore", node_id_prefix: str = ""
    ) -> Dict[str, Any]:
        if not node_id_prefix:
            node_id_prefix = f"node_{entity}"

        children = []

        all_triples = kg_store._triples
        child_objects = [
            t.tail for t in all_triples
            if t.head == entity and t.relation == "hasComponent"
        ]
        for child in child_objects:
            children.append(
                self._build_node_merged(child, kg_store, f"{node_id_prefix}_{child}")
            )

        props = self._kg_property_map.get(entity, [])
        for prop_name, _prop_type in props:
            frame_info = self._find_in_frame(prop_name)
            children.append(
                self._build_variable_node(
                    prop_name, frame_info, f"{node_id_prefix}_prop_{prop_name}"
                )
            )

        methods = self._kg_method_map.get(entity, [])
        for method_name in methods:
            children.append(
                self._build_method_node(
                    method_name, f"{node_id_prefix}_method_{method_name}"
                )
            )

        if child_objects or props or methods:
            return {
                "componentName": "Card",
                "id": node_id_prefix,
                "props": {"title": entity, "showHeadDivider": True},
                "hidden": False,
                "condition": True,
                "children": children,
            }

        return {
            "componentName": "Typography",
            "id": node_id_prefix,
            "props": {"children": entity},
        }

    def _find_in_frame(self, name: str) -> Optional[Dict[str, Any]]:
        for node_id, node in self._frame_nodes.items():
            dn = node.get("display_name", "")
            bn = node.get("browse_name", "")
            if dn == name or bn == name:
                return node
        for node_id, node in self._frame_nodes.items():
            dn = node.get("display_name", "")
            bn = node.get("browse_name", "")
            if name.lower() in dn.lower() or name.lower() in bn.lower():
                return node
        return None

    def _build_variable_node(
        self,
        name: str,
        frame_info: Optional[Dict[str, Any]],
        node_id: str,
    ) -> Dict[str, Any]:
        if frame_info:
            data_type = frame_info.get("data_type", "String")
            raw_value = frame_info.get("value")
        else:
            data_type = "String"
            raw_value = None

        prop_type = TYPE_TO_PROP_TYPE.get(data_type, "string")
        component = TYPE_TO_LOWCODE_COMPONENT.get(prop_type, "Input")
        extra: Dict[str, Any] = {}

        if raw_value is not None:
            if prop_type == "bool":
                extra["checked"] = str(raw_value).lower() in ("true", "1", "yes")
            elif prop_type == "number":
                try:
                    raw_str = str(raw_value)
                    extra["value"] = float(raw_str) if "." in raw_str else int(raw_str)
                except (ValueError, TypeError):
                    pass
            else:
                extra["value"] = str(raw_value)

        node = {
            "componentName": component,
            "id": node_id,
            "props": {
                "label": name,
                "disabled": True,
                **extra,
            },
        }
        if frame_info:
            node["props"]["_opcua_data_type"] = data_type
            node["props"]["_opcua_node_id"] = frame_info.get("node_id", "")
        return node

    def _build_method_node(self, name: str, node_id: str) -> Dict[str, Any]:
        return {
            "componentName": "Button",
            "id": node_id,
            "props": {
                "type": "primary",
                "children": name,
                "onClick": {
                    "type": "JSExpression",
                    "value": f"this.methods.{name}",
                },
            },
        }

    def _build_page_node(
        self,
        device_type: str,
        title: str,
        children: List[Dict],
        frame: Optional[Dict[str, Any]],
        source: str,
    ) -> Dict[str, Any]:
        page_id = device_type or "page"
        data_source_list = []
        if frame:
            data_source_list.append({
                "id": "deviceData",
                "isInit": True,
                "type": "fetch",
                "options": {
                    "uri": f"/api/opcua/{device_type}/data",
                    "method": "GET",
                    "params": {},
                    "isCors": True,
                    "timeout": 5000,
                    "headers": {},
                },
            })

        methods: Dict[str, Any] = {}
        if self._kg_method_map:
            for _head, method_names in self._kg_method_map.items():
                for mn in method_names:
                    methods[mn] = {
                        "type": "JSFunction",
                        "value": (
                            f"function {mn}(params) {{\n"
                            f"  console.log('执行操作: {mn}');\n"
                            f"}}"
                        ),
                    }

        return {
            "componentName": "Page",
            "id": f"page_{page_id}",
            "fileName": title.replace(" ", "_"),
            "props": {"title": title, "ref": "page"},
            "css": "body { font-family: sans-serif; } .device-card { margin: 8px 0; }",
            "state": {},
            "dataSource": {"list": data_source_list},
            "lifeCycles": {
                "componentDidMount": {
                    "type": "JSFunction",
                    "value": (
                        "function componentDidMount() {\n"
                        f"  console.log('{title} 监控页面已加载');\n"
                        "}"
                    ),
                },
            },
            "methods": methods,
            "children": children,
        }

    def _build_project_schema(
        self,
        device_type: str,
        component_map: List[Dict],
        page_node: Dict,
        title: str,
        frame: Optional[Dict[str, Any]],
        source: str,
    ) -> Dict[str, Any]:
        constants: Dict[str, Any] = {"DEVICE_TYPE": device_type}
        if frame:
            constants["SERVER_URL"] = frame.get("server_url", "")
            constants["FRAME_ID"] = frame.get("frame_id", 1)

        desc_parts = [f"{title} 低代码页面"]
        if source == "merged":
            desc_parts.append("由 KG 语义骨架 + OPC UA 帧运行时数据融合生成")
        elif source == "kg":
            desc_parts.append("由 IMKG 知识图谱生成")
        else:
            desc_parts.append("由 OPC UA 数据帧生成")

        meta = {
            "name": f"{title} 监控页面",
            "description": "".join(desc_parts),
            "creator": "lowcode_generator",
            "source": source,
            "gmt_create": datetime.now().isoformat(),
        }
        if frame:
            meta["source_frame_id"] = frame.get("frame_id")
            meta["server_url"] = frame.get("server_url", "")

        return {
            "version": "1.0.0",
            "componentsMap": component_map,
            "componentsTree": [page_node],
            "utils": [],
            "constants": constants,
            "css": (
                "body { font-size: 14px; margin: 0; padding: 16px; }\n"
                ".device-card { margin-bottom: 12px; }\n"
                ".var-item { display: flex; align-items: center; gap: 8px; padding: 4px 0; }\n"
                ".var-label { font-weight: 500; min-width: 120px; }"
            ),
            "config": {
                "sdkVersion": "1.0.18",
                "historyMode": "hash",
                "targetRootID": "root",
                "theme": {"primary": "#1890ff"},
            },
            "meta": meta,
            "i18n": {},
            "router": {
                "baseUrl": "/",
                "routes": [
                    {"path": device_type.lower(), "page": f"page_{device_type or 'page'}"}
                ],
            },
            "dataSource": {"list": []},
            "pages": [
                {"id": f"page_{device_type or 'page'}", "treeId": f"page_{device_type or 'page'}"}
            ],
        }

    def _convert_kg_only(
        self,
        kg_store: "TripleStore",
        device_type: str,
        device_name: str,
    ) -> Dict[str, Any]:
        self._parse_kg(kg_store)

        from device_identification.textcnn import DEVICE_TYPE_NAMES
        title = device_name or DEVICE_TYPE_NAMES.get(device_type, device_type)

        component_map = self._build_merged_component_map()

        all_triples = kg_store._triples

        def build_node(entity: str, prefix: str) -> Dict[str, Any]:
            children = []
            child_objects = [
                t.tail for t in all_triples
                if t.head == entity and t.relation == "hasComponent"
            ]
            for child in child_objects:
                children.append(build_node(child, f"{prefix}_{child}"))

            for prop_name, _ in self._kg_property_map.get(entity, []):
                children.append(
                    self._build_variable_node(prop_name, None, f"{prefix}_prop_{prop_name}")
                )

            for method_name in self._kg_method_map.get(entity, []):
                children.append(
                    self._build_method_node(method_name, f"{prefix}_method_{method_name}")
                )

            if child_objects or children:
                return {
                    "componentName": "Card",
                    "id": prefix,
                    "props": {"title": entity},
                    "children": children,
                }
            return {"componentName": "Typography", "id": prefix, "props": {"children": entity}}

        page_children = [
            build_node(root, f"node_{root}") for root in self._kg_root_objects
        ]

        page_node = self._build_page_node(device_type, title, page_children, None, "kg")
        return self._build_project_schema(device_type, component_map, page_node, title, None, "kg")

    def _convert_frame_only(
        self,
        frame: Dict[str, Any],
        device_type: str,
        device_name: str,
    ) -> Dict[str, Any]:
        self._parse_frame(frame)

        nodes = self._frame_nodes
        metadata = frame.get("device_metadata", [])
        if not device_type:
            device_type = self._infer_device_type(metadata)
        if not device_name:
            device_name = self._find_root_name_from_frame()

        from device_identification.textcnn import DEVICE_TYPE_NAMES
        title = device_name or DEVICE_TYPE_NAMES.get(device_type, device_type)

        root_ids = [
            nid for nid, n in nodes.items()
            if n.get("parent_node_id") is None
        ]

        def convert_node(node_id: str) -> Optional[Dict[str, Any]]:
            node = nodes.get(node_id)
            if node is None:
                return None

            nc = node.get("node_class", "")
            dn = node.get("display_name", node.get("browse_name", ""))
            safe_id = node_id.replace("=", "_").replace(";", "_")

            if nc == "Object":
                child_nodes = []
                for cid in node.get("children", []):
                    c = convert_node(cid)
                    if c:
                        child_nodes.append(c)
                return {
                    "componentName": "Card",
                    "id": f"node_obj_{safe_id}",
                    "props": {"title": dn, "showHeadDivider": True},
                    "children": child_nodes,
                }
            elif nc == "Variable":
                return self._build_variable_node(dn, node, f"node_var_{safe_id}")
            elif nc == "Method":
                return self._build_method_node(dn, f"node_method_{safe_id}")
            elif nc == "ObjectType":
                return None
            return {"componentName": "Typography", "id": f"node_{safe_id}", "props": {"children": dn}}

        children = []
        for rid in root_ids:
            child = convert_node(rid)
            if child:
                children.append(child)

        component_map = self._build_frame_component_map()

        page_node = self._build_page_node(device_type, title, children, frame, "frame")
        return self._build_project_schema(device_type, component_map, page_node, title, frame, "frame")

    def _find_root_name_from_frame(self) -> str:
        for nid, node in self._frame_nodes.items():
            if node.get("parent_node_id") is None:
                return node.get("display_name", node.get("browse_name", "Device"))
        for nid, node in self._frame_nodes.items():
            return node.get("display_name", node.get("browse_name", "Device"))
        return "Device"

    def _infer_device_type(self, metadata: List[Dict]) -> str:
        if not metadata:
            return "CNC"
        field_names = [m.get("field_name", "") for m in metadata]
        type_keywords = {
            "CNC": ["Spindle", "CNC", "Tool", "Worktable"],
            "IR": ["Robot", "EndEffector", "Drive", "Axis"],
            "SOM": ["Sorting", "Feeder", "Conveyor", "Vision"],
            "SCM": ["Scribing", "Laser", "ScribingHead"],
            "PM": ["Pick", "Placement", "Nozzle", "FeederBank"],
            "PW": ["Weld", "Press", "Electrode", "Cooling"],
        }
        best_type = "CNC"
        best_score = 0
        for dtype, keywords in type_keywords.items():
            score = sum(1 for f in field_names for kw in keywords if kw.lower() in f.lower())
            if score > best_score:
                best_score = score
                best_type = dtype
        return best_type

    def _build_merged_component_map(self) -> List[Dict[str, Any]]:
        return [
            {"componentName": "Page", "package": "@alilc/lowcode-materials", "version": "1.0.0", "destructuring": True},
            {"componentName": "Card", "package": "@alifd/next", "version": "1.23.0", "destructuring": True},
            {"componentName": "NumberPicker", "package": "@alifd/next", "version": "1.23.0", "destructuring": True},
            {"componentName": "Input", "package": "@alifd/next", "version": "1.23.0", "destructuring": True},
            {"componentName": "Switch", "package": "@alifd/next", "version": "1.23.0", "destructuring": True},
            {"componentName": "Button", "package": "@alifd/next", "version": "1.23.0", "destructuring": True},
            {"componentName": "Typography", "package": "@alifd/next", "version": "1.23.0", "destructuring": True},
        ]

    def _build_frame_component_map(self) -> List[Dict[str, Any]]:
        used = set()
        for node in self._frame_nodes.values():
            nc = node.get("node_class", "")
            if nc == "Variable":
                dt = node.get("data_type", "String")
                pt = TYPE_TO_PROP_TYPE.get(dt, "string")
                used.add(TYPE_TO_LOWCODE_COMPONENT.get(pt, "Input"))
            elif nc == "Method":
                used.add("Button")
            elif nc == "Object":
                used.add("Card")
        cm = [
            {"componentName": "Page", "package": "@alilc/lowcode-materials", "version": "1.0.0", "destructuring": True},
        ]
        for comp in ["Card", "NumberPicker", "Input", "Switch", "Button", "Typography"]:
            if comp in used or comp == "Typography":
                cm.append(
                    {"componentName": comp, "package": "@alifd/next", "version": "1.23.0", "destructuring": True}
                )
        return cm

    def save(self, schema: Dict[str, Any], output_path: str) -> str:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)
        logger.info(f"项目 Schema 已保存: {output_path}")
        return str(path)


class KGToLowcodeGenerator:
    """IMKG 知识图谱 → 低代码组件物料描述 (ComponentDescription) 转换器

    单独生成组件的物料描述 JSON，用于注册到低代码平台的组件面板。
    此转换器不依赖 OPC UA 帧数据，仅基于 KG 语义结构。

    使用示例:
        converter = KGToLowcodeGenerator()
        component_desc = converter.convert(kg_store, "CNC")
        converter.save(component_desc, "output/lowcode/CNC.material.json")
    """

    def __init__(self):
        self._entity_properties: Dict[str, List[str]] = {}
        self._entity_methods: Dict[str, List[str]] = {}
        self._entity_children: Dict[str, List[str]] = {}
        self._entity_parents: Dict[str, List[str]] = {}

    def convert(
        self,
        kg_store: "TripleStore",
        device_type: str = "",
        component_name: str = "",
        component_title: str = "",
    ) -> Dict[str, Any]:
        all_triples = kg_store._triples
        entities = kg_store.get_all_entities()

        for t in all_triples:
            if t.relation == "hasProperty":
                self._entity_properties.setdefault(t.head, []).append(t.tail)
            elif t.relation == "hasOperation":
                self._entity_methods.setdefault(t.head, []).append(t.tail)
            elif t.relation == "hasComponent":
                self._entity_children.setdefault(t.head, []).append(t.tail)
                self._entity_parents.setdefault(t.tail, []).append(t.head)

        if not component_name:
            component_name = device_type
        if not component_title:
            from device_identification.textcnn import DEVICE_TYPE_NAMES
            component_title = DEVICE_TYPE_NAMES.get(device_type, device_type)

        props = self._build_props()
        events = self._build_events()
        snippets = self._build_snippets(kg_store, component_name)

        return {
            "componentName": component_name,
            "title": component_title,
            "category": "工业设备",
            "group": "精选组件",
            "description": f"{component_title} 低代码物料组件 - 由 IMKG 自动生成",
            "devMode": "proCode",
            "npm": {
                "package": f"@factory/{component_name.lower()}",
                "version": "1.0.0",
                "exportName": component_name,
                "destructuring": False,
            },
            "props": props,
            "snippets": snippets,
            "configure": {
                "component": {
                    "isContainer": len(self._entity_children) > 0,
                    "nestingRule": {
                        "childWhitelist": sorted(entities),
                    },
                },
                "supports": {
                    "style": True,
                    "className": True,
                    "events": events,
                    "loop": False,
                    "condition": True,
                },
            },
        }

    def _build_props(self) -> List[Dict[str, Any]]:
        props = []
        for head, prop_names in self._entity_properties.items():
            items = []
            for name in prop_names:
                items.append({
                    "name": name,
                    "title": {"label": name, "tip": f"{head}.{name}"},
                    "propType": "number",
                    "setter": "NumberSetter",
                    "defaultValue": 0,
                    "supportVariable": True,
                })
            for name in self._entity_methods.get(head, []):
                items.append({
                    "name": name,
                    "title": {"label": name, "tip": f"{head}.{name} 操作"},
                    "propType": "bool",
                    "setter": "BoolSetter",
                    "defaultValue": False,
                })
            if items:
                props.append({
                    "title": f"{head} 属性",
                    "display": "block",
                    "type": "group",
                    "items": items,
                })
        return props

    def _build_events(self) -> List[Dict[str, str]]:
        seen = set()
        events = []
        for _head, names in self._entity_methods.items():
            for nm in names:
                if nm not in seen:
                    seen.add(nm)
                    events.append({
                        "name": f"on{nm}",
                        "template": (
                            f"on{nm}(event, params){{\n"
                            f"  console.log('{nm}');\n"
                            f"}}"
                        ),
                        "description": f"{nm} 操作事件",
                    })
        return events

    def _build_snippets(
        self, kg_store: "TripleStore", component_name: str
    ) -> List[Dict[str, Any]]:
        props: Dict[str, Any] = {}
        for _head, names in self._entity_properties.items():
            for nm in names:
                props[nm] = 0
        for _head, names in self._entity_methods.items():
            for nm in names:
                props[nm] = False
        return [{
            "title": f"{component_name} (默认)",
            "schema": {"componentName": component_name, "props": props},
        }]

    def save(self, material: Dict[str, Any], output_path: str) -> str:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(material, f, ensure_ascii=False, indent=2)
        logger.info(f"组件物料描述已保存: {output_path}")
        return str(path)


def generate_lowcode_schema(
    kg_store: "TripleStore" = None,
    frame: Dict[str, Any] = None,
    device_type: str = "",
    device_name: str = "",
    output_path: str = None,
) -> Dict[str, Any]:
    gen = LowcodeGenerator()
    schema = gen.convert(kg_store, frame, device_type, device_name)
    if output_path:
        gen.save(schema, str(output_path))
    return schema


def generate_assets_bundle(
    materials: List[Dict[str, Any]],
    device_types: List[str],
    output_path: str = "output/lowcode/assets.json",
) -> str:
    packages = [
        {
            "title": "Fusion 组件库",
            "package": "@alifd/next",
            "version": "1.23.18",
            "urls": [
                "https://g.alicdn.com/code/lib/alifd__next/1.23.18/next.min.css",
                "https://g.alicdn.com/code/lib/alifd__next/1.23.18/next-with-locales.min.js",
            ],
            "library": "Next",
        },
        {
            "title": "工业设备组件库",
            "package": "@factory/equipment-ui",
            "version": "1.0.0",
            "urls": [
                "https://cdn.example.com/factory-equipment/1.0.0/main.js",
                "https://cdn.example.com/factory-equipment/1.0.0/main.css",
            ],
            "library": "FactoryEquipment",
        },
    ]

    assets = {
        "version": "1.1.0",
        "packages": packages,
        "components": materials,
        "sort": {
            "groupList": ["精选组件", "原子组件"],
            "categoryList": ["通用", "数据展示", "表单", "工业设备"],
        },
        "plugins": [],
        "setters": [],
        "extConfig": {
            "deviceTypes": device_types,
            "generatedBy": "lowcode_generator",
            "generatedAt": datetime.now().isoformat(),
        },
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(assets, f, ensure_ascii=False, indent=2)
    logger.info(f"资产包已保存: {output_path}")
    return str(path)
