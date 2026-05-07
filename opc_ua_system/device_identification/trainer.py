import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

logger = logging.getLogger(__name__)


class TextCNNTrainer:
    """TextCNN训练器 - 使用飞机制造和电子制造行业的设备样本训练分类器"""

    def __init__(
        self,
        model: "CharTextCNN",
        device: str = "cpu",
        learning_rate: float = 0.001,
        max_epochs: int = 100,
        early_stop_patience: int = 10,
    ):
        self.model = model.to(device)
        self.device = device
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(model.parameters(), lr=learning_rate)
        self.max_epochs = max_epochs
        self.early_stop_patience = early_stop_patience

    def train(
        self,
        train_data: torch.Tensor,
        train_labels: torch.Tensor,
        val_data: torch.Tensor = None,
        val_labels: torch.Tensor = None,
        batch_size: int = 32,
    ) -> Dict[str, List[float]]:
        train_dataset = TensorDataset(train_data, train_labels)
        train_loader = DataLoader(
            train_dataset, batch_size=batch_size, shuffle=True
        )

        if val_data is not None and val_labels is not None:
            val_dataset = TensorDataset(val_data, val_labels)
            val_loader = DataLoader(
                val_dataset, batch_size=batch_size, shuffle=False
            )
        else:
            val_loader = None

        history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}
        best_val_acc = 0.0
        patience_counter = 0

        for epoch in range(self.max_epochs):
            self.model.train()
            total_loss = 0.0
            correct = 0
            total = 0

            for batch_x, batch_y in train_loader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)

                self.optimizer.zero_grad()
                logits = self.model(batch_x)
                loss = self.criterion(logits, batch_y)
                loss.backward()
                self.optimizer.step()

                total_loss += loss.item() * batch_x.size(0)
                preds = torch.argmax(logits, dim=1)
                correct += (preds == batch_y).sum().item()
                total += batch_y.size(0)

            train_loss = total_loss / total
            train_acc = correct / total
            history["train_loss"].append(train_loss)
            history["train_acc"].append(train_acc)

            if val_loader is not None:
                val_loss, val_acc = self._evaluate(val_loader)
                history["val_loss"].append(val_loss)
                history["val_acc"].append(val_acc)

                if val_acc > best_val_acc:
                    best_val_acc = val_acc
                    patience_counter = 0
                else:
                    patience_counter += 1

                logger.info(
                    f"Epoch {epoch+1}/{self.max_epochs} | "
                    f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | "
                    f"Val Loss: {val_loss:.4f} Acc: {val_acc:.4f}"
                )

                if patience_counter >= self.early_stop_patience:
                    logger.info(f"Early stopping at epoch {epoch+1}")
                    break
            else:
                logger.info(
                    f"Epoch {epoch+1}/{self.max_epochs} | "
                    f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f}"
                )

        return history

    def _evaluate(
        self, loader: DataLoader
    ) -> Tuple[float, float]:
        self.model.eval()
        total_loss = 0.0
        correct = 0
        total = 0

        with torch.no_grad():
            for batch_x, batch_y in loader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)
                logits = self.model(batch_x)
                loss = self.criterion(logits, batch_y)

                total_loss += loss.item() * batch_x.size(0)
                preds = torch.argmax(logits, dim=1)
                correct += (preds == batch_y).sum().item()
                total += batch_y.size(0)

        return total_loss / total, correct / total

    def save_model(self, filepath: str) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.model.state_dict(), filepath)
        logger.info(f"模型已保存: {filepath}")

    def load_model(self, filepath: str) -> None:
        self.model.load_state_dict(
            torch.load(filepath, map_location=self.device)
        )
        self.model.eval()
        logger.info(f"模型已加载: {filepath}")
