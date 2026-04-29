"""
Full inference pipeline orchestrator.
Ported from the notebook's run_pipeline_submission() function.
Accepts an image or PDF and returns structured table data.
"""

import logging
import os
import time
from typing import Callable, List, Optional

import pymupdf
from PIL import Image

from app.config import IMG_EXTENSIONS, PDF_EXTENSIONS, TD_PAD
from app.pipeline.ocr import _blank, predict_text_batch, safe_crop
from app.pipeline.spans import _confirm_spans, _find_span_candidates, _find_vspan_candidates
from app.pipeline.table_detection import run_td
from app.pipeline.table_structure import run_tsr_batch

logger = logging.getLogger(__name__)


def _load_images_from_file(file_path: str) -> List[Image.Image]:
    """Load images from an image file or multi-page PDF."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in PDF_EXTENSIONS:
        doc = pymupdf.open(file_path)
        images = []
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            images.append(img)
        doc.close()
        return images
    if ext in IMG_EXTENSIONS:
        return [Image.open(file_path).convert("RGB")]
    raise ValueError(f"Unsupported file type: {ext}")


def _round_stage_timings(stage_timings: dict[str, float]) -> dict[str, int]:
    return {stage: int(round(value)) for stage, value in stage_timings.items()}


def _save_table_crop(
    crop: Image.Image,
    output_dir: Optional[str],
    page_idx: int,
    table_id: int,
) -> Optional[str]:
    if not output_dir:
        return None

    crops_dir = os.path.join(output_dir, "crops")
    os.makedirs(crops_dir, exist_ok=True)
    filename = f"page-{page_idx + 1}-table-{table_id + 1}.png"
    crop_path = os.path.join(crops_dir, filename)
    crop.save(crop_path)
    return f"/outputs/{os.path.basename(output_dir)}/crops/{filename}"


def run_pipeline_for_page(
    page: Image.Image,
    page_idx: int,
    output_dir: Optional[str] = None,
    stage_callback: Optional[Callable[[str], None]] = None,
) -> dict:
    """Run the full pipeline on a single page image."""
    width, height = page.size
    start_time = time.time()
    stage_timings = {"table_detection": 0.0, "table_structure": 0.0, "ocr": 0.0}

    if stage_callback:
        stage_callback("table_detection")
    td_start = time.time()
    td_boxes, td_scores = run_td(page)
    stage_timings["table_detection"] = (time.time() - td_start) * 1000
    if not td_boxes:
        latency_ms = int((time.time() - start_time) * 1000)
        stage_timings_ms = _round_stage_timings(stage_timings)
        stage_timings_ms["total"] = latency_ms
        return {"tables": [], "latency_ms": latency_ms, "stage_timings_ms": stage_timings_ms}

    pad_boxes = []
    table_crops = []
    for tx1, ty1, tx2, ty2 in td_boxes:
        cx1, cy1 = max(0, tx1 - TD_PAD), max(0, ty1 - TD_PAD)
        cx2, cy2 = min(width, tx2 + TD_PAD), min(height, ty2 + TD_PAD)
        pad_boxes.append((cx1, cy1, cx2, cy2))
        table_crops.append(page.crop((cx1, cy1, cx2, cy2)))

    if stage_callback:
        stage_callback("table_structure")
    tsr_start = time.time()
    tsr_results = run_tsr_batch(table_crops)
    stage_timings["table_structure"] = (time.time() - tsr_start) * 1000

    tables = []
    for t_idx, (
        (tx1, ty1, tx2, ty2),
        (cx1, cy1, cx2, cy2),
        crop,
        tsr_result,
    ) in enumerate(zip(td_boxes, pad_boxes, table_crops, tsr_results)):
        rows = tsr_result["rows"]
        cols = tsr_result["cols"]
        raw_spans = tsr_result["raw_spans"]
        if not rows or not cols:
            continue

        crop_width, crop_height = crop.size
        nr, nc = len(rows), len(cols)
        cells = []
        for ri, row in enumerate(rows):
            for ci, col in enumerate(cols):
                ix1 = max(row[0], col[0])
                iy1 = max(row[1], col[1])
                ix2 = min(row[2], col[2])
                iy2 = min(row[3], col[3])
                if ix2 <= ix1 or iy2 <= iy1:
                    continue
                if ci == nc - 1:
                    ix2 = min(crop_width, ix2 + 10)
                cells.append({"ri": ri, "ci": ci, "box": [ix1, iy1, ix2, iy2]})

        tables.append(
            {
                "t_idx": t_idx,
                "td_box": (tx1, ty1, tx2, ty2),
                "td_score": td_scores[t_idx] if t_idx < len(td_scores) else 0.0,
                "ox": cx1,
                "oy": cy1,
                "nr": nr,
                "nc": nc,
                "crop_width": crop_width,
                "crop_height": crop_height,
                "crop": crop,
                "cells": cells,
                "lookup": {(cell["ri"], cell["ci"]): cell for cell in cells},
                "raw_spans": raw_spans,
                "structure_confidence": tsr_result["structure_confidence"],
            }
        )

    if not tables:
        latency_ms = int((time.time() - start_time) * 1000)
        stage_timings_ms = _round_stage_timings(stage_timings)
        stage_timings_ms["total"] = latency_ms
        return {"tables": [], "latency_ms": latency_ms, "stage_timings_ms": stage_timings_ms}

    if stage_callback:
        stage_callback("ocr")
    ocr_start = time.time()

    r1_crops, r1_meta, table_cands = [], [], []
    for ti, table_data in enumerate(tables):
        cands = _find_span_candidates(table_data["raw_spans"], table_data["cells"])
        table_cands.append(cands)
        for si, span in enumerate(cands):
            for cj, cell in enumerate(span["claimed"]):
                page_box = [
                    cell["box"][0] + table_data["ox"],
                    cell["box"][1] + table_data["oy"],
                    cell["box"][2] + table_data["ox"],
                    cell["box"][3] + table_data["oy"],
                ]
                img = safe_crop(page, page_box, width, height)
                r1_crops.append(img if img else _blank())
                r1_meta.append((ti, si, cj, img is not None))

    r1_texts = predict_text_batch(r1_crops)

    cand_ctexts = [{} for _ in tables]
    for (ti, si, cj, valid), text in zip(r1_meta, r1_texts):
        cand_ctexts[ti].setdefault(si, {})[cj] = text if valid else ""

    r2_crops, r2_meta, table_confirmed = [], [], []
    for ti, table_data in enumerate(tables):
        confirmed = _confirm_spans(table_cands[ti], cand_ctexts[ti])
        table_confirmed.append(confirmed)
        col_occ = set()
        for span in confirmed:
            col_occ |= span["cell_keys"]
        table_data["col_occ"] = col_occ

        for si, span in enumerate(confirmed):
            ex1 = min(cell["box"][0] for cell in span["claimed"])
            ey1 = min(cell["box"][1] for cell in span["claimed"])
            ex2 = max(cell["box"][2] for cell in span["claimed"])
            ey2 = max(cell["box"][3] for cell in span["claimed"])
            page_box = [
                ex1 + table_data["ox"],
                ey1 + table_data["oy"],
                ex2 + table_data["ox"],
                ey2 + table_data["oy"],
            ]
            img = safe_crop(page, page_box, width, height)
            r2_crops.append(img if img else _blank())
            r2_meta.append(("span", ti, si))

        for cell in table_data["cells"]:
            if (cell["ri"], cell["ci"]) in col_occ:
                continue
            page_box = [
                cell["box"][0] + table_data["ox"],
                cell["box"][1] + table_data["oy"],
                cell["box"][2] + table_data["ox"],
                cell["box"][3] + table_data["oy"],
            ]
            img = safe_crop(page, page_box, width, height)
            r2_crops.append(img if img else _blank())
            r2_meta.append(("cell", ti, cell["ri"], cell["ci"]))

    r2_texts = predict_text_batch(r2_crops)

    span_texts = [{} for _ in tables]
    cell_texts = [{} for _ in tables]
    for meta, text in zip(r2_meta, r2_texts):
        if meta[0] == "span":
            span_texts[meta[1]][meta[2]] = text
        else:
            cell_texts[meta[1]][(meta[2], meta[3])] = text

    r3_crops, r3_meta, table_vcands = [], [], []
    for ti, table_data in enumerate(tables):
        vcands = _find_vspan_candidates(
            table_data["lookup"],
            cell_texts[ti],
            table_data["nr"],
            table_data["nc"],
            table_data["ox"],
            table_data["oy"],
        )
        table_vcands.append(vcands)
        for vi, vspan in enumerate(vcands):
            img = safe_crop(page, vspan["page_box"], width, height)
            r3_crops.append(img if img else _blank())
            r3_meta.append((ti, vi))

    r3_texts = predict_text_batch(r3_crops)

    vspan_texts = [{} for _ in tables]
    for (ti, vi), text in zip(r3_meta, r3_texts):
        vspan_texts[ti][vi] = text

    stage_timings["ocr"] = (time.time() - ocr_start) * 1000

    tables_out = []
    for ti, table_data in enumerate(tables):
        tx1, ty1, tx2, ty2 = table_data["td_box"]
        col_occ = table_data["col_occ"]
        row_occ = set()
        for vspan in table_vcands[ti]:
            row_occ |= vspan["cell_keys"]
        all_occ = col_occ | row_occ

        out_cells = []

        for cell in table_data["cells"]:
            pos = (cell["ri"], cell["ci"])
            if pos in all_occ:
                continue
            page_box = [
                cell["box"][0] + table_data["ox"],
                cell["box"][1] + table_data["oy"],
                cell["box"][2] + table_data["ox"],
                cell["box"][3] + table_data["oy"],
            ]
            out_cells.append(
                {
                    "bbox": [int(value) for value in page_box],
                    "row": cell["ri"],
                    "col": cell["ci"],
                    "rowspan": 1,
                    "colspan": 1,
                    "text": cell_texts[ti].get(pos, ""),
                }
            )

        for si, span in enumerate(table_confirmed[ti]):
            span_keys = sorted(span["cell_keys"])
            ex1 = min(cell["box"][0] for cell in span["claimed"])
            ey1 = min(cell["box"][1] for cell in span["claimed"])
            ex2 = max(cell["box"][2] for cell in span["claimed"])
            ey2 = max(cell["box"][3] for cell in span["claimed"])
            page_box = [
                ex1 + table_data["ox"],
                ey1 + table_data["oy"],
                ex2 + table_data["ox"],
                ey2 + table_data["oy"],
            ]
            out_cells.append(
                {
                    "bbox": [int(value) for value in page_box],
                    "row": min(row for row, _ in span_keys),
                    "col": min(col for _, col in span_keys),
                    "rowspan": 1,
                    "colspan": len(sorted({col for _, col in span_keys})),
                    "text": span_texts[ti].get(si, ""),
                }
            )

        for vi, vspan in enumerate(table_vcands[ti]):
            span_keys = sorted(vspan["cell_keys"])
            out_cells.append(
                {
                    "bbox": [int(value) for value in vspan["page_box"]],
                    "row": min(row for row, _ in span_keys),
                    "col": min(col for _, col in span_keys),
                    "rowspan": vspan["rowspan"],
                    "colspan": 1,
                    "text": vspan_texts[ti].get(vi, ""),
                }
            )

        out_cells.sort(key=lambda cell: (cell["row"], cell["col"]))
        crop_url = _save_table_crop(table_data["crop"], output_dir, page_idx, table_data["t_idx"])
        tables_out.append(
            {
                "table_id": table_data["t_idx"],
                "bbox": [int(tx1), int(ty1), int(tx2), int(ty2)],
                "crop_url": crop_url,
                "detection_confidence": round(table_data.get("td_score", 0.0), 4),
                "structure_confidence": table_data["structure_confidence"],
                "cells": out_cells,
            }
        )

    latency_ms = int((time.time() - start_time) * 1000)
    stage_timings_ms = _round_stage_timings(stage_timings)
    stage_timings_ms["total"] = latency_ms
    return {"tables": tables_out, "latency_ms": latency_ms, "stage_timings_ms": stage_timings_ms}


def run_pipeline(
    file_path: str,
    output_dir: Optional[str] = None,
    display_filename: Optional[str] = None,
    stage_callback: Optional[Callable[[str], None]] = None,
) -> dict:
    """Run the full pipeline on a file."""
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    images = _load_images_from_file(file_path)
    all_pages = []
    total_latency = 0
    total_stage_timings = {"table_detection": 0, "table_structure": 0, "ocr": 0, "total": 0}

    for page_idx, page_img in enumerate(images):
        try:
            page_result = run_pipeline_for_page(
                page_img,
                page_idx,
                output_dir=output_dir,
                stage_callback=stage_callback,
            )
            page_stage_timings = page_result.get("stage_timings_ms", {})
            for stage in total_stage_timings:
                total_stage_timings[stage] += page_stage_timings.get(stage, 0)

            all_pages.append(
                {
                    "page": page_idx,
                    "tables": page_result["tables"],
                    "latency_ms": page_result["latency_ms"],
                    "stage_timings_ms": page_stage_timings,
                    "status": "success",
                    "error": None,
                }
            )
            total_latency += page_result["latency_ms"]
        except Exception as exc:
            logger.exception("Error processing page %d", page_idx)
            all_pages.append(
                {
                    "page": page_idx,
                    "tables": [],
                    "latency_ms": 0,
                    "stage_timings_ms": {
                        "table_detection": 0,
                        "table_structure": 0,
                        "ocr": 0,
                        "total": 0,
                    },
                    "status": "error",
                    "error": str(exc),
                }
            )

    if stage_callback:
        stage_callback("finalizing")

    return {
        "filename": display_filename or os.path.basename(file_path),
        "pages": all_pages,
        "total_latency_ms": total_latency,
        "stage_timings_ms": total_stage_timings,
    }
