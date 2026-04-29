"""
Table Structure Recognition - runs the TSR model on cropped table images.
Includes geometry helpers and NMS logic from the notebook.
"""

import torch

from app.config import DEVICE, SPAN_CONF_MIN, X_NMS_IOU, Y_NMS_IOU
from app.models.loader import model_store


def box_area(b):
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])


def intersection_area(a, b):
    ix1 = max(a[0], b[0])
    iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2])
    iy2 = min(a[3], b[3])
    return max(0, ix2 - ix1) * max(0, iy2 - iy1)


def coverage(span_box, cell_box):
    ca = box_area(cell_box)
    return 0.0 if ca == 0 else intersection_area(span_box, cell_box) / ca


def y_iou(b1, b2):
    inter = max(0, min(b1[3], b2[3]) - max(b1[1], b2[1]))
    union = max(b1[3], b2[3]) - min(b1[1], b2[1])
    return inter / union if union > 0 else 0.0


def y_nms(rows, iou_thresh=Y_NMS_IOU):
    rows = sorted(rows, key=lambda r: r["score"], reverse=True)
    kept = []
    for row in rows:
        if all(y_iou(row["box"], kept_row["box"]) < iou_thresh for kept_row in kept):
            kept.append(row)
    return sorted(kept, key=lambda r: r["box"][1])


def x_iou(b1, b2):
    inter = max(0, min(b1[2], b2[2]) - max(b1[0], b2[0]))
    union = max(b1[2], b2[2]) - min(b1[0], b2[0])
    return inter / union if union > 0 else 0.0


def x_nms(cols, iou_thresh=X_NMS_IOU):
    cols = sorted(cols, key=lambda c: c["score"], reverse=True)
    kept = []
    for col in cols:
        if all(x_iou(col["box"], kept_col["box"]) < iou_thresh for kept_col in kept):
            kept.append(col)
    return sorted(kept, key=lambda c: c["box"][0])


def _average_score(items):
    if not items:
        return None
    return round(sum(item["score"] for item in items) / len(items), 4)


@torch.no_grad()
def run_tsr_batch(crops):
    """Run TSR on a list of cropped table images."""
    if not crops:
        return []

    tsr_proc = model_store.tsr_proc
    tsr_model = model_store.tsr_model

    sizes = [(crop.size[1], crop.size[0]) for crop in crops]
    inp = tsr_proc(images=crops, return_tensors="pt").to(DEVICE)
    out = tsr_model(**inp)
    target_sizes = torch.tensor(sizes, device=DEVICE)
    results = tsr_proc.post_process_object_detection(
        out, threshold=0.05, target_sizes=target_sizes
    )

    all_out = []
    for res in results:
        raw_rows, raw_cols, raw_spans = [], [], []
        for score_tensor, label_tensor, box_tensor in zip(
            res["scores"], res["labels"], res["boxes"]
        ):
            name = tsr_model.config.id2label.get(label_tensor.item(), "")
            score = score_tensor.item()
            box = box_tensor.tolist()
            if name == "table row" and score > 0.30:
                raw_rows.append({"box": box, "score": score})
            elif name == "table column" and score > 0.30:
                raw_cols.append({"box": box, "score": score})
            elif name == "table spanning cell" and score >= SPAN_CONF_MIN:
                raw_spans.append({"box": box, "score": score})

        kept_rows = y_nms(raw_rows)
        kept_cols = x_nms(raw_cols)
        rows_avg = _average_score(kept_rows)
        cols_avg = _average_score(kept_cols)
        spans_avg = _average_score(raw_spans)
        metrics = [value for value in (rows_avg, cols_avg, spans_avg) if value is not None]

        all_out.append(
            {
                "rows": [row["box"] for row in kept_rows],
                "cols": [col["box"] for col in kept_cols],
                "raw_spans": raw_spans,
                "structure_confidence": {
                    "overall": round(sum(metrics) / len(metrics), 4) if metrics else None,
                    "rows_avg": rows_avg,
                    "cols_avg": cols_avg,
                    "spans_avg": spans_avg,
                },
            }
        )

    return all_out
