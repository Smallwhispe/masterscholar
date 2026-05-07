import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class OPCUANode:
    node_id: str
    display_name: str
    node_class: str
    browse_name: str
    value: Any = None
    data_type: str = ""
    parent_node_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "display_name": self.display_name,
            "node_class": self.node_class,
            "browse_name": self.browse_name,
            "value": str(self.value) if self.value is not None else None,
            "data_type": self.data_type,
            "parent_node_id": self.parent_node_id,
            "children": self.children,
            "timestamp": self.timestamp,
        }


class OPCUAClient:
    """OPC UA客户端 - 负责连接到OPC UA服务器并浏览节点"""

    def __init__(self, server_url: str, timeout_ms: int = 5000):
        self.server_url = server_url
        self.timeout_ms = timeout_ms
        self._client = None
        self._connected = False

    async def connect(self) -> bool:
        """建立与OPC UA服务器的连接"""
        try:
            from asyncua import Client

            self._client = Client(url=self.server_url, timeout=self.timeout_ms)
            await self._client.connect()
            self._connected = True
            logger.info(f"成功连接到OPC UA服务器: {self.server_url}")
            return True
        except ImportError:
            logger.error("asyncua模块未安装，请运行: pip install asyncua")
            return False
        except Exception as e:
            logger.error(f"连接OPC UA服务器失败: {e}")
            return False

    async def disconnect(self) -> None:
        """断开与OPC UA服务器的连接"""
        if self._client and self._connected:
            try:
                await self._client.disconnect()
                self._connected = False
                logger.info("已断开OPC UA服务器连接")
            except Exception as e:
                logger.error(f"断开连接时出错: {e}")

    async def browse_nodes(
        self, start_node_id: str = "0:ObjectsFolder"
    ) -> List[OPCUANode]:
        """递归浏览服务器地址空间中的所有节点"""
        if not self._connected:
            logger.error("未连接到OPC UA服务器")
            return []

        nodes = []
        try:
            root = self._client.get_node(start_node_id)
            await self._browse_recursive(root, nodes, parent_id=None)
            logger.info(f"浏览完成，共发现 {len(nodes)} 个节点")
        except Exception as e:
            logger.error(f"浏览节点失败: {e}")
        return nodes

    async def _browse_recursive(
        self, node, nodes: List[OPCUANode], parent_id: Optional[str]
    ) -> None:
        """递归浏览子节点"""
        try:
            node_class = await node.read_node_class()
            display_name = (await node.read_display_name()).Text
            browse_name = (await node.read_browse_name()).Name
            node_id = str(await node.read_node_id())

            opcua_node = OPCUANode(
                node_id=node_id,
                display_name=display_name,
                node_class=str(node_class),
                browse_name=browse_name,
                parent_node_id=parent_id,
                timestamp=datetime.now().isoformat(),
            )

            try:
                value = await node.read_value()
                opcua_node.value = value
                if value is not None:
                    dv = await node.read_data_value()
                    if dv.StatusCode.is_good():
                        opcua_node.data_type = str(
                            type(value).__name__
                        )
            except Exception:
                pass

            nodes.append(opcua_node)

            children = await node.get_children()
            for child in children:
                child_id = str(await child.read_node_id())
                opcua_node.children.append(child_id)
                await self._browse_recursive(child, nodes, node_id)

        except Exception as e:
            logger.debug(f"浏览节点时出错: {e}")

    async def subscribe_data_changes(
        self, node_id: str, callback, interval_ms: int = 1000
    ):
        """订阅节点数据变化"""
        if not self._connected:
            logger.error("未连接到OPC UA服务器")
            return None
        try:
            node = self._client.get_node(node_id)
            subscription = await self._client.create_subscription(
                interval_ms, callback
            )
            handle = await subscription.subscribe_data_change(node)
            logger.info(f"已订阅节点 {node_id} 的数据变化")
            return subscription
        except Exception as e:
            logger.error(f"订阅数据变化失败: {e}")
            return None

    @property
    def is_connected(self) -> bool:
        return self._connected
