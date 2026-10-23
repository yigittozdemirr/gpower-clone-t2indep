"""Collect oracle vectors from the real G*Power GUI (Windows UI automation, no mouse).

For every row of oracle/vectors_todo.csv: select the analysis type, type the inputs, press Calculate,
read the output fields exactly as G*Power displays them, save a screenshot of the window
(oracle/screenshots/Vxx.png) and of any error dialog (Vxx_dialog.png), and write
oracle/gpower_vectors.csv plus the raw readings in oracle/gpower_raw.jsonl.

Only G*Power's own windows are touched (matched by process). Do not use the mouse/keyboard while it runs.

    uv run --group oracle python tools/gpower_gui_collect.py [path\\to\\GPowerNT.exe]
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
import warnings
from pathlib import Path

warnings.simplefilter("ignore")  # pywinauto: 32-bit target from 64-bit Python (standard controls still work)

from pywinauto import Application  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TODO = ROOT / "oracle" / "vectors_todo.csv"
OUT_CSV = ROOT / "oracle" / "gpower_vectors.csv"
RAW = ROOT / "oracle" / "gpower_raw.jsonl"
SHOTS = ROOT / "oracle" / "screenshots"
DEFAULT_EXE = Path(os.environ.get("GPOWER_EXE", r"C:\Users\Casper\Tools\gpower-analysis\GPowerNT.exe"))

TITLE = "G*Power 3.1.9.7"
FAMILY = "t tests"
TEST = "Means: Difference between two independent means (two groups)"
MODES = {
    "a-priori": "A priori: Compute required sample size - given α, power, and effect size",
    "compromise": "Compromise: Compute implied α & power - given β/α ratio, sample size, and effect size",
    "criterion": "Criterion: Compute required α - given power, effect size, and sample size",
    "post-hoc": "Post hoc: Compute achieved power - given α, sample size, and effect size",
    "sensitivity": "Sensitivity: Compute required effect size - given α, power, and sample size",
}
INPUT_LABELS = {
    "Effect size d": "d", "α err prob": "alpha", "Power (1-β err prob)": "power",
    "Allocation ratio N2/N1": "ratio", "Sample size group 1": "n1", "Sample size group 2": "n2",
    "β/α ratio": "beta_alpha_ratio",
}
OUTPUT_LABELS = {
    "Noncentrality parameter δ": "ncp", "Critical t": "critical_t", "Df": "df",
    "Sample size group 1": "n1", "Sample size group 2": "n2", "Total sample size": "n_total",
    "Actual power": "actual_power", "Power (1-β err prob)": "power", "α err prob": "alpha",
    "β err prob": "beta", "Effect size d": "d",
}
INPUT_LABEL_IDS = range(1005, 1012)   # paired with edits 1021.. (1004 = Tail(s) → combo 1040)
INPUT_EDIT_IDS = range(1021, 1028)
OUTPUT_LABEL_IDS = range(1060, 1070)  # paired with edits 1050..
OUTPUT_EDIT_IDS = range(1050, 1060)
OUT_FIELDS = ["ncp", "critical_t", "df", "n1", "n2", "n_total", "actual_power", "power", "alpha", "beta", "d"]


def gpower_pid() -> int | None:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq GPowerNT.exe", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    pids = [int(line.split('","')[1]) for line in out.splitlines() if "GPowerNT" in line]
    return pids[0] if pids else None


class GPower:
    def __init__(self, exe: Path):
        pid = gpower_pid()
        if pid is None:
            Application(backend="win32").start(str(exe))
            time.sleep(4)
            pid = gpower_pid()
        self.app = Application(backend="win32").connect(process=pid)
        self.win = self.app.window(title=TITLE)
        self.win.wait("visible", timeout=20)
        self.ctl(1000).select(FAMILY)
        self.ctl(1001).select(TEST)

    def ctl(self, cid: int):
        return self.win.child_window(control_id=cid)

    def _pairs(self, label_ids, edit_ids) -> dict:
        # Several hidden controls share an id; only the visible one belongs to the current analysis.
        visible = {}
        for child in self.win.wrapper_object().children():
            if child.is_visible():
                visible.setdefault(child.control_id(), child)
        pairs = {}
        for lid, eid in zip(label_ids, edit_ids):
            if lid in visible and eid in visible:
                pairs[visible[lid].window_text().strip()] = visible[eid]
        return pairs

    def dialogs(self) -> list:
        return [w for w in self.app.windows() if w.class_name() == "#32770" and w.is_visible()]

    def run(self, row: dict) -> dict:
        mode = MODES[row["mode"]]
        # Re-select the analysis type so stale outputs are cleared to '?'.
        other = next(m for m in MODES.values() if m != mode)
        self.ctl(1002).select(other)
        self.ctl(1002).select(mode)
        self.ctl(1040).select("One" if row["tails"] == "1" else "Two")
        inputs = self._pairs(INPUT_LABEL_IDS, INPUT_EDIT_IDS)
        typed = {}
        for label, edit in inputs.items():
            field = INPUT_LABELS.get(label)
            if field and row.get(field, "") != "":
                edit.set_edit_text(row[field])
                typed[field] = row[field]
        self.ctl(1009).click()
        dialog_text, deadline = "", time.time() + 60
        while time.time() < deadline:
            time.sleep(0.3)
            boxes = self.dialogs()
            if boxes:
                box = boxes[0]
                dialog_text = " | ".join(c.window_text() for c in box.children() if c.window_text().strip())
                box.set_focus()
                time.sleep(0.3)
                box.capture_as_image().save(SHOTS / f"{row['id']}_dialog.png")
                buttons = [c for c in box.children() if c.class_name() == "Button"]
                if buttons:
                    buttons[0].click()
                else:
                    box.close()
                time.sleep(0.5)
                break
            outputs = self._pairs(OUTPUT_LABEL_IDS, OUTPUT_EDIT_IDS)
            if outputs and all(e.window_text() not in ("", "?") for e in outputs.values()):
                break
        outputs = {OUTPUT_LABELS.get(label, label): edit.window_text()
                   for label, edit in self._pairs(OUTPUT_LABEL_IDS, OUTPUT_EDIT_IDS).items()}
        self.win.set_focus()
        time.sleep(0.4)
        self.win.capture_as_image().save(SHOTS / f"{row['id']}.png")
        return {"id": row["id"], "mode": row["mode"], "typed": typed,
                "displayed_inputs": {INPUT_LABELS.get(l, l): e.window_text() for l, e in inputs.items()},
                "outputs": outputs, "dialog": dialog_text}


def main() -> int:
    exe = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_EXE
    SHOTS.mkdir(parents=True, exist_ok=True)
    with open(TODO, encoding="utf-8", newline="") as fh:
        todo = list(csv.DictReader(fh))
    gp = GPower(exe)
    raw, rows = [], []
    for row in todo:
        reading = gp.run(row)
        if not reading["dialog"] and all(v in ("", "?") for v in reading["outputs"].values()):
            reading = gp.run(row)  # occasionally the first Calculate after start-up is not registered
        raw.append(reading)
        outs = reading["outputs"]
        failed = reading["dialog"] or all(v in ("", "?") for v in outs.values())
        rows.append({
            **{k: row[k] for k in ["id", "mode", "tails", "d", "alpha", "power", "ratio", "n1", "n2",
                                   "beta_alpha_ratio"]},
            **{f"gp_{k}": ("" if failed else outs.get(k, "")) for k in OUT_FIELDS},
            "gp_error": reading["dialog"] or ("sonuç yok" if failed else ""),
            "screenshot": f"oracle/screenshots/{row['id']}.png",
            "note": row.get("amac", ""),
        })
        print(row["id"], json.dumps(outs, ensure_ascii=True), reading["dialog"].encode("ascii", "replace").decode())
    with open(RAW, "w", encoding="utf-8") as fh:
        for reading in raw:
            fh.write(json.dumps(reading, ensure_ascii=False) + "\n")
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} vectors -> {OUT_CSV.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
