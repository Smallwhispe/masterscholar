import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .client import OPCUAClient, OPCUANode

logger = logging.getLogger(__name__)


class DataCollector:
    """OPC UA数据帧采集器 - 从OPC UA服务器持续采集数据帧并转换为JSON格式"""

    def __init__(
        self,
        client: OPCUAClient,
        output_dir: str = "data/raw",
        json_indent: int = 2,
    ):
        self.client = client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.json_indent = json_indent
        self._collecting = False
        self._frame_counter = 0
        self._collected_frames: List[Dict[str, Any]] = []
        self._callbacks: List[Callable] = []

    async def collect_snapshot(
        self, root_node_id: str = "0:ObjectsFolder"
    ) -> Dict[str, Any]:
        """采集一次完整的地址空间快照 (数据帧)"""
        if not self.client.is_connected:
            logger.error("OPC UA客户端未连接")
            return {}

        nodes = await self.client.browse_nodes(root_node_id)
        frame = self._build_frame(nodes)
        self._frame_counter += 1
        self._collected_frames.append(frame)
        return frame

    def _build_frame(self, nodes: List[OPCUANode]) -> Dict[str, Any]:
        """将节点列表构建为标准数据帧 (JSON格式)"""
        nodes_dict = {}
        device_metadata = []

        for node in nodes:
            node_data = node.to_dict()
            nodes_dict[node.node_id] = node_data

            if node.value is not None:
                device_metadata.append(
                    {
                        "field_name": node.display_name,
                        "browse_name": node.browse_name,
                        "value": node_data["value"],
                        "data_type": node.data_type,
                        "node_class": node.node_class,
                        "node_id": node.node_id,
                        "parent_node_id": node.parent_node_id,
                    }
                )

        frame = {
            "frame_id": self._frame_counter,
            "timestamp": datetime.now().isoformat(),
            "server_url": self.client.server_url,
            "node_count": len(nodes),
            "nodes": nodes_dict,
            "device_metadata": device_metadata,
            "hierarchy": self._build_hierarchy(nodes),
        }
        return frame

    def _build_hierarchy(
        self, nodes: List[OPCUANode]
    ) -> Dict[str, Any]:
        """从节点列表构建层次结构树"""
        lookup = {n.node_id: n for n in nodes}
        root_nodes = []

        for node in nodes:
            if node.parent_node_id is None or node.parent_node_id not in lookup:
                root_nodes.append(node.node_id)

        def build_tree(node_id: str) -> Dict[str, Any]:
            node = lookup.get(node_id)
            if node is None:
                return {}
            return {
                "node_id": node.node_id,
                "display_name": node.display_name,
                "node_class": node.node_class,
                "value": str(node.value) if node.value is not None else None,
                "children": [
                    build_tree(cid)
                    for cid in node.children
                    if cid in lookup
                ],
            }

        return {
            "roots": [build_tree(rid) for rid in root_nodes]
        }

    def save_frame(self, frame: Dict[str, Any], filename: str = None) -> str:
        """保存数据帧到JSON文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"frame_{self._frame_counter}_{timestamp}.json"

        filepath = self.output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(frame, f, ensure_ascii=False, indent=self.json_indent)

        logger.info(f"数据帧已保存: {filepath}")
        return str(filepath)

    def add_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """注册数据帧回调函数"""
        self._callbacks.append(callback)

    async def start_streaming(
        self,
        root_node_id: str = "0:ObjectsFolder",
        interval_ms: int = 1000,
        max_frames: int = 0,
    ) -> None:
        """开始流式采集数据帧"""
        self._collecting = True
        logger.info(
            f"开始流式采集，间隔={interval_ms}ms, "
            f"最大帧数={'无限' if max_frames == 0 else max_frames}"
        )

        while self._collecting:
            try:
                frame = await self.collect_snapshot(root_node_id)
                self.save_frame(frame)

                for cb in self._callbacks:
                    try:
                        cb(frame)
                    except Exception as e:
                        logger.error(f"回调执行出错: {e}")

                if max_frames > 0 and self._frame_counter >= max_frames:
                    break

                await asyncio.sleep(interval_ms / 1000.0)

            except Exception as e:
                logger.error(f"采集数据帧时出错: {e}")
                await asyncio.sleep(1.0)

        logger.info(f"流式采集结束，共采集 {self._frame_counter} 帧")

    def stop_streaming(self) -> None:
        """停止流式采集"""
        self._collecting = False

    def get_latest_frame(self) -> Optional[Dict[str, Any]]:
        """获取最新采集的数据帧"""
        if self._collected_frames:
            return self._collected_frames[-1]
        return None

    def export_to_processed(self, output_dir: str = "data/processed") -> str:
        """将采集的数据帧导出到处理后目录供后续模块使用"""
        processed_dir = Path(output_dir)
        processed_dir.mkdir(parents=True, exist_ok=True)

        metadata_file = processed_dir / "device_metadata.json"
        all_metadata = []
        for frame in self._collected_frames:
            all_metadata.extend(frame.get("device_metadata", []))

        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(all_metadata, f, ensure_ascii=False, indent=2)

        logger.info(f"设备元数据已导出: {metadata_file}")
        return str(metadata_file)
