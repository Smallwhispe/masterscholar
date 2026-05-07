import logging
from typing import List, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class CharTextCNN(nn.Module):
    """字符级TextCNN分类器 - 用于工业设备类型识别

    采用字符级卷积的原因：
    - 工业设备字段名称通常是缩写组合，词级语义不清晰
    - 词向量难以覆盖大量专业缩写(如IR, CNC, SOM, SCM, PM, PW)
    - 字符级方法可以直接利用每个字符的信息

    预处理流程:
    1. 拆分字符序列
    2. 多通道卷积提取局部特征
    3. 池化固定输出长度
    4. Softmax分类 → 输出候选实体

    识别精度 >90%，为后续建模提供基础语义单元。
    """

    def __init__(
        self,
        vocab_size: int,
        num_classes: int = 6,
        char_embedding_dim: int = 64,
        num_filters: int = 128,
        kernel_sizes: List[int] = None,
        dropout_rate: float = 0.5,
    ):
        super().__init__()
        if kernel_sizes is None:
            kernel_sizes = [2, 3, 4, 5]

        self.char_embedding = nn.Embedding(
            vocab_size, char_embedding_dim, padding_idx=0
        )
        self.convs = nn.ModuleList(
            [
                nn.Conv1d(
                    in_channels=char_embedding_dim,
                    out_channels=num_filters,
                    kernel_size=k,
                )
                for k in kernel_sizes
            ]
        )
        self.dropout = nn.Dropout(dropout_rate)
        self.fc = nn.Linear(num_filters * len(kernel_sizes), num_classes)

    def forward(
        self, x: torch.Tensor
    ) -> torch.Tensor:
        """
        Args:
            x: 字符索引序列 [batch_size, seq_len]
        Returns:
            类别logits [batch_size, num_classes]
        """
        x = self.char_embedding(x)           # [B, L, D]
        x = x.permute(0, 2, 1)              # [B, D, L]

        conv_outputs = []
        for conv in self.convs:
            conv_out = F.relu(conv(x))       # [B, F, L-k+1]
            pooled = F.max_pool1d(
                conv_out, conv_out.size(2)
            ).squeeze(2)                     # [B, F]
            conv_outputs.append(pooled)

        x = torch.cat(conv_outputs, dim=1)   # [B, F*len(kernels)]
        x = self.dropout(x)
        logits = self.fc(x)                  # [B, num_classes]

        return logits

    def predict(self, x: torch.Tensor) -> torch.Tensor:
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            probs = F.softmax(logits, dim=1)
            predictions = torch.argmax(probs, dim=1)
        return predictions


DEVICE_TYPE_LABELS = {
    0: "IR",   # Industrial Robot (工业机器人)
    1: "CNC",  # CNC Machine (数控机床)
    2: "SOM",  # Sorting Machine (分拣机)
    3: "SCM",  # Scribing Machine (划线机)
    4: "PM",   # Pick-and-Place Machine (贴片机)
    5: "PW",   # Press Welder (压焊机)
}

DEVICE_TYPE_NAMES = {
    "IR": "Industrial Robot",
    "CNC": "CNC Machine",
    "SOM": "Sorting Machine",
    "SCM": "Scribing Machine",
    "PM": "Pick-and-Place Machine",
    "PW": "Press Welder",
}


def get_device_type_name(label: str) -> str:
    return DEVICE_TYPE_NAMES.get(label, "Unknown")


def get_label_info(idx: int) -> dict:
    label = DEVICE_TYPE_LABELS.get(idx, "Unknown")
    return {"index": idx, "label": label, "name": DEVICE_TYPE_NAMES.get(label, "Unknown")}
