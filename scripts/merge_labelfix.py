"""Replace the broken label rows with the corrected ones, keeping both on record.

The first 16 models were run with a label implementation that silently failed on
SentencePiece tokenizers and on models that do not answer at generated position 0. Those
models were re-scored for the `label` condition only, into `<slug>.labelfix.csv`. The last
four models (gemma x2, internlm, Qwen-14B) were run after the fix and already carry correct
label rows.

This merges the corrected rows into the main CSV and writes the superseded ones to
`results/raw_naive_label/` — they are not garbage, they are the evidence for how often the
standard method fails, which is a reported result.

    python scripts/merge_labelfix.py --raw results/raw
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=REPO / "results" / "raw")
    ap.add_argument("--archive", type=Path, default=REPO / "results" / "raw_naive_label")
    args = ap.parse_args()
    args.archive.mkdir(parents=True, exist_ok=True)

    fixes = sorted(args.raw.glob("*.labelfix.csv"))
    if not fixes:
        print("no .labelfix.csv files found — nothing to merge")
        return 0

    for fx in fixes:
        slug = fx.name[: -len(".labelfix.csv")]
        main_csv = args.raw / f"{slug}.csv"
        if not main_csv.exists():
            print(f"  [skip] {slug}: no main CSV")
            continue

        rows = list(csv.DictReader(main_csv.open(encoding="utf-8")))
        new_label = list(csv.DictReader(fx.open(encoding="utf-8")))
        fields = list(rows[0].keys())
        for extra in ("label_position",):
            if extra not in fields:
                fields.append(extra)

        old_label = [r for r in rows if r["condition"] == "label"]
        keep = [r for r in rows if r["condition"] != "label"]

        # Archive the superseded rows — they are the failure-rate evidence.
        arch = args.archive / f"{slug}.naive_label.csv"
        with arch.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(old_label[0].keys()))
            w.writeheader(); w.writerows(old_label)

        merged = keep + new_label
        merged.sort(key=lambda r: (int(r["item_id"]), r["condition"], int(r["replicate"] or 0)))
        with main_csv.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader(); w.writerows(merged)

        # The main manifest still describes the ORIGINAL label run. Leaving it would mean
        # the manifest and the data disagree about how the label rows were produced, which
        # defeats the point of having manifests at all.
        fxman = args.raw / f"{slug}.labelfix.manifest.json"
        mainman = args.raw / f"{slug}.manifest.json"
        if fxman.exists() and mainman.exists():
            fx_m = json.loads(fxman.read_text(encoding="utf-8"))
            mm = json.loads(mainman.read_text(encoding="utf-8"))
            mm["option_label_token_ids"] = fx_m.get("option_label_token_ids")
            mm["label_rescored"] = True
            mm["label_rescore_packages"] = fx_m.get("packages")
            mm["label_rescore_prompt_sha_first"] = fx_m.get("prompt_sha_first")
            mm["superseded_label_manifest"] = f"raw_naive_label/{slug}.labelfix.manifest.json"
            mainman.write_text(json.dumps(mm, indent=2, default=str), encoding="utf-8")
        if fxman.exists():
            shutil.move(str(fxman), str(args.archive / f"{slug}.labelfix.manifest.json"))
        fx.unlink()
        print(f"  {slug}: replaced {len(old_label)} label rows with {len(new_label)} corrected")

    print(f"\nmerged {len(fixes)} models; superseded rows archived to {args.archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
