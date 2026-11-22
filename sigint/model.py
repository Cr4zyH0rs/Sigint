"""Mode classifier: torchvision ResNet-18 with a 1-channel stem.

torchvision.models.resnet18 (He et al., "Deep Residual Learning for Image
Recognition", CVPR 2016; https://pytorch.org/vision/stable/models/generated/torchvision.models.resnet18.html).
Trained from scratch here because the pretrained-weight download host is not
reachable from this test environment.
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torchvision

from .synth import CLASSES


def build_model(n_classes: int = len(CLASSES), in_ch: int = 1) -> nn.Module:
    m = torchvision.models.resnet18(weights=None, num_classes=n_classes)
    m.conv1 = nn.Conv2d(in_ch, 64, kernel_size=7, stride=2, padding=3, bias=False)
    return m


class Classifier:
    def __init__(self, path: str | None = None, device="cpu"):
        self.device = device
        state = torch.load(path, map_location=device) if path else None
        # the number of classes comes from the checkpoint (v1 = 6 classes, batch 2 = 13)
        n = state["fc.weight"].shape[0] if state else len(CLASSES)
        # 1 input channel = features.spectrogram; 3 = features.spectrogram_mc
        self.in_ch = state["conv1.weight"].shape[1] if state else 1
        self.model = build_model(n, self.in_ch).to(device)
        if state:
            self.model.load_state_dict(state)
        self.model.eval()

    def featurize(self, x12k: np.ndarray) -> np.ndarray:
        from . import features
        return features.spectrogram_mc(x12k) if self.in_ch == 3 else features.spectrogram(x12k)

    @torch.no_grad()
    def predict(self, spec: np.ndarray):
        t = torch.from_numpy(np.asarray(spec, np.float32))
        t = (t[None, None] if t.ndim == 2 else t[None]).to(self.device)
        p = torch.softmax(self.model(t), 1)[0].cpu().numpy()
        i = int(p.argmax())
        return CLASSES[i], float(p[i]), p
