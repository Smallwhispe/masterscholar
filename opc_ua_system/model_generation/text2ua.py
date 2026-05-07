import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import torch
except ImportError:
    torch = None


class Text2UA:
    """Text2UA模块 - 将非结构化工业文本转换为UA节点结构

    用于对非结构化工业文本进行层次化标注，包括:
    - 关键设备名 (DeviceName)
    - 设备特征 (Feature)
    - 属性值 (Attribute) 三级标签

    输出可用于FormatTransformationAgent进行后续处理。
    """

    def __init__(self):
        self.device_patterns = [
            re.compile(r"(\b[A-Z]{2,5}\b.*?Machine)", re.IGNORECASE),
            re.compile(r"(\b[A-Z]{2,5}\b.*?Robot)", re.IGNORECASE),
            re.compile(r"(\b[A-Z]{2,5}\b.*?System)", re.IGNORECASE),
        ]

        self.property_pattern = re.compile(
            r"(\w+)\s*[=:：]\s*(\d+\.?\d*)\s*(℃|mm|rpm|kW|Hz|MPa|bar|V|A)?"
        )

        self.operation_patterns = [
            re.compile(r"(start|stop|reset|change|load|move|weld|cut|sort)\s*\w*", re.IGNORECASE),
            re.compile(r"\b(Start|Stop|Reset)\w*\b"),
        ]

    def parse_text(self, text: str) -> Dict[str, Any]:
        """解析非结构化工业文本

        Args:
            text: 非结构化工业文本内容
        Returns:
            标注后的结构化数据
        """
        annotations = []

        for pattern in self.device_patterns:
            for match in pattern.finditer(text):
                annotations.append({
                    "entity": match.group(1),
                    "type": "DeviceName",
                    "span": match.span(),
                    "attributes": [],
                    "operations": [],
                })

        for op_pattern in self.operation_patterns:
            for match in op_pattern.finditer(text):
                annotations.append({
                    "entity": match.group(0),
                    "type": "Operation",
                    "span": match.span(),
                    "parameters": [],
                })

        for match in self.property_pattern.finditer(text):
            name = match.group(1)
            value = match.group(2)
            unit = match.group(3) or ""
            annotations.append({
                "entity": name,
                "type": "Attribute",
                "span": match.span(),
                "value": value,
                "data_type": "Double" if "." in value else "Integer",
                "unit": unit,
            })

        device_names = [
            a for a in annotations if a["type"] == "DeviceName"
        ]
        main_device = device_names[0]["entity"] if device_names else "UnknownDevice"

        return {
            "text": text,
            "device_name": main_device,
            "annotations": annotations,
            "device_count": len(device_names),
            "attribute_count": len(
                [a for a in annotations if a["type"] == "Attribute"]
            ),
            "operation_count": len(
                [a for a in annotations if a["type"] == "Operation"]
            ),
        }

    def parse_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """批量解析文本"""
        return [self.parse_text(t) for t in texts]

    def to_sa_format(
        self, iea_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """将IEA格式转换为SA格式"""
        from .format_agent import FormatTransformationAgent

        fta = FormatTransformationAgent()
        return fta.convert_from_iea(iea_result)
