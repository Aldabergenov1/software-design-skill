# === clip_dataset.py ===
import numpy as np, torch

class ClipDataset(torch.utils.data.Dataset):
    """Ultrasound cine loops, vendor A. Each item: 2-second clip, (T, H, W) float32."""
    def __init__(self, paths, seconds=2.0):
        self.paths = paths
        self.n_frames = int(seconds * 30)

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, i):
        frames = np.load(self.paths[i])            # (T_total, H, W)
        start = np.random.randint(0, len(frames) - self.n_frames + 1)
        return torch.from_numpy(frames[start:start + self.n_frames])


# === temporal_model.py ===
import math

class TemporalHead(torch.nn.Module):
    def __init__(self, dim, max_frames=60):
        super().__init__()
        t = torch.arange(max_frames) / 30.0        # seconds
        self.register_buffer("time_emb", torch.stack([torch.sin(2 * math.pi * t),
                                                      torch.cos(2 * math.pi * t)], -1))
        self.proj = torch.nn.Linear(dim + 2, dim)

    def forward(self, x):                          # x: (B, T, dim)
        te = self.time_emb[: x.shape[1]].expand(x.shape[0], -1, -1)
        return self.proj(torch.cat([x, te], -1))
