import logging

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch未安装，空间变换模块无法使用")


class SpaceTransformer(nn.Module):
    """空间变换模块 - 将CBOW字符嵌入空间映射到ComplEx KG嵌入空间

    变换的必要性:
    - CBOW是字符语义空间
    - ComplEx嵌入是在KG空间
    - 两个空间完全不同，无法直接进行score运算

    可选变换方式:
    1. 线性变换 (Linear)
    2. 仿射变换 (Affine)
    3. 多层感知机 (MLP) - 推荐，表达力最强
    """

    def __init__(
        self,
        cbow_dim: int,
        kg_dim: int,
        hidden_dim: int = 128,
        transform_type: str = "mlp",
    ):
        super().__init__()
        self.cbow_dim = cbow_dim
        self.kg_dim = kg_dim
        self.transform_type = transform_type

        if transform_type == "linear":
            self.transform = nn.Linear(cbow_dim, kg_dim, bias=False)
        elif transform_type == "affine":
            self.transform = nn.Linear(cbow_dim, kg_dim, bias=True)
        elif transform_type == "mlp":
            self.transform = nn.Sequential(
                nn.Linear(cbow_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(hidden_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(hidden_dim, kg_dim),
            )
        else:
            raise ValueError(f"未知的变换类型: {transform_type}")

    def forward(self, cbow_vectors: torch.Tensor) -> torch.Tensor:
        """将CBOW字符嵌入向量映射到KG嵌入空间

        Args:
            cbow_vectors: CBOW字符嵌入 [batch, cbow_dim]
        Returns:
            KG空间嵌入向量 [batch, kg_dim]
        """
        return self.transform(cbow_vectors)

    def transform_entity_name(
        self,
        cbow: "CBOW",
        name_indices: list,
        char_to_idx: dict,
    ) -> torch.Tensor:
        """将单个实体名称的CBOW向量变换到KG空间

        Args:
            cbow: 训练好的CBOW模型
            name_indices: 实体名称的字符索引列表
            char_to_idx: 字符到ID的映射
        Returns:
            KG空间中的实体向量表示
        """
        cbow.eval()
        self.eval()

        with torch.no_grad():
            name_vec = cbow.get_name_embedding(name_indices)
            name_vec = name_vec.unsqueeze(0)             # [1, cbow_dim]
            kg_vec = self(name_vec)                      # [1, kg_dim]
        return kg_vec.squeeze(0)                         # [kg_dim]
