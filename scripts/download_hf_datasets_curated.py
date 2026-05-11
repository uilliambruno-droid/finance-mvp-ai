from __future__ import annotations

import json
from pathlib import Path

from datasets import load_dataset

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "data" / "hf"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DATASETS = [
    {
        "id": "atrost/financial_phrasebank",
        "config": None,
        "splits": ["train", "validation", "test"],
        "max_rows": None,
        "purpose": "Sentimento financeiro com splits prontos.",
    },
    {
        "id": "virattt/financial-qa-10K",
        "config": None,
        "splits": ["train"],
        "max_rows": None,
        "purpose": "Q&A financeiro de alta cobertura para respostas do assistente.",
    },
    {
        "id": "OpenFinAL/Financial_Question_Answering",
        "config": None,
        "splits": ["train"],
        "max_rows": None,
        "purpose": "Conversas e FAQ financeiro para tom de atendimento.",
    },
    {
        "id": "zeroshot/twitter-financial-news-sentiment",
        "config": None,
        "splits": ["train", "validation"],
        "max_rows": None,
        "purpose": "Sentimento de notícias financeiras em linguagem de mercado.",
    },
    {
        "id": "paperswithbacktest/Stocks-Daily-Price",
        "config": None,
        "splits": ["train"],
        "max_rows": 300000,
        "purpose": "Série histórica diária de ações para contexto de mercado global.",
    },
]

summary: list[dict] = []

for item in DATASETS:
    dataset_id = item["id"]
    config = item["config"]
    splits = item["splits"]
    max_rows = item["max_rows"]

    target_dir = OUTPUT_DIR / dataset_id.replace("/", "__")
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== {dataset_id} ===")

    loaded_splits = []
    for split in splits:
        try:
            ds = load_dataset(dataset_id, config, split=split)
            original_rows = len(ds)
            if max_rows and original_rows > max_rows:
                ds = ds.select(range(max_rows))

            out_file = target_dir / f"{split}.parquet"
            ds.to_parquet(str(out_file))

            loaded_splits.append(
                {
                    "split": split,
                    "rows": len(ds),
                    "original_rows": original_rows,
                    "columns": ds.column_names,
                    "output_file": str(out_file.relative_to(BASE_DIR)),
                }
            )
            print(f"ok split={split} rows={len(ds)} cols={len(ds.column_names)}")
        except Exception as exc:
            loaded_splits.append({"split": split, "error": str(exc)})
            print(f"fail split={split}: {exc}")

    summary.append(
        {
            "dataset_id": dataset_id,
            "config": config,
            "purpose": item["purpose"],
            "splits": loaded_splits,
        }
    )

summary_file = OUTPUT_DIR / "_summary_curated.json"
summary_file.write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"\nResumo curado salvo em: {summary_file}")
