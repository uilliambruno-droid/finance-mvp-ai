from __future__ import annotations

import json
from pathlib import Path

from datasets import load_dataset

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "data" / "hf"
TARGET_DIR = OUTPUT_DIR / "zongowo111__v2-crypto-ohlcv-data"
TARGET_DIR.mkdir(parents=True, exist_ok=True)

SPLIT = "train[:200000]"
DATASET_ID = "zongowo111/v2-crypto-ohlcv-data"

print(f"Loading {DATASET_ID} / {SPLIT} ...")
ds = load_dataset(DATASET_ID, split=SPLIT)
print(f"Loaded rows={len(ds)} cols={ds.column_names}")

out_file = TARGET_DIR / "train_200k.parquet"
ds.to_parquet(str(out_file))

summary_path = OUTPUT_DIR / "_summary_crypto_subset.json"
summary = {
    "dataset_id": DATASET_ID,
    "split": SPLIT,
    "rows": len(ds),
    "columns": ds.column_names,
    "output_file": str(out_file.relative_to(BASE_DIR)),
    "purpose": "Recorte de OHLCV cripto para contexto de mercado e análise de risco.",
}
summary_path.write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"Saved: {out_file}")
print(f"Summary: {summary_path}")
