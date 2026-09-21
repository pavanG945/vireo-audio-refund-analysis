"""Builds a stratified validation sample for manual review of the GW-OTHER
reclassification, and scores the tool's output against those manual labels.
"""
import pandas as pd

from . import config

SAMPLE_SIZE = 120  # see validation/validation_summary.md for the rationale


def build_sample(tickets_with_classification: pd.DataFrame, n: int = SAMPLE_SIZE,
                  seed: int = 42) -> pd.DataFrame:
    """Stratified sample across the classifier's predicted labels, so rare
    labels (e.g. AMBIGUOUS) aren't drowned out by common ones.
    """
    gw = tickets_with_classification[
        tickets_with_classification["refund_reason_code"] == config.DEFAULT_DROPDOWN_CODE
    ].copy()
    gw = gw[gw["effective_reason_code"].notna()]

    n_labels = gw["effective_reason_code"].nunique()
    per_label = max(1, n // max(1, n_labels))

    sampled = (
        gw.groupby("effective_reason_code", group_keys=False)
        .apply(lambda g: g.sample(min(len(g), per_label), random_state=seed))
    )
    if len(sampled) < n:
        remainder = gw.drop(sampled.index)
        extra = remainder.sample(min(len(remainder), n - len(sampled)), random_state=seed)
        sampled = pd.concat([sampled, extra])

    cols = [
        "ticket_id", "category", "refund_amount_corrected", "customer_message",
        "agent_notes", "effective_reason_code", "classification_confidence",
        "classification_evidence", "classification_source",
    ]
    out = sampled[cols].rename(columns={"effective_reason_code": "tool_predicted_label"})
    out["manual_label"] = ""  # filled in during manual review
    out["manual_correct"] = ""  # Y/N, filled in during manual review
    out["error_type"] = ""  # filled in when manual_correct == N
    return out.sample(frac=1, random_state=seed).reset_index(drop=True)


def score(validation_results: pd.DataFrame) -> dict:
    labeled = validation_results[validation_results["manual_correct"].isin(["Y", "N"])]
    if len(labeled) == 0:
        return {"n": 0, "accuracy": None}
    correct = (labeled["manual_correct"] == "Y").sum()
    return {
        "n": len(labeled),
        "correct": int(correct),
        "accuracy": correct / len(labeled),
        "errors_by_type": labeled[labeled["manual_correct"] == "N"]["error_type"]
        .value_counts()
        .to_dict(),
    }
