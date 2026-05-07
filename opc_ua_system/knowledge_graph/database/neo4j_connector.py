import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Neo4jConnector:
    """Neo4j图数据库连接器 - 知识图谱持久化存储"""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password",
    ):
        self.uri = uri
        self.user = user
        self.password = password
        self._driver = None

    def connect(self) -> bool:
        """连接到Neo4j数据库"""
        try:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
            self._driver.verify_connectivity()
            logger.info(f"已连接到Neo4j: {self.uri}")
            return True
        except ImportError:
            logger.error("neo4j模块未安装，请运行: pip install neo4j")
            return False
        except Exception as e:
            logger.error(f"Neo4j连接失败: {e}")
            return False

    def close(self) -> None:
        """关闭连接"""
        if self._driver:
            self._driver.close()

    def clear_database(self) -> None:
        """清空数据库"""
        if not self._driver:
            return
        with self._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        logger.info("数据库已清空")

    def import_triples(
        self,
        triples: List[Dict],
        device_type: str = "",
    ) -> int:
        """导入三元组到Neo4j"""
        if not self._driver:
            logger.error("未连接到Neo4j")
            return 0

        count = 0
        with self._driver.session() as session:
            for t in triples:
                head = t.get("head", "")
                relation = t.get("relation", "")
                tail = t.get("tail", "")
                head_type = t.get("head_type", "Entity")
                tail_type = t.get("tail_type", "Entity")

                if not head or not relation or not tail:
                    continue

                query = (
                    f"MERGE (h:{head_type} {{name: $head, device_type: $device_type}}) "
                    f"MERGE (t:{tail_type} {{name: $tail, device_type: $device_type}}) "
                    f"MERGE (h)-[:{relation}]->(t)"
                )
                session.run(
                    query,
                    head=head,
                    tail=tail,
                    device_type=device_type,
                )
                count += 1

        logger.info(f"已导入 {count} 个三元组到 Neo4j")
        return count

    def query_entity(
        self, name: str, device_type: str = ""
    ) -> List[Dict]:
        """查询实体相关的三元组"""
        if not self._driver:
            return []
        with self._driver.session() as session:
            query = (
                "MATCH (h)-[r]->(t) "
                "WHERE h.name = $name "
                "RETURN h.name as head, type(r) as relation, t.name as tail, "
                "labels(h)[0] as head_type, labels(t)[0] as tail_type"
            )
            result = session.run(query, name=name)
            return [record.data() for record in result]

    def get_device_kg(
        self, device_type: str
    ) -> Dict[str, List]:
        """获取特定设备类型的完整知识图谱"""
        if not self._driver:
            return {"nodes": [], "edges": []}

        with self._driver.session() as session:
            nodes_query = (
                "MATCH (n {device_type: $device_type}) "
                "RETURN DISTINCT n.name as name, labels(n)[0] as type"
            )
            nodes_result = session.run(
                nodes_query, device_type=device_type
            )
            nodes = [record.data() for record in nodes_result]

            edges_query = (
                "MATCH (h {device_type: $device_type})-[r]->(t {device_type: $device_type}) "
                "RETURN h.name as head, type(r) as relation, t.name as tail"
            )
            edges_result = session.run(
                edges_query, device_type=device_type
            )
            edges = [record.data() for record in edges_result]

        return {"nodes": nodes, "edges": edges}

    def find_path(
        self,
        start: str,
        end: str,
        max_depth: int = 3,
    ) -> List[Dict]:
        """查找两个实体之间的路径"""
        if not self._driver:
            return []
        with self._driver.session() as session:
            query = (
                f"MATCH p = shortestPath((a {{name: $start}})-[*1..{max_depth}]-(b {{name: $end}})) "
                "RETURN [n in nodes(p) | n.name] as path, "
                "[r in relationships(p) | type(r)] as relations"
            )
            result = session.run(query, start=start, end=end)
            return [record.data() for record in result]
