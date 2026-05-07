from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class Triple:
    """知识图谱三元组 <head, relation, tail>"""
    head: str
    relation: str
    tail: str
    head_type: str = ""
    tail_type: str = ""
    confidence: float = 1.0
    source: str = "imkg"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "head": self.head,
            "relation": self.relation,
            "tail": self.tail,
            "head_type": self.head_type,
            "tail_type": self.tail_type,
            "confidence": self.confidence,
            "source": self.source,
        }

    def __hash__(self):
        return hash((self.head, self.relation, self.tail))

    def __eq__(self, other):
        if not isinstance(other, Triple):
            return False
        return (
            self.head == other.head
            and self.relation == other.relation
            and self.tail == other.tail
        )


class TripleStore:
    """三元组存储 - 管理知识图谱中的所有三元组"""

    def __init__(self):
        self._triples: List[Triple] = []
        self._entity_index: Dict[str, Set[int]] = {}    # entity -> triple indices
        self._relation_index: Dict[str, Set[int]] = {}  # relation -> triple indices
        self._head_index: Dict[str, Set[int]] = {}      # head -> triple indices
        self._tail_index: Dict[str, Set[int]] = {}      # tail -> triple indices
        self._entity_types: Dict[str, str] = {}

    def add_triple(self, triple: Triple) -> None:
        """添加三元组"""
        if triple in self._triples:
            return
        idx = len(self._triples)
        self._triples.append(triple)

        for entity in (triple.head, triple.tail):
            self._entity_index.setdefault(entity, set()).add(idx)
        self._relation_index.setdefault(triple.relation, set()).add(idx)
        self._head_index.setdefault(triple.head, set()).add(idx)
        self._tail_index.setdefault(triple.tail, set()).add(idx)

        if triple.head_type:
            self._entity_types[triple.head] = triple.head_type
        if triple.tail_type:
            self._entity_types[triple.tail] = triple.tail_type

    def add_triples(self, triples: List[Triple]) -> None:
        """批量添加三元组"""
        for t in triples:
            self.add_triple(t)

    def get_all_entities(self) -> Set[str]:
        """获取所有实体"""
        return set(self._entity_index.keys())

    def get_all_relations(self) -> Set[str]:
        """获取所有关系"""
        return set(self._relation_index.keys())

    def get_entity_type(self, entity: str) -> Optional[str]:
        """获取实体类型"""
        return self._entity_types.get(entity)

    def query_by_head(self, head: str) -> List[Triple]:
        """根据head查询三元组"""
        return [self._triples[i] for i in self._head_index.get(head, set())]

    def query_by_tail(self, tail: str) -> List[Triple]:
        """根据tail查询三元组"""
        return [self._triples[i] for i in self._tail_index.get(tail, set())]

    def query_by_relation(self, relation: str) -> List[Triple]:
        """根据关系查询三元组"""
        return [self._triples[i] for i in self._relation_index.get(relation, set())]

    def query(
        self,
        head: str = None,
        relation: str = None,
        tail: str = None,
    ) -> List[Triple]:
        """多条件查询三元组"""
        results = set(range(len(self._triples)))
        if head is not None:
            results &= self._head_index.get(head, set())
        if relation is not None:
            results &= self._relation_index.get(relation, set())
        if tail is not None:
            results &= self._tail_index.get(tail, set())
        return [self._triples[i] for i in results]

    def get_neighbors(self, entity: str) -> List[Triple]:
        """获取实体的所有邻接三元组"""
        indices = self._entity_index.get(entity, set())
        return [self._triples[i] for i in indices]

    def get_subgraph(
        self, entity: str, max_depth: int = 2
    ) -> List[Triple]:
        """获取实体为中心的子图"""
        visited_triples: Set[int] = set()
        frontier = {entity}

        for _ in range(max_depth):
            next_frontier = set()
            for e in frontier:
                for idx in self._entity_index.get(e, set()):
                    if idx not in visited_triples:
                        visited_triples.add(idx)
                        t = self._triples[idx]
                        next_frontier.add(t.head)
                        next_frontier.add(t.tail)
            frontier = next_frontier

        return [self._triples[i] for i in visited_triples]

    def get_entity_to_entity_triples(
        self, entity1: str, entity2: str
    ) -> List[Triple]:
        """查找两个实体之间的直接三元组"""
        results = []
        for t in self.query(head=entity1, tail=entity2):
            results.append(t)
        for t in self.query(head=entity2, tail=entity1):
            results.append(t)
        return results

    @property
    def triple_count(self) -> int:
        return len(self._triples)

    @property
    def entity_count(self) -> int:
        return len(self._entity_index)

    @property
    def relation_count(self) -> int:
        return len(self._relation_index)

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "triples": [t.to_dict() for t in self._triples],
            "entity_count": self.entity_count,
            "relation_count": self.relation_count,
            "entities": sorted(self.get_all_entities()),
            "relations": sorted(self.get_all_relations()),
        }

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "triple_count": self.triple_count,
            "entity_count": self.entity_count,
            "relation_count": self.relation_count,
            "entity_types": dict(self._entity_types),
            "relations": list(self.get_all_relations()),
        }
