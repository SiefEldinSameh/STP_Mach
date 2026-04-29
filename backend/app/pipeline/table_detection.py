"""
Table Detection — runs the DETR-based TD model on a page image.
"""

import torch
from app.config import DEVICE, TD_CONF
from app.models.loader import model_store


@torch.no_grad()
def run_td(page):
    """Detect tables in a PIL image. Returns sorted list of [x1,y1,x2,y2] boxes."""
    if model_store.td_model is None or model_store.td_proc is None:
        err = getattr(model_store, "load_error", None) or "TD model not initialized"
        raise RuntimeError(err)
    W, H = page.size
    td_proc = model_store.td_proc
    td_model = model_store.td_model

    inp = td_proc(images=page, return_tensors="pt").to(DEVICE)
    out = td_model(**inp)
    res = td_proc.post_process_object_detection(
        out,
        threshold=TD_CONF,
        target_sizes=torch.tensor([[H, W]], device=DEVICE),
    )[0]

    detections = sorted(
        [
            (box.tolist(), score.item())
            for box, score in zip(res["boxes"], res["scores"])
        ],
        key=lambda item: item[0][1],
    )
    boxes = [box for box, _ in detections]
    scores = [score for _, score in detections]
    return boxes, scores
