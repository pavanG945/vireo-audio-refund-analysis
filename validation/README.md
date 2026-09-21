# validation/

1. Run `python -m src.main` at least once (needs `output/classification_cache.json`).
2. `python validation/run_validation.py build` -- writes `validation_sample.csv`,
   a stratified sample of GW-OTHER tickets across the classifier's predicted
   labels.
3. Manually review each row: read `customer_message` and `agent_notes`,
   fill in `manual_label`, `manual_correct` (Y/N against `tool_predicted_label`),
   and `error_type` if incorrect.
4. `python validation/run_validation.py score` -- writes `validation_results.csv`
   and `validation_summary.md` with accuracy and an error-type breakdown.

`validation_sample.csv` and `validation_results.csv` are not committed
(they contain customer message text) -- see `DECISIONS.md`.
`validation_summary.md` (aggregate numbers only, no free text) is safe to
commit and is referenced from the memo and submission form.
