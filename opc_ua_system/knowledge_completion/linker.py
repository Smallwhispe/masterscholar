import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import torch
    import numpy as np

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch未安装，知识补全链接器无法使用")


class KnowledgeLinker:
    """知识补全链接器 - 遍历IMKG实体，找到未知tail的合理父节点(head)

    流程:
    1. 接收未知设备实体的名称
    2. 将名称拆分字符序列 → CBOW编码 → SpaceTransform → KG空间
    3. 遍历所有可能的head ∈ E (E是IMKG中的实体集合)
    4. 用ComplEx的打分函数计算每个候选head的score
    5. 选中分数最高的即为tail应该在IMKG中挂靠的节点
    """

    def __init__(
        self,
        cbow: "CBOW",
        complex_model: "ComplEx",
        space_transformer: "SpaceTransformer",
        char_to_idx: Dict[str, int],
        entity_to_idx: Dict[str, int],
        relation_to_idx: Dict[str, int],
        idx_to_entity: Dict[int, str],
        idx_to_relation: Dict[int, str],
        device: str = "cpu",
    ):
        self.cbow = cbow.to(device)
        self.complex = complex_model.to(device)
        self.transformer = space_transformer.to(device)
        self.char_to_idx = char_to_idx
        self.entity_to_idx = entity_to_idx
        self.relation_to_idx = relation_to_idx
        self.idx_to_entity = idx_to_entity
        self.idx_to_relation = idx_to_relation
        self.device = device

        self.cbow.eval()
        self.complex.eval()
        self.transformer.eval()

    def _name_to_indices(self, name: str) -> List[int]:
        """将名称转换为字符索引"""
        return [
            self.char_to_idx.get(c, self.char_to_idx.get("<UNK>", 1))
            for c in name
        ]

    def _name_to_kg_vector(self, name: str) -> torch.Tensor:
        """将实体名称映射到KG空间向量"""
        indices = self._name_to_indices(name)

        with torch.no_grad():
            cbow_vec = self.cbow.get_name_embedding(indices)
            cbow_vec = cbow_vec.unsqueeze(0).to(self.device)
            kg_vec = self.transformer(cbow_vec)
        return kg_vec.squeeze(0)

    def link_entity(
        self,
        unknown_name: str,
        candidate_relations: List[str] = None,
        top_k: int = 5,
    ) -> List[Dict]:
        """为未知实体找到IMKG中最合理的链接位置

        Args:
            unknown_name: 未知实体名称
            candidate_relations: 候选关系类型列表
            top_k: 返回前K个最高得分的结果
        Returns:
            [{head_name, relation, tail_name, score}, ...]
        """
        if candidate_relations is None:
            candidate_relations = [
                "hasComponent",
                "hasProperty",
                "hasOperation",
                "hasParameter",
                "connectedTo",
                "controlledBy",
            ]

        tail_vec = self._name_to_kg_vector(unknown_name)

        all_heads = self.complex.get_all_entity_embeddings_real()
        head_real, head_imag = torch.chunk(all_heads, 2, dim=-1)
        head_complex = torch.complex(head_real, head_imag)

        results = []

        for rel_name in candidate_relations:
            rel_idx = self.relation_to_idx.get(rel_name)
            if rel_idx is None:
                continue

            with torch.no_grad():
                r = self.complex.get_relation_embedding(
                    torch.tensor([rel_idx], device=self.device)
                ).squeeze(0)

                tail_real, tail_imag = torch.chunk(
                    tail_vec.unsqueeze(0), 2, dim=-1
                )
                tail_complex = torch.complex(
                    tail_real.squeeze(0), tail_imag.squeeze(0)
                )

                scores = torch.sum(
                    head_complex.conj() * r * tail_complex, dim=-1
                ).real

                sorted_scores, sorted_indices = torch.sort(
                    scores, descending=True
                )

                for i in range(min(top_k, len(sorted_indices))):
                    head_idx = sorted_indices[i].item()
                    score = sorted_scores[i].item()
                    head_name = self.idx_to_entity.get(head_idx, f"Entity_{head_idx}")

                    results.append({
                        "head_name": head_name,
                        "relation": rel_name,
                        "tail_name": unknown_name,
                        "score": score,
                        "rank": i + 1,
                    })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def complete_unknown_entities(
        self,
        unknown_entities: List[Dict],
        min_score: float = 0.3,
    ) -> List[Dict]:
        """批量补全未知实体

        Args:
            unknown_entities: 未知实体列表 [{"name": "UnknownField1", "entities": {...}}, ...]
            min_score: 最小接受分数阈值
        Returns:
            补全的三元组列表
        """
        completed = []

        for entity in unknown_entities:
            name = entity.get("name", "")
            entities = entity.get("entities", {})

            for entity_type, entity_list in entities.items():
                for e_name in entity_list:
                    if not e_name:
                        continue

                    relation_map = {
                        "DeviceName": "hasComponent",
                        "Feature": "hasProperty",
                        "Attribute": "hasProperty",
                        "Operation": "hasOperation",
                    }
                    relations = [relation_map.get(entity_type, "hasProperty")]

                    links = self.link_entity(e_name, relations, top_k=1)
                    if links and links[0]["score"] >= min_score:
                        link = links[0]
                        completed.append({
                            "head": link["head_name"],
                            "relation": link["relation"],
                            "tail": link["tail_name"],
                            "score": link["score"],
                            "source": "knowledge_completion",
                        })
                        logger.info(
                            f"补全: {link['head_name']} -{link['relation']}-> "
                            f"{link['tail_name']} (score={link['score']:.4f})"
                        )

        return completed

    def find_parent_node(
        self,
        entity_name: str,
    ) -> Optional[Dict]:
        """找到未知字段在IMKG中最合理的父节点"""
        links = self.link_entity(
            entity_name,
            candidate_relations=["hasComponent", "hasProperty", "hasOperation"],
            top_k=1,
        )
        if links:
            return links[0]
        return None
