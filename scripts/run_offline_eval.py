from __future__ import annotations

import argparse
import json

from app.api.dependencies import get_offline_evaluation_runner
from app.core.models import TokenBudget
from app.evaluation import load_evaluation_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline evaluation for deer-rag.")
    parser.add_argument("dataset_path", help="Path to the evaluation dataset YAML file.")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--candidate-k", type=int, default=None)
    parser.add_argument("--rerank", action="store_true")
    parser.add_argument("--merge-adjacent", action="store_true", default=False)
    parser.add_argument("--compression-mode", choices=["none", "extractive"], default="none")
    parser.add_argument("--strategies", nargs="+", default=["dense", "bm25", "hybrid"])
    args = parser.parse_args()

    dataset = load_evaluation_dataset(args.dataset_path)
    result = get_offline_evaluation_runner().run_dataset(
        dataset,
        strategies=args.strategies,
        top_k=args.top_k,
        candidate_k=args.candidate_k,
        rerank=args.rerank,
        budget=TokenBudget(),
        merge_adjacent=args.merge_adjacent,
        compression_mode=args.compression_mode,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
