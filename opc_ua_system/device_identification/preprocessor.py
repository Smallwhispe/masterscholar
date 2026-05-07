import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class CharPreprocessor:
    """字符级预处理器 - 将设备字段名称拆分为字符序列"""

    def __init__(self, max_sequence_length: int = 128):
        self.max_seq_len = max_sequence_length
        self.char_to_idx: Dict[str, int] = {"<PAD>": 0, "<UNK>": 1}
        self.idx_to_char: Dict[int, str] = {0: "<PAD>", 1: "<UNK>"}
        self._next_idx = 2

    def build_vocab(self, texts: List[str]) -> None:
        """从文本列表构建字符级词表"""
        for text in texts:
            for char in text:
                if char not in self.char_to_idx:
                    self.char_to_idx[char] = self._next_idx
                    self.idx_to_char[self._next_idx] = char
                    self._next_idx += 1
        logger.info(f"字符词表构建完成，大小: {self.vocab_size}")

    @property
    def vocab_size(self) -> int:
        return len(self.char_to_idx)

    def encode(self, text: str) -> List[int]:
        """将文本编码为字符索引序列"""
        indices = []
        for char in text[:self.max_seq_len]:
            indices.append(
                self.char_to_idx.get(char, self.char_to_idx["<UNK>"])
            )
        while len(indices) < self.max_seq_len:
            indices.append(self.char_to_idx["<PAD>"])
        return indices

    def encode_batch(self, texts: List[str]) -> List[List[int]]:
        """批量编码"""
        return [self.encode(t) for t in texts]

    def decode(self, indices: List[int]) -> str:
        """将索引序列解码为文本"""
        chars = [
            self.idx_to_char.get(i, "<UNK>")
            for i in indices
            if i not in (0, 1)
        ]
        return "".join(chars)

    def save(self, filepath: str) -> None:
        """保存字符词表"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                {"char_to_idx": self.char_to_idx, "max_seq_len": self.max_seq_len},
                f,
                ensure_ascii=False,
                indent=2,
            )

    @classmethod
    def load(cls, filepath: str) -> "CharPreprocessor":
        """加载字符词表"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        preprocessor = cls(max_sequence_length=data["max_seq_len"])
        preprocessor.char_to_idx = data["char_to_idx"]
        preprocessor.idx_to_char = {v: k for k, v in data["char_to_idx"].items()}
        preprocessor._next_idx = len(preprocessor.char_to_idx)
        return preprocessor

    def preprocess_device_fields(
        self, device_metadata: List[Dict]
    ) -> Tuple[List[List[int]], List[str]]:
        """预处理设备元数据 - 提取有效字段名称并编码"""
        texts = []
        for item in device_metadata:
            field_name = item.get("field_name", "")
            browse_name = item.get("browse_name", "")
            combined = field_name or browse_name
            if combined:
                texts.append(combined)
        encoded = self.encode_batch(texts)
        return encoded, texts
