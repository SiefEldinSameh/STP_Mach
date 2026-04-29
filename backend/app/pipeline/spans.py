"""
Span detection logic — horizontal and vertical span candidates.
Ported from the notebook span geometry functions.
"""

from app.config import SPAN_COVER
from app.pipeline.table_structure import coverage


def _find_span_candidates(raw_spans, base_cells):
    """Find horizontal span candidates from raw TSR spanning cell detections."""
    cands = []
    for sp in raw_spans:
        claimed = [c for c in base_cells if coverage(sp["box"], c["box"]) >= SPAN_COVER]
        if len(claimed) < 2:
            continue
        by_row = {}
        for c in claimed:
            by_row.setdefault(c["ri"], []).append(c)
        for ri, rc in by_row.items():
            if len(rc) < 2:
                continue
            rc.sort(key=lambda c: c["ci"])
            cands.append(
                {
                    "score": sp["score"],
                    "claimed": rc,
                    "cell_keys": frozenset((c["ri"], c["ci"]) for c in rc),
                    "row": ri,
                }
            )
    cands.sort(key=lambda s: s["score"], reverse=True)
    seen, unique = set(), []
    for sp in cands:
        if sp["cell_keys"] & seen:
            continue
        unique.append(sp)
        seen |= sp["cell_keys"]
    return unique


def _confirm_spans(candidates, cand_cell_texts):
    """Confirm horizontal spans by checking OCR text content."""
    confirmed = []
    for ci, sp in enumerate(candidates):
        ct = cand_cell_texts.get(ci, {})
        cs = sorted(sp["claimed"], key=lambda c: c["ci"])
        li = sp["claimed"].index(cs[0])
        lt = ct.get(li, "").strip()
        ot = [ct.get(sp["claimed"].index(c), "").strip() for c in cs[1:]]
        if lt and all(t == "" for t in ot):
            continue
        tc = [sp["claimed"][j] for j, t in ct.items() if t.strip()]
        if len(tc) < 2:
            continue
        tc.sort(key=lambda c: c["ci"])
        confirmed.append(
            {
                "score": sp["score"],
                "claimed": tc,
                "cell_keys": frozenset((c["ri"], c["ci"]) for c in tc),
                "row": sp["row"],
            }
        )
    return confirmed


def _find_vspan_candidates(cell_lookup, cell_texts, n_rows, n_cols, ox, oy):
    """Find vertical span candidates (column 0 only, as in the notebook)."""
    cands, col_occ = [], set()
    for ci in range(n_cols):
        if ci != 0:
            continue
        ri = 0
        while ri < n_rows:
            if (ri, ci) in col_occ:
                ri += 1
                continue
            cell = cell_lookup.get((ri, ci))
            if cell is None:
                ri += 1
                continue
            text = cell_texts.get((ri, ci), "").strip()
            if ri > 0 and text:
                group = [cell]
                look = ri + 1
                while look < n_rows:
                    below = cell_lookup.get((look, ci))
                    if below is None:
                        break
                    if cell_texts.get((look, ci), "").strip():
                        break
                    group.append(below)
                    look += 1
                if len(group) >= 2:
                    ck = frozenset((c["ri"], c["ci"]) for c in group)
                    ex1 = min(c["box"][0] for c in group)
                    ey1 = min(c["box"][1] for c in group)
                    ex2 = max(c["box"][2] for c in group)
                    ey2 = max(c["box"][3] for c in group)
                    cands.append(
                        {
                            "cell_keys": ck,
                            "rowspan": len(group),
                            "page_box": [ex1 + ox, ey1 + oy, ex2 + ox, ey2 + oy],
                        }
                    )
                    for gc in group:
                        col_occ.add((gc["ri"], gc["ci"]))
                    ri = look
                    continue
            ri += 1
    return cands
