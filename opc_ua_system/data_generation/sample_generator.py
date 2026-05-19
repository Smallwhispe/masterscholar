import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SampleData:
    """示例数据生成器 - 提供各阶段的示例输入输出

    对应目录: data/samples/
    - sample_frame.json      : OPC UA数据帧示例
    - sample_metadata.json   : 设备元数据示例
    - sample_iea.json        : IEA格式示例
    - sample_sa.json         : SA格式示例
    """

    def __init__(self, samples_dir: str = "data/samples/"):
        self.samples_dir = Path(samples_dir)
        self.samples_dir.mkdir(parents=True, exist_ok=True)

    def create_sample_frame(self) -> Dict:
        """创建OPC UA数据帧示例"""
        frame = {
            "frame_id": 1,
            "timestamp": "2025-01-15T10:30:00",
            "server_url": "opc.tcp://192.168.1.100:4840",
            "node_count": 8,
            "nodes": {
                "ns=2;i=5001": {
                    "node_id": "ns=2;i=5001",
                    "display_name": "CNCMachine_01",
                    "browse_name": "CNCMachine_01",
                    "node_class": "Object",
                    "data_type": "",
                    "parent_node_id": None,
                    "children": [
                        "ns=2;i=5002",
                        "ns=2;i=5003",
                        "ns=2;i=5004",
                    ],
                    "timestamp": "2025-01-15T10:30:00",
                },
                "ns=2;i=5002": {
                    "node_id": "ns=2;i=5002",
                    "display_name": "Spindle",
                    "browse_name": "Spindle",
                    "node_class": "Object",
                    "parent_node_id": "ns=2;i=5001",
                    "children": ["ns=2;i=5005", "ns=2;i=5006"],
                },
                "ns=2;i=5003": {
                    "node_id": "ns=2;i=5003",
                    "display_name": "ToolChanger",
                    "browse_name": "ToolChanger",
                    "node_class": "Object",
                    "parent_node_id": "ns=2;i=5001",
                    "children": ["ns=2;i=5007"],
                },
                "ns=2;i=5004": {
                    "node_id": "ns=2;i=5004",
                    "display_name": "Worktable",
                    "browse_name": "Worktable",
                    "node_class": "Object",
                    "parent_node_id": "ns=2;i=5001",
                    "children": ["ns=2;i=5008"],
                },
                "ns=2;i=5005": {
                    "node_id": "ns=2;i=5005",
                    "display_name": "SpindleSpeed",
                    "browse_name": "SpindleSpeed",
                    "node_class": "Variable",
                    "value": "8000",
                    "data_type": "UInt32",
                    "parent_node_id": "ns=2;i=5002",
                },
                "ns=2;i=5006": {
                    "node_id": "ns=2;i=5006",
                    "display_name": "SpindleLoad",
                    "browse_name": "SpindleLoad",
                    "node_class": "Variable",
                    "value": "45.2",
                    "data_type": "Double",
                    "parent_node_id": "ns=2;i=5002",
                },
                "ns=2;i=5007": {
                    "node_id": "ns=2;i=5007",
                    "display_name": "ToolNumber",
                    "browse_name": "ToolNumber",
                    "node_class": "Variable",
                    "value": "3",
                    "data_type": "UInt16",
                    "parent_node_id": "ns=2;i=5003",
                },
                "ns=2;i=5008": {
                    "node_id": "ns=2;i=5008",
                    "display_name": "FeedRate",
                    "browse_name": "FeedRate",
                    "node_class": "Variable",
                    "value": "150.0",
                    "data_type": "Double",
                    "parent_node_id": "ns=2;i=5004",
                },
            },
            "device_metadata": [
                {
                    "field_name": "Spindle",
                    "browse_name": "Spindle",
                    "value": "",
                    "data_type": "",
                    "node_class": "Object",
                    "node_id": "ns=2;i=5002",
                    "parent_node_id": "ns=2;i=5001",
                },
                {
                    "field_name": "ToolChanger",
                    "browse_name": "ToolChanger",
                    "value": "",
                    "data_type": "",
                    "node_class": "Object",
                    "node_id": "ns=2;i=5003",
                    "parent_node_id": "ns=2;i=5001",
                },
                {
                    "field_name": "Worktable",
                    "browse_name": "Worktable",
                    "value": "",
                    "data_type": "",
                    "node_class": "Object",
                    "node_id": "ns=2;i=5004",
                    "parent_node_id": "ns=2;i=5001",
                },
                {
                    "field_name": "SpindleSpeed",
                    "browse_name": "SpindleSpeed",
                    "value": "8000",
                    "data_type": "UInt32",
                    "node_class": "Variable",
                    "node_id": "ns=2;i=5005",
                    "parent_node_id": "ns=2;i=5002",
                },
                {
                    "field_name": "SpindleLoad",
                    "browse_name": "SpindleLoad",
                    "value": "45.2",
                    "data_type": "Double",
                    "node_class": "Variable",
                    "node_id": "ns=2;i=5006",
                    "parent_node_id": "ns=2;i=5002",
                },
                {
                    "field_name": "ToolNumber",
                    "browse_name": "ToolNumber",
                    "value": "3",
                    "data_type": "UInt16",
                    "node_class": "Variable",
                    "node_id": "ns=2;i=5007",
                    "parent_node_id": "ns=2;i=5003",
                },
                {
                    "field_name": "FeedRate",
                    "browse_name": "FeedRate",
                    "value": "150.0",
                    "data_type": "Double",
                    "node_class": "Variable",
                    "node_id": "ns=2;i=5008",
                    "parent_node_id": "ns=2;i=5004",
                },
            ],
        }

        filepath = self.samples_dir / "sample_frame.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(frame, f, ensure_ascii=False, indent=2)
        logger.info(f"示例数据帧已创建: {filepath}")
        return frame

    def create_sample_sa(self) -> Dict:
        """创建SA格式示例"""
        sa = {
            "device_name": "CNC Machine",
            "objects": [
                {
                    "name": "Spindle",
                    "variables": [
                        {"name": "SpindleSpeed", "value": "8000", "data_type": "UInt32"},
                        {"name": "SpindleLoad", "value": "45.2", "data_type": "Double"},
                    ],
                    "methods": [
                        {"name": "StartSpindle", "params": []},
                    ],
                },
                {
                    "name": "ToolChanger",
                    "variables": [
                        {"name": "ToolNumber", "value": "3", "data_type": "UInt16"},
                    ],
                    "methods": [
                        {"name": "ChangeTool", "params": ["tool_id"]},
                    ],
                },
            ],
        }

        filepath = self.samples_dir / "sample_sa.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(sa, f, ensure_ascii=False, indent=2)
        return sa

    def create_sample_iea(self) -> Dict:
        """创建IEA格式示例"""
        iea = {
            "text": "CNCMachine_01 with Spindle running at 8000 RPM, ToolChanger holding 3 tools",
            "annotations": [
                {
                    "entity": "CNCMachine_01",
                    "type": "DeviceName",
                    "span": [0, 16],
                    "attributes": [],
                    "operations": [],
                },
                {
                    "entity": "Spindle",
                    "type": "DeviceName",
                    "span": [21, 28],
                    "attributes": [
                        {"name": "SpindleSpeed", "value": "8000", "unit": "RPM"},
                    ],
                    "operations": [],
                },
                {
                    "entity": "ToolChanger",
                    "type": "DeviceName",
                    "span": [41, 52],
                    "attributes": [],
                    "operations": [],
                },
            ],
        }

        filepath = self.samples_dir / "sample_iea.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(iea, f, ensure_ascii=False, indent=2)
        return iea

    def create_all(self) -> Dict[str, str]:
        """创建所有示例数据"""
        self.create_sample_frame()
        self.create_sample_sa()
        self.create_sample_iea()
        return {
            "frame": str(self.samples_dir / "sample_frame.json"),
            "sa": str(self.samples_dir / "sample_sa.json"),
            "iea": str(self.samples_dir / "sample_iea.json"),
        }
