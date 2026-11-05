"""Export the SST-2 validation split (872 sentences) to JSON for SST2_VALIDATION_FILE.

Lets an instance evaluate on SST-2 without the `datasets` library (and pyarrow) in memory at runtime; the hosted
demo image runs this once at build time.

    python scripts/export_sst2.py out/sst2_validation.json
"""

import json
import sys
from pathlib import Path


def main() -> int:
    from datasets import load_dataset

    out = Path(sys.argv[1] if len(sys.argv) > 1 else "sst2_validation.json")
    split = load_dataset("stanfordnlp/sst2", split="validation")
    names = split.features["label"].names
    rows = [{"sentence": r["sentence"], "label": names[r["label"]]} for r in split]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows), encoding="utf-8")
    print(f"wrote {len(rows)} sentences to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
