import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SPARQLEndpoint:
    """基于RDFLib的SPARQL查询端点 - 知识图谱语义查询"""

    def __init__(self, namespace: str = "http://example.org/ua/"):
        self.namespace = namespace
        self._graph = None

    def init_graph(self) -> None:
        """初始化RDF图"""
        try:
            from rdflib import Graph, Namespace, RDF, RDFS

            self._graph = Graph()
            self.ns = Namespace(self.namespace)
            self._graph.bind("ua", self.ns)
            self.RDF = RDF
            self.RDFS = RDFS
            logger.info("RDF图初始化完成")
        except ImportError:
            logger.error("rdflib模块未安装，请运行: pip install rdflib")

    def load_triples(self, triples: List[Dict]) -> int:
        """加载三元组到RDF图中"""
        if self._graph is None:
            self.init_graph()
            if self._graph is None:
                return 0

        count = 0
        for t in triples:
            head = self.ns[t.get("head", "")]
            relation = self.ns[t.get("relation", "")]
            tail = self.ns[t.get("tail", "")]
            self._graph.add((head, relation, tail))
            count += 1

        logger.info(f"已加载 {count} 个三元组到RDF图")
        return count

    def query(self, sparql_query: str) -> List[Dict]:
        """执行SPARQL查询"""
        if self._graph is None:
            logger.error("RDF图未初始化")
            return []

        try:
            results = self._graph.query(sparql_query)
            bindings = [
                {
                    str(var): str(bind[var]).split("#")[-1]
                    if "#" in str(bind[var])
                    else str(bind[var])
                    for var in results.vars
                }
                for bind in results
            ]
            return bindings
        except Exception as e:
            logger.error(f"SPARQL查询失败: {e}")
            return []

    def query_entity_properties(self, entity: str) -> Dict[str, List[str]]:
        """查询实体的所有属性"""
        query = f"""
        PREFIX ua: <{self.namespace}>
        SELECT ?property ?value
        WHERE {{
            ua:{entity} ?property ?value .
            ?property a rdf:Property .
        }}
        """
        results = self.query(query)
        props = {}
        for r in results:
            prop = r.get("property", "")
            val = r.get("value", "")
            props.setdefault(prop, []).append(val)
        return props

    def query_subclass_hierarchy(self, class_name: str) -> List[str]:
        """查询类的继承层次"""
        query = f"""
        PREFIX ua: <{self.namespace}>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?subclass
        WHERE {{
            ?subclass rdfs:subClassOf ua:{class_name} .
        }}
        """
        results = self.query(query)
        return [r.get("subclass", "") for r in results]

    def save_rdf(self, filepath: str) -> None:
        """保存RDF图到文件"""
        if self._graph is None:
            return

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        fmt = "xml"
        if filepath.endswith(".ttl"):
            fmt = "turtle"
        elif filepath.endswith(".nt"):
            fmt = "nt"
        elif filepath.endswith(".jsonld"):
            fmt = "json-ld"

        self._graph.serialize(destination=filepath, format=fmt)
        logger.info(f"RDF图已保存: {filepath}")

    def load_rdf(self, filepath: str) -> None:
        """从文件加载RDF图"""
        if self._graph is None:
            self.init_graph()

        fmt = None
        if filepath.endswith(".ttl"):
            fmt = "turtle"
        elif filepath.endswith(".rdf") or filepath.endswith(".owl"):
            fmt = "xml"

        try:
            self._graph.parse(filepath, format=fmt)
            logger.info(f"已加载RDF文件: {filepath}")
        except Exception as e:
            logger.error(f"加载RDF文件失败: {e}")
