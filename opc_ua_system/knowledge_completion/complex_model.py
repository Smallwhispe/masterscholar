from typing import Optional, Tuple

import torch
import torch.nn as nn


class ComplEx(nn.Module):
    """ComplEx模型 - 复数张量分解知识图谱补全

    实体向量和关系向量从IMKG的真实三元组出发：
    1. 随机初始化
    2. 正负样本训练
    3. 打分函数计算

    最终这些向量用于判断三元组的合理性，帮助未知字段找到正确的父节点。

    ComplEx打分函数:
    score(h, r, t) = Re(<w_h, w_r, conj(w_t)>)
    = Re(sum(w_h * w_r * conj(w_t)))
    """

    def __init__(
        self,
        num_entities: int,
        num_relations: int,
        embedding_dim: int = 256,
        regularization_lambda: float = 0.01,
    ):
        super().__init__()
        self.num_entities = num_entities
        self.num_relations = num_relations
        self.embedding_dim = embedding_dim
        self.regularization_lambda = regularization_lambda

        self.entity_embeddings = nn.Embedding(num_entities, embedding_dim * 2)
        self.relation_embeddings = nn.Embedding(num_relations, embedding_dim * 2)

        nn.init.xavier_uniform_(self.entity_embeddings.weight)
        nn.init.xavier_uniform_(self.relation_embeddings.weight)

    def _split_complex(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """将向量拆分为实部和虚部"""
        return x[..., :self.embedding_dim], x[..., self.embedding_dim:]

    def get_entity_embedding(
        self, entity_ids: torch.Tensor, return_complex: bool = False
    ) -> torch.Tensor:
        """获取实体嵌入"""
        emb = self.entity_embeddings(entity_ids)
        if return_complex:
            return emb
        real, imag = self._split_complex(emb)
        return torch.complex(real, imag)

    def get_relation_embedding(
        self, relation_ids: torch.Tensor, return_complex: bool = False
    ) -> torch.Tensor:
        """获取关系嵌入"""
        emb = self.relation_embeddings(relation_ids)
        if return_complex:
            return emb
        real, imag = self._split_complex(emb)
        return torch.complex(real, imag)

    def score(
        self,
        head_ids: torch.Tensor,
        relation_ids: torch.Tensor,
        tail_ids: torch.Tensor,
    ) -> torch.Tensor:
        """计算ComplEx打分函数

        score(h, r, t) = Re(sum(h_conj * r * t))
        """
        h = self.get_entity_embedding(head_ids)
        r = self.get_relation_embedding(relation_ids)
        t = self.get_entity_embedding(tail_ids)

        scores = torch.sum(
            h.conj() * r * t, dim=-1
        ).real
        return scores

    def forward(
        self,
        head_ids: torch.Tensor,
        relation_ids: torch.Tensor,
        tail_ids: torch.Tensor,
    ) -> torch.Tensor:
        """前向传播计算正样本得分"""
        return self.score(head_ids, relation_ids, tail_ids)

    def compute_loss(
        self,
        positive_scores: torch.Tensor,
        negative_scores: torch.Tensor,
    ) -> torch.Tensor:
        """计算损失 (使用Margin Ranking Loss)"""
        margin = 1.0
        target = torch.ones_like(positive_scores)
        loss = torch.nn.functional.margin_ranking_loss(
            positive_scores, negative_scores, target, margin=margin
        )
        reg_loss = self.regularization_lambda * (
            self.entity_embeddings.weight.norm(p=2)
            + self.relation_embeddings.weight.norm(p=2)
        )
        return loss + reg_loss

    def predict_head(
        self,
        relation_id: int,
        tail_id: int,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """预测给定(relation, tail)的head实体

        key: ComplEx对每个未知tail做head预测
        """
        r = self.get_entity_embedding(
            torch.tensor([relation_id], device=self.entity_embeddings.weight.device)
        )
        t = self.get_entity_embedding(
            torch.tensor([tail_id], device=self.entity_embeddings.weight.device)
        )

        all_heads = self.get_entity_embedding(
            torch.arange(self.num_entities, device=self.entity_embeddings.weight.device)
        )

        scores = torch.sum(all_heads.conj() * r * t, dim=-1).real
        return scores, torch.argsort(scores, descending=True)

    def predict_tail(
        self,
        head_id: int,
        relation_id: int,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """预测给定(head, relation)的tail实体"""
        h = self.get_entity_embedding(
            torch.tensor([head_id], device=self.entity_embeddings.weight.device)
        )
        r = self.get_relation_embedding(
            torch.tensor([relation_id], device=self.entity_embeddings.weight.device)
        )

        all_tails = self.get_entity_embedding(
            torch.arange(self.num_entities, device=self.entity_embeddings.weight.device)
        )

        scores = torch.sum(h.conj() * r * all_tails, dim=-1).real
        return scores, torch.argsort(scores, descending=True)

    def get_all_entity_embeddings_real(self) -> torch.Tensor:
        """获取所有实体的嵌入 (用于空间变换映射)"""
        emb = self.entity_embeddings.weight
        real, imag = self._split_complex(emb)
        return torch.cat([real, imag], dim=-1)
