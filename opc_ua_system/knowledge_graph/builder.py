import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import torch

from .triple_store import Triple, TripleStore
from .imkg import IMKG_BUILDERS

logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    """知识图谱构建器

    根据设备类型从对应的IMKG定义构建知识图谱。
    不同类别设备之间差距很大，异构性较强，每种设备类型有单独的IMKG。
    """

    def __init__(self):
        self.store = TripleStore()
        self._device_type: Optional[str] = None
        self._entity_to_idx: Dict[str, int] = {}
        self._relation_to_idx: Dict[str, int] = {}
        self._idx_to_entity: Dict[int, str] = {}
        self._idx_to_relation: Dict[int, str] = {}

    def build_from_device_type(self, device_type: str) -> TripleStore:
        builder = IMKG_BUILDERS.get(device_type)
        if builder is None:
            logger.warning(f"未知设备类型: {device_type}，使用默认通用KG")
            builder = IMKG_BUILDERS.get("CNC", lambda: [])

        triples = builder()
        self.store = TripleStore()
        self.store.add_triples(triples)
        self._device_type = device_type
        self._build_mappings()

        logger.info(
            f"已构建 {device_type} 类型的IMKG: "
            f"{self.store.entity_count}个实体, "
            f"{self.store.relation_count}种关系, "
            f"{self.store.triple_count}个三元组"
        )
        return self.store

    def _build_mappings(self) -> None:
        entities = sorted(self.store.get_all_entities())
        relations = sorted(self.store.get_all_relations())

        self._entity_to_idx = {e: i for i, e in enumerate(entities)}
        self._relation_to_idx = {r: i for i, r in enumerate(relations)}
        self._idx_to_entity = {i: e for e, i in self._entity_to_idx.items()}
        self._idx_to_relation = {i: r for r, i in self._relation_to_idx.items()}

    @property
    def num_entities(self) -> int:
        return len(self._entity_to_idx)

    @property
    def num_relations(self) -> int:
        return len(self._relation_to_idx)

    def entity_to_idx(self, entity: str) -> Optional[int]:
        return self._entity_to_idx.get(entity)

    def relation_to_idx(self, relation: str) -> Optional[int]:
        return self._relation_to_idx.get(relation)

    def idx_to_entity(self, idx: int) -> str:
        return self._idx_to_entity.get(idx, "<UNK>")

    def idx_to_relation(self, idx: int) -> str:
        return self._idx_to_relation.get(idx, "<UNK>")

    def get_triple_indices(self) -> List[List[int]]:
        indices = []
        for triple in self.store._triples:
            h = self._entity_to_idx.get(triple.head)
            r = self._relation_to_idx.get(triple.relation)
            t = self._entity_to_idx.get(triple.tail)
            if h is not None and r is not None and t is not None:
                indices.append([h, r, t])
        return indices

    def get_entity_embeddings_init(
        self, dim: int = 256
    ) -> torch.Tensor:
        return torch.randn(self.num_entities, dim) * 0.1

    def get_relation_embeddings_init(
        self, dim: int = 256
    ) -> torch.Tensor:
        return torch.randn(self.num_relations, dim) * 0.1

    def add_completed_triples(
        self, triples: List[Triple]
    ) -> None:
        self.store.add_triples(triples)
        self._build_mappings()
        logger.info(f"已添加 {len(triples)} 个补全三元组")

    def get_adjacency_info(self) -> tuple:
        triples = []
        for t in self.store._triples:
            h = self._entity_to_idx.get(t.head)
            r = self._relation_to_idx.get(t.relation)
            ta = self._entity_to_idx.get(t.tail)
            if h is not None and r is not None and ta is not None:
                triples.append((h, r, ta))

        return (
            np.array([t[0] for t in triples]),
            np.array([t[1] for t in triples]),
            np.array([t[2] for t in triples]),
        )

    @property
    def device_type(self) -> Optional[str]:
        return self._device_type

    def export_to_json(self, filepath: str) -> None:
        import json

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.store.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"知识图谱已导出: {filepath}")
