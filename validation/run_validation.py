"""python validation/run_validation.py build   -> writes validation_sample.csv
python validation/run_validation.py score   -> reads validation_sample.csv
                                                 (after manual labeling) and
                                                 writes validation_summary.md
Run `python -m src.main` at least once first so the classification cache
exists.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import analysis, config, data_cleaning, data_loader, validation  # noqa: E402

VALIDATION_DIR = Path(__file__).resolve().parent
SAMPLE_PATH = VALIDATION_DIR / "validation_sample.csv"
RESULTS_PATH = VALIDATION_DIR / "validation_results.csv"
SUMMARY_PATH = VALIDATION_DIR / "validation_summary.md"


def cmd_build():
    cache_path = config.OUTPUT_DIR / "classification_cache.json"
    if not cache_path.exists():
        print("No classification cache found -- run `python -m src.main` first.")
        sys.exit(1)
    cache = json.loads(cache_path.read_text(encoding="utf-8"))

    tickets = data_cleaning.clean_tickets(data_loader.load_tickets())
    tickets = analysis.add_effective_reason_code(tickets, cache)

    sample = validation.build_sample(tickets)
    sample.to_csv(SAMPLE_PATH, index=False)
    print(f"Wrote {len(sample)} tickets to {SAMPLE_PATH}")
    print("Fill in manual_label, manual_correct (Y/N), and error_type "
          "(if N), then run: python validation/run_validation.py score")


def cmd_score():
    if not SAMPLE_PATH.exists():
        print(f"{SAMPLE_PATH} not found -- run `build` first.")
        sys.exit(1)
    import pandas as pd
    df = pd.read_csv(SAMPLE_PATH)
    df.to_csv(RESULTS_PATH, index=False)

    result = validation.score(df)
    if result["accuracy"] is None:
        print("No rows have manual_correct filled in yet (Y/N). Nothing to score.")
        return

    lines = [
        "# Validation Summary\n",
        f"Sample size (labeled): {result['n']} of {len(df)} sampled GW-OTHER tickets.\n",
        f"Accuracy: {result['accuracy']:.1%} ({result['correct']}/{result['n']} correct).\n",
        "\n## Errors by type\n",
    ]
    for etype, count in result["errors_by_type"].items():
        lines.append(f"- {etype}: {count}\n")

    SUMMARY_PATH.write_text("".join(lines), encoding="utf-8")
    print(f"Accuracy: {result['accuracy']:.1%} ({result['correct']}/{result['n']})")
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("build", "score"):
        print(__doc__)
        sys.exit(1)
    {"build": cmd_build, "score": cmd_score}[sys.argv[1]]()
