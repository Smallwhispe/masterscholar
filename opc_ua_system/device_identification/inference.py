import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch

logger = logging.getLogger(__name__)


class DeviceIdentifier:
    """设备类型识别推理器

    整体流程：
    1. 加载预训练的字符级TextCNN模型
    2. 接收OPC UA数据帧中的设备元数据
    3. 对字段名称进行字符级编码
    4. TextCNN推理 → 输出设备类型 (IR/CNC/SOM/SCM/PM/PW)
    5. NER提取实体（实体类别由训练数据标签集决定）
    """

    def __init__(
        self,
        model: "CharTextCNN",
        preprocessor: "CharPreprocessor",
        ner_model: Optional["NERModel"] = None,
        ner_tag_mapping: Optional[Dict[int, str]] = None,
        device: str = "cpu",
    ):
        self.model = model.to(device)
        self.preprocessor = preprocessor
        self.ner_model = ner_model
        self.ner_tag_mapping = ner_tag_mapping or {0: "O"}
        if ner_model:
            self.ner_model = ner_model.to(device)
        self.device = device
        self.model.eval()
        if self.ner_model:
            self.ner_model.eval()

        from .textcnn import DEVICE_TYPE_LABELS
        self.labels = DEVICE_TYPE_LABELS

    @classmethod
    def from_pretrained(
        cls,
        model_path: str,
        preprocessor_path: str,
        ner_model_path: str = None,
        ner_tag_mapping_path: str = None,
        device: str = "cpu",
    ) -> "DeviceIdentifier":
        from .preprocessor import CharPreprocessor
        from .textcnn import CharTextCNN

        preprocessor = CharPreprocessor.load(preprocessor_path)
        model = CharTextCNN(
            vocab_size=preprocessor.vocab_size,
            num_classes=6,
            dropout_rate=0.5,
        )
        model.load_state_dict(
            torch.load(model_path, map_location=device)
        )
        model.eval()

        ner_model = None
        ner_tag_mapping = None

        if ner_model_path and ner_tag_mapping_path:
            tag_mapping_data = json.load(open(ner_tag_mapping_path, "r"))
            ner_tag_mapping = {
                int(k): v for k, v in tag_mapping_data.get("idx_to_tag", {}).items()
            }
            num_tags = tag_mapping_data.get("num_tags", len(ner_tag_mapping) or 1)

            from .ner import NERModel
            ner_model = NERModel(
                num_entity_tags=num_tags,
                vocab_size=preprocessor.vocab_size,
            )
            ner_model.load_state_dict(
                torch.load(ner_model_path, map_location=device)
            )
            ner_model.eval()

        return cls(model, preprocessor, ner_model, ner_tag_mapping, device)

    def identify_from_frame(
        self, frame: Dict
    ) -> Dict:
        device_metadata = frame.get("device_metadata", [])
        if not device_metadata:
            return {
                "device_type": "Unknown",
                "device_name": "Unknown",
                "confidence": 0.0,
                "entities": {},
            }

        encoded, field_names = self.preprocessor.preprocess_device_fields(
            device_metadata
        )
        if not field_names:
            return {
                "device_type": "Unknown",
                "device_name": "Unknown",
                "confidence": 0.0,
                "entities": {},
            }

        tensor_data = torch.tensor(encoded, dtype=torch.long).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor_data)
            probs = torch.softmax(logits, dim=1)
            aggregated = probs.mean(dim=0)
            pred_idx = torch.argmax(aggregated).item()
            confidence = aggregated[pred_idx].item()

        device_type = self.labels.get(pred_idx, "Unknown")
        from .textcnn import get_device_type_name
        device_name = get_device_type_name(device_type)

        entities = {}
        if self.ner_model:
            from .ner import EntityExtractor
            extractor = EntityExtractor(self.ner_tag_mapping)
            entities_list = extractor.extract_from_device_fields(
                device_metadata,
                model=self.ner_model,
                char_to_idx=self.preprocessor.char_to_idx,
                device=self.device,
            )
            for e in entities_list:
                for k, v in e.get("entities", {}).items():
                    if k not in entities:
                        entities[k] = []
                    entities[k].extend(v)

        result = {
            "device_type": device_type,
            "device_name": device_name,
            "confidence": confidence,
            "entities": entities,
            "field_count": len(field_names),
        }
        logger.info(f"设备类型识别结果: {result}")
        return result

    def identify_batch(
        self, frames: List[Dict]
    ) -> List[Dict]:
        return [self.identify_from_frame(frame) for frame in frames]
