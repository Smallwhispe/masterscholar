import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def load_config(config_path: str) -> Dict[str, Any]:
    """加载YAML配置文件"""
    import yaml

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def validate_frame(frame: Dict[str, Any]) -> bool:
    """验证数据帧格式是否有效"""
    required_keys = ["frame_id", "timestamp", "node_count", "nodes"]
    return all(key in frame for key in required_keys)


def validate_kg_triple(triple: Dict[str, Any]) -> bool:
    """验证KG三元组格式"""
    required_keys = ["head", "relation", "tail"]
    return all(key in triple for key in required_keys)


def ensure_directory(dir_path: str) -> Path:
    """确保目录存在"""
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_device_metadata(metadata_path: str) -> List[Dict]:
    """加载设备元数据JSON文件"""
    path = Path(metadata_path)
    if not path.exists():
        logger.warning(f"设备元数据文件不存在: {metadata_path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
