import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.optim as optim

from .cbow import CBOW
from .complex_model import ComplEx
from .space_transformer import SpaceTransformer

logger = logging.getLogger(__name__)


class CompletionTrainer:
    """知识补全训练器 - 联合训练CBOW、ComplEx和空间变换

    整体训练流程:
    1. 在IMKG三元组上训练ComplEx，得到KG空间的实体/关系嵌入
    2. 在实体名称的字符序列上训练CBOW，得到字符语义空间嵌入
    3. 使用已有实体名对应的KG嵌入作为监督，训练空间变换
    4. 结合后：未知实体名 → CBOW → SpaceTransform → KG空间 → ComplEx打分补全
    """

    def __init__(
        self,
        cbow: CBOW,
        complex_model: ComplEx,
        space_transformer: SpaceTransformer,
        device: str = "cpu",
        lr_cbow: float = 0.001,
        lr_complex: float = 0.001,
        lr_transform: float = 0.0005,
    ):
        self.cbow = cbow.to(device)
        self.complex = complex_model.to(device)
        self.transformer = space_transformer.to(device)
        self.device = device

        self.cbow_optimizer = optim.Adam(cbow.parameters(), lr=lr_cbow)
        self.complex_optimizer = optim.Adam(complex_model.parameters(), lr=lr_complex)
        self.transform_optimizer = optim.Adam(
            space_transformer.parameters(), lr=lr_transform
        )
        self.cbow_criterion = nn.CrossEntropyLoss()

    def train_cbow(
        self,
        context_batches: List[torch.Tensor],
        target_batches: List[torch.Tensor],
        max_epochs: int = 100,
    ) -> Dict[str, List[float]]:
        """训练CBOW字符嵌入模型"""
        history = {"loss": []}

        for epoch in range(max_epochs):
            epoch_loss = 0.0
            n_batches = 0

            for context, target in zip(context_batches, target_batches):
                context = context.to(self.device)
                target = target.to(self.device)

                self.cbow_optimizer.zero_grad()
                logits = self.cbow(context)
                loss = self.cbow_criterion(logits, target)
                loss.backward()
                self.cbow_optimizer.step()

                epoch_loss += loss.item()
                n_batches += 1

            avg_loss = epoch_loss / max(n_batches, 1)
            history["loss"].append(avg_loss)

            if (epoch + 1) % 10 == 0:
                logger.info(
                    f"CBOW Epoch {epoch+1}/{max_epochs}, Loss: {avg_loss:.4f}"
                )

        return history

    def train_complex(
        self,
        triple_indices: List[List[int]],
        max_epochs: int = 200,
        batch_size: int = 128,
        negative_samples: int = 10,
    ):
        """训练ComplEx模型"""
        import random

        history = {"loss": []}

        device = self.device
        num_entities = self.complex.num_entities

        for epoch in range(max_epochs):
            random.shuffle(triple_indices)
            epoch_loss = 0.0
            n_batches = 0

            for start in range(0, len(triple_indices), batch_size):
                batch = triple_indices[start : start + batch_size]
                if len(batch) < 2:
                    continue

                heads = torch.tensor(
                    [t[0] for t in batch], dtype=torch.long, device=device
                )
                rels = torch.tensor(
                    [t[1] for t in batch], dtype=torch.long, device=device
                )
                tails = torch.tensor(
                    [t[2] for t in batch], dtype=torch.long, device=device
                )

                positive_scores = self.complex(heads, rels, tails)

                neg_tails = torch.randint(
                    0, num_entities, (len(batch), negative_samples), device=device
                )
                all_neg_scores = []
                for ns in range(negative_samples):
                    neg_t = neg_tails[:, ns]
                    neg_score = self.complex(heads, rels, neg_t)
                    all_neg_scores.append(neg_score.unsqueeze(1))
                neg_scores = torch.cat(all_neg_scores, dim=1).mean(dim=1)

                loss = self.complex.compute_loss(positive_scores, neg_scores)

                self.complex_optimizer.zero_grad()
                loss.backward()
                self.complex_optimizer.step()

                epoch_loss += loss.item()
                n_batches += 1

            avg_loss = epoch_loss / max(n_batches, 1)
            history["loss"].append(avg_loss)

            if (epoch + 1) % 20 == 0:
                logger.info(
                    f"ComplEx Epoch {epoch+1}/{max_epochs}, Loss: {avg_loss:.4f}"
                )

        return history

    def train_transformer(
        self,
        entity_name_to_cbow: Dict[str, torch.Tensor],
        entity_to_kg_embedding: Dict[str, torch.Tensor],
        entity_to_idx: Dict[str, int],
        max_epochs: int = 100,
        batch_size: int = 64,
    ) -> Dict[str, List[float]]:
        """训练空间变换 (CBOW空间 → KG空间)

        使用IMKG中已有实体的KG嵌入作为训练目标
        """
        import random

        history = {"loss": []}
        mse_loss = nn.MSELoss()

        entity_names = list(entity_name_to_cbow.keys())
        cbow_vecs = torch.stack(
            [entity_name_to_cbow[e] for e in entity_names]
        ).to(self.device)

        kg_vecs = torch.stack(
            [entity_to_kg_embedding.get(e, torch.zeros(self.transformer.kg_dim))
             for e in entity_names]
        ).to(self.device)

        indices = list(range(len(entity_names)))

        for epoch in range(max_epochs):
            random.shuffle(indices)
            epoch_loss = 0.0
            n_batches = 0

            for start in range(0, len(indices), batch_size):
                batch_idx = indices[start : start + batch_size]

                cbow_batch = cbow_vecs[batch_idx]
                kg_batch = kg_vecs[batch_idx]

                self.transform_optimizer.zero_grad()
                predicted = self.transformer(cbow_batch)
                loss = mse_loss(predicted, kg_batch)
                loss.backward()
                self.transform_optimizer.step()

                epoch_loss += loss.item()
                n_batches += 1

            avg_loss = epoch_loss / max(n_batches, 1)
            history["loss"].append(avg_loss)

            if (epoch + 1) % 10 == 0:
                logger.info(
                    f"Transform Epoch {epoch+1}/{max_epochs}, Loss: {avg_loss:.4f}"
                )

        return history

    def save_models(self, base_dir: str) -> None:
        """保存所有模型"""
        base = Path(base_dir)
        base.mkdir(parents=True, exist_ok=True)

        torch.save(self.cbow.state_dict(), base / "cbow.pt")
        torch.save(self.complex.state_dict(), base / "complex.pt")
        torch.save(self.transformer.state_dict(), base / "transformer.pt")
        logger.info(f"模型已保存到: {base_dir}")

    def load_models(self, base_dir: str) -> None:
        """加载所有模型"""
        base = Path(base_dir)
        self.cbow.load_state_dict(
            torch.load(base / "cbow.pt", map_location=self.device)
        )
        self.complex.load_state_dict(
            torch.load(base / "complex.pt", map_location=self.device)
        )
        self.transformer.load_state_dict(
            torch.load(base / "transformer.pt", map_location=self.device)
        )
        self.cbow.eval()
        self.complex.eval()
        self.transformer.eval()
        logger.info(f"模型已从 {base_dir} 加载")
