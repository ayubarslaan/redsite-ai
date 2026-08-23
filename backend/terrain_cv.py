"""
HiRISE Terrain Classification using PyTorch CNN
Classifies Mars terrain into: safe, rocky, dune, cratered
"""


import torch
import torch.nn as nn
from torchvision import models, transforms
from typing import List, Tuple
from pathlib import Path

# ---------------------------------------------------------------------------
# Model architecture
# ---------------------------------------------------------------------------

class TerrainClassifier(nn.Module):
    """
    ResNet-18 backbone with custom classification head for Mars terrain.

    Classes:
        0: safe — flat, low rock abundance, suitable for landing
        1: rocky — high rock abundance, landing hazard
        2: dune — sand dunes, mobility hazard
        3: cratered — cratered terrain, uneven surface
    """

    NUM_CLASSES = 4
    CLASS_NAMES = ["safe", "rocky", "dune", "cratered"]

    def __init__(self, num_classes: int = NUM_CLASSES, pretrained: bool = True):
        super().__init__()
        self.backbone = models.resnet18(weights="IMAGENET1K_V1" if pretrained else None)

        # Replace final FC layer
        in_features = self.backbone.fc.in_features
        self.backbone.fc = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(in_features, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.backbone(x)

# ---------------------------------------------------------------------------
# Inference pipeline
# ---------------------------------------------------------------------------

class TerrainInference:
    """Production inference pipeline for HiRISE terrain classification."""

    INPUT_SIZE = (256, 256)

    def __init__(self, model_path: Path = None, device: str = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = TerrainClassifier(pretrained=False)

        if model_path and model_path.exists():
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))

        self.model.to(self.device)
        self.model.eval()

        self.transform = transforms.Compose([
            transforms.Resize(self.INPUT_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

    def predict(self, image) -> Tuple[str, float]:
        """
        Predict terrain class for a single image.

        Args:
            image: PIL Image or tensor

        Returns:
            (class_name, confidence)
        """
        tensor = self.transform(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1)
            confidence, predicted = torch.max(probs, 1)

        class_idx = predicted.item()
        class_name = TerrainClassifier.CLASS_NAMES[class_idx]
        conf = confidence.item()

        return class_name, conf

    def predict_batch(self, images: List) -> List[Tuple[str, float]]:
        """Predict terrain class for a batch of images."""
        tensors = torch.stack([self.transform(img) for img in images]).to(self.device)

        with torch.no_grad():
            logits = self.model(tensors)
            probs = torch.softmax(logits, dim=1)
            confidences, predicted = torch.max(probs, dim=1)

        results = []
        for idx, conf in zip(predicted, confidences):
            results.append((
                TerrainClassifier.CLASS_NAMES[idx.item()],
                conf.item()
            ))
        return results

# ---------------------------------------------------------------------------
# Training scaffold
# ---------------------------------------------------------------------------

def get_training_transforms():
    """Data augmentation for training."""
    return transforms.Compose([
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.Resize((256, 256)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

# Example training loop (simplified)
# def train_model(model, dataloader, epochs=10, lr=1e-4):
#     optimizer = torch.optim.Adam(model.parameters(), lr=lr)
#     criterion = nn.CrossEntropyLoss()
#     for epoch in range(epochs):
#         for images, labels in dataloader:
#             optimizer.zero_grad()
#             outputs = model(images)
#             loss = criterion(outputs, labels)
#             loss.backward()
#             optimizer.step()
#     return model
