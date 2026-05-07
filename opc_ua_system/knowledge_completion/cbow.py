from typing import Dict, List

try:
    import torch
    import torch.nn as nn

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class CBOW(nn.Module):
    """CBOW字符嵌入模型 - 对实体名字做字符级词嵌入

    流程:
    1. 把所有实体名字组成集合 W = {w1, w2, ..., wN}
    2. 对每个名字 wN，拆成字符序列 CN = {c1, ..., cm}
    3. 用CBOW模型训练字符向量：给定上下文字符，预测中间字符
    4. 对于实体名字 wn，把其所有字符的embedding做平均

    最终得到每个实体名字的字符级向量表示，用于和KG嵌入空间的映射。
    """

    def __init__(
        self,
        vocab_size: int,
        embedding_dim: int = 64,
        window_size: int = 3,
    ):
        super().__init__()
        self.embedding_dim = embedding_dim
        self.window_size = window_size
        self.char_embedding = nn.Embedding(vocab_size, embedding_dim)
        self.linear = nn.Linear(embedding_dim, vocab_size)

    def forward(
        self, context_chars: torch.Tensor
    ) -> torch.Tensor:
        """
        Args:
            context_chars: 上下文字符索引 [B, 2*window_size]
        Returns:
            目标字符的logits [B, vocab_size]
        """
        embeds = self.char_embedding(context_chars)   # [B, 2*W, D]
        context_vec = embeds.mean(dim=1)              # [B, D]
        logits = self.linear(context_vec)              # [B, V]
        return logits

    def get_char_embedding(
        self, char_ids: torch.Tensor
    ) -> torch.Tensor:
        """获取字符嵌入"""
        return self.char_embedding(char_ids)

    def get_name_embedding(
        self, name_indices: List[int]
    ) -> torch.Tensor:
        """通过平均字符嵌入获取实体名称的嵌入向量"""
        if not name_indices:
            return torch.zeros(self.embedding_dim)

        indices = torch.tensor(name_indices, dtype=torch.long)
        with torch.no_grad():
            char_vecs = self.char_embedding(indices)
            name_vec = char_vecs.mean(dim=0)
        return name_vec

    def encode_names(
        self,
        name_sequences: List[List[int]],
    ) -> torch.Tensor:
        """批量编码实体名称

        Args:
            name_sequences: 每个实体名对应的字符索引列表
        Returns:
            实体名称嵌入矩阵 [num_entities, embedding_dim]
        """
        embeddings = []
        for seq in name_sequences:
            vec = self.get_name_embedding(seq)
            embeddings.append(vec.unsqueeze(0))
        return torch.cat(embeddings, dim=0)
