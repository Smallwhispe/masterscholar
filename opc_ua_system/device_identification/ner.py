import logging
from typing import Dict, List, Optional, Tuple, Set

import torch
import torch.nn as nn
import torch.nn.functional as F
from crf import CRF

logger = logging.getLogger(__name__)


def build_tag_mapping(bio_tags: List[str]) -> Tuple[Dict[int, str], int]:
    """从训练数据的BIO标签集合自动构建标签映射

    输入: 训练语料中出现的所有BIO标签，例如 ["O", "B-DeviceName", "I-DeviceName", ...]
    输出: ({idx: tag}, num_tags)
    """
    sorted_tags = sorted(set(bio_tags))
    if "O" in sorted_tags:
        sorted_tags.remove("O")
        sorted_tags.insert(0, "O")
    tag_to_idx = {tag: i for i, tag in enumerate(sorted_tags)}
    idx_to_tag = {i: tag for tag, i in tag_to_idx.items()}
    logger.info(f"从训练数据构建标签映射: {len(idx_to_tag)} 种标签 {sorted_tags}")
    return idx_to_tag, len(idx_to_tag)


class NERModel(nn.Module):
    """NER实体识别模型 (BiLSTM+CRF)

    标签集从训练数据自动构建，不硬编码。

    从设备字段中识别实体，标签格式为BIO标注：
    - "O": 无关字符
    - "B-xxx": 某类实体开头
    - "I-xxx": 某类实体内部
    实体类别由训练数据决定。
    """

    def __init__(
        self,
        num_entity_tags: int,
        vocab_size: int,
        char_embedding_dim: int = 64,
        hidden_dim: int = 128,
        dropout_rate: float = 0.5,
    ):
        super().__init__()
        self.num_entity_tags = num_entity_tags
        self.char_embedding = nn.Embedding(
            vocab_size, char_embedding_dim, padding_idx=0
        )
        self.bilstm = nn.LSTM(
            input_size=char_embedding_dim,
            hidden_size=hidden_dim // 2,
            num_layers=1,
            batch_first=True,
            bidirectional=True,
        )
        self.dropout = nn.Dropout(dropout_rate)
        self.linear = nn.Linear(hidden_dim, num_entity_tags)
        self.crf = CRF(num_entity_tags)

    def forward(
        self,
        x: torch.Tensor,
        mask: torch.Tensor = None,
        tags: torch.Tensor = None,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        x = self.char_embedding(x)
        x, _ = self.bilstm(x)
        x = self.dropout(x)
        emissions = self.linear(x)

        if tags is not None:
            loss = -self.crf(emissions, tags, mask=mask, summed=False).mean()
            return emissions, loss

        return emissions, None

    def decode(
        self, emissions: torch.Tensor, mask: torch.Tensor = None
    ) -> List[List[int]]:
        return self.crf.decode(emissions, mask=mask)


class EntityExtractor:
    """从NER输出中提取结构化实体

    实体类别由标签映射动态决定，不硬编码。
    """

    def __init__(self, idx_to_tag: Dict[int, str] = None):
        if idx_to_tag is None:
            idx_to_tag = {0: "O"}
        self.idx_to_tag = idx_to_tag

    def extract(
        self, tokens: List[str], tag_indices: List[int]
    ) -> Dict[str, List[str]]:
        result = {}
        current_type = None
        current_entity: List[str] = []

        for token, tag_idx in zip(tokens, tag_indices):
            tag = self.idx_to_tag.get(tag_idx, "O")

            if tag.startswith("B-"):
                if current_entity and current_type:
                    result.setdefault(current_type, []).append(
                        "".join(current_entity)
                    )
                current_type = tag[2:]
                current_entity = [token]
            elif tag.startswith("I-") and current_type == tag[2:]:
                current_entity.append(token)
            else:
                if current_entity and current_type:
                    result.setdefault(current_type, []).append(
                        "".join(current_entity)
                    )
                current_type = None
                current_entity = []

        if current_entity and current_type:
            result.setdefault(current_type, []).append("".join(current_entity))

        return result

    def extract_from_device_fields(
        self,
        fields: List[Dict],
        model: Optional[NERModel] = None,
        char_to_idx: Dict[str, int] = None,
        device: torch.device = None,
    ) -> List[Dict[str, List[str]]]:
        """从设备字段提取实体

        当提供model时通过模型推理获取标签序列；
        否则用启发式规则生成dummy标签用于占位测试。
        """
        results = []
        for field in fields:
            name = field.get("field_name", "") or field.get("browse_name", "")
            if not name:
                results.append({"field_name": name, "entities": {}})
                continue

            tokens = list(name)

            if model is not None and char_to_idx is not None and device is not None:
                indices = [char_to_idx.get(c, 1) for c in name]
                x = torch.tensor([indices], dtype=torch.long).to(device)
                model.eval()
                with torch.no_grad():
                    emissions, _ = model(x)
                tag_indices = model.decode(emissions)[0]
            else:
                tag_indices = [1 if i == 0 else 2 for i in range(len(tokens))]

            entities = self.extract(tokens, tag_indices)
            results.append({"field_name": name, "entities": entities})
        return results
