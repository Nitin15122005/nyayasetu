# Evaluation datasets

- `templates/` — one `<suite>.jsonl.template` per dataset-driven suite, committed to git. These show the exact schema (see `schema.py`) with obviously-placeholder values. They are **not evaluation data** — every field is a `PLACEHOLDER` string and no metric should ever be computed from them.
- `raw/` — real datasets go here, named `<suite>.jsonl`, matching the `dataset_file` field in `evaluation/config/experiments/<suite>.yaml`. Empty in this commit — populating it with reviewed, labeled records is a separate, deliberate step (not something to be generated automatically), since these are the ground truth an evaluation report's credibility rests on.
- `raw/fixtures/` — binary fixtures (PDFs, images) referenced by `file_path` in `document_analysis`, `legal_qa`, and `end_to_end` datasets. Not created yet — add it when the first fixture-needing dataset is populated.

To add a real dataset: copy the matching file from `templates/` to `raw/<suite>.jsonl`, replace every placeholder with a reviewed real record, and run `python -m evaluation.cli run --suite <suite>` — the loader in `loader.py` will reject anything that doesn't match the schema in `schema.py`, with an exact file:line pointer.
