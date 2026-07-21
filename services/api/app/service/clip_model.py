"""Local CLIP embedder — the only place torch / open_clip are imported.

Vendor-faithful CLIP: we run OpenAI's `ViT-B-32` with the exact OpenAI
pretrained weights, served through the maintained `open_clip_torch` runtime
(pins cleanly on fresh clones, unlike `git+openai/CLIP`). Text and image queries
map into the *same* 512-d L2-normalized space, so cosine similarity (inner
product on normalized vectors) ranks image↔image and text↔image alike.

Device is auto-detected at load time: CUDA → Apple MPS → CPU, defaulting to CPU.
No GPU is ever required (`deployment: local`, per the build plan). The heavy
imports and the ~350 MB weight download happen lazily on first use, so importing
this module (and the services that depend on it) stays cheap and network-free —
tests inject a stub embedder instead of loading the real model.
"""

import io
import logging
import threading

import numpy as np

logger = logging.getLogger(__name__)

MODEL_NAME = "ViT-B-32"
PRETRAINED = "openai"
EMBED_DIM = 512

_lock = threading.Lock()
_model = None
_preprocess = None
_tokenizer = None
_device: str | None = None


def _select_device() -> str:
    """First available of CUDA → Apple MPS → CPU. Never hard-requires a GPU."""
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _ensure_loaded() -> None:
    """Lazily load the CLIP model once, thread-safely (double-checked)."""
    global _model, _preprocess, _tokenizer, _device
    if _model is not None:
        return
    with _lock:
        if _model is not None:
            return
        import open_clip
        import torch

        device = _select_device()
        logger.info("Loading CLIP %s/%s on device=%s", MODEL_NAME, PRETRAINED, device)
        model, _, preprocess = open_clip.create_model_and_transforms(
            MODEL_NAME, pretrained=PRETRAINED
        )
        model = model.to(device).eval()
        _model = model
        _preprocess = preprocess
        _tokenizer = open_clip.get_tokenizer(MODEL_NAME)
        _device = device
        # Free the grad graph — inference only.
        torch.set_grad_enabled(False)


def current_device() -> str | None:
    """The device the model loaded onto, or None if not loaded yet."""
    return _device


def _normalize(vec: "np.ndarray") -> "np.ndarray":
    vec = vec.astype("float32").reshape(-1)
    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec = vec / norm
    return vec


def embed_image(image_bytes: bytes) -> np.ndarray:
    """Embed raw image bytes to an L2-normalized 512-d float32 vector."""
    import torch
    from PIL import Image

    _ensure_loaded()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = _preprocess(img).unsqueeze(0).to(_device)
    with torch.no_grad():
        features = _model.encode_image(tensor)
    return _normalize(features.cpu().numpy())


def embed_text(text: str) -> np.ndarray:
    """Embed a text query to an L2-normalized 512-d float32 vector."""
    import torch

    _ensure_loaded()
    tokens = _tokenizer([text]).to(_device)
    with torch.no_grad():
        features = _model.encode_text(tokens)
    return _normalize(features.cpu().numpy())
