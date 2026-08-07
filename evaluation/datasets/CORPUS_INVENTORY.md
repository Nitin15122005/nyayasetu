# External Legal Corpus — Inventory Report

Corpus location (configured, not hardcoded): `D:\Programs\raw-pdfs`
Scanned 4020 PDF files across 6 category folders in 134.8s.

This report is generated BEFORE any extraction — see `evaluation/datasets/build/corpus/build_from_corpus.py` for the extraction phase, which reads this inventory to decide what to sample and to skip corrupted/empty/duplicate files.

## Per-category summary

| Category | PDFs | Non-PDF files (skipped) | Avg pages | Corrupted | Empty | OCR-needed | Exact-dup files | Language distribution |
|---|---|---|---|---|---|---|---|---|
| Affidavit | 39 | 0 | 23.9 | 0 | 31 | 31 | 4 | unknown:31, en:8 |
| Bail_Application | 1 | 0 | 66.0 | 0 | 0 | 0 | 0 | en:1 |
| Court_Notice | 39 | 0 | 27.9 | 0 | 0 | 0 | 0 | en:39 |
| FIR | 193 | 0 | 6.9 | 0 | 0 | 0 | 0 | mr:193 |
| Legal_Notice | 3747 | 0 | 6.3 | 0 | 0 | 0 | 85 | en:3746, mr:1 |
| Property_Deed | 1 | 27 | 25.0 | 0 | 1 | 1 | 0 | unknown:1 |

## Corpus-wide language distribution

- en: 3794 (94.4%)
- mr: 194 (4.8%)
- unknown: 32 (0.8%)

## Duplicate detection

- **Exact duplicates (sha256 file-hash match)**: 19 group(s), 89 files total.
  - `03ca4e8c5e7c…`: ['Legal_Notice\\data\\MLHC010010412024_1_2024-11-07.pdf', 'Legal_Notice\\data\\MLHC010010422024_1_2024-11-07.pdf', 'Legal_Notice\\data\\MLHC010010432024_1_2024-11-07.pdf', 'Legal_Notice\\data\\MLHC010010442024_1_2024-11-07.pdf', 'Legal_Notice\\data\\MLHC010010452024_1_2024-11-07.pdf', 'Legal_Notice\\data\\MLHC010010462024_1_2024-11-07.pdf', 'Legal_Notice\\data\\MLHC010010472024_1_2024-11-07.pdf', 'Legal_Notice\\data\\MLHC010010482024_1_2024-11-07.pdf', 'Legal_Notice\\data\\MLHC010010492024_1_2024-11-07.pdf', 'Legal_Notice\\data\\MLHC010010512024_1_2024-11-07.pdf', 'Legal_Notice\\data\\MLHC010010522024_1_2024-11-07.pdf', 'Legal_Notice\\data\\MLHC010010532024_1_2024-11-07.pdf', 'Legal_Notice\\data\\MLHC010010542024_1_2024-11-07.pdf', 'Legal_Notice\\data\\MLHC010010552024_1_2024-11-07.pdf']
  - `055dc6c8192e…`: ['Legal_Notice\\data\\TRHC010008002021_1_2024-05-22.pdf', 'Legal_Notice\\data\\TRHC010008052021_1_2024-05-22.pdf']
  - `29a7e67fe328…`: ['Legal_Notice\\data\\MLHC010010602024_1_2024-11-06.pdf', 'Legal_Notice\\data\\MLHC010010612024_1_2024-11-06.pdf', 'Legal_Notice\\data\\MLHC010010622024_1_2024-11-06.pdf']
  - `2eb09a6da6cf…`: ['Legal_Notice\\data\\MLHC010003462023_1_2024-05-28.pdf', 'Legal_Notice\\data\\MLHC010003482023_1_2024-05-28.pdf', 'Legal_Notice\\data\\MLHC010003502023_1_2024-05-28.pdf', 'Legal_Notice\\data\\MLHC010003522023_1_2024-05-28.pdf', 'Legal_Notice\\data\\MLHC010003542023_1_2024-05-28.pdf', 'Legal_Notice\\data\\MLHC010003562023_1_2024-05-28.pdf', 'Legal_Notice\\data\\MLHC010003582023_1_2024-05-28.pdf', 'Legal_Notice\\data\\MLHC010003602023_1_2024-05-28.pdf', 'Legal_Notice\\data\\MLHC010003632023_1_2024-05-28.pdf', 'Legal_Notice\\data\\MLHC010003652023_1_2024-05-28.pdf', 'Legal_Notice\\data\\MLHC010003672023_1_2024-05-28.pdf']
  - `332d29564655…`: ['Affidavit\\9681c618-e930-4245-ac4d-b500be0ab26c (1).pdf', 'Affidavit\\9681c618-e930-4245-ac4d-b500be0ab26c.pdf']
  - `33d621e4aa8f…`: ['Legal_Notice\\data\\TRHC010017812023_1_2024-02-21.pdf', 'Legal_Notice\\data\\TRHC010018052023_1_2024-02-21.pdf']
  - `3658928ff69d…`: ['Legal_Notice\\data\\MLHC010000222024_1_2024-02-22.pdf', 'Legal_Notice\\data\\MLHC010014792023_1_2024-02-22.pdf']
  - `39789859c3f5…`: ['Legal_Notice\\data\\TRHC010013862021_1_2024-03-18.pdf', 'Legal_Notice\\data\\TRHC010013872021_1_2024-03-18.pdf', 'Legal_Notice\\data\\TRHC010013882021_1_2024-03-18.pdf']
  - `4315db75fb26…`: ['Legal_Notice\\data\\MLHC010004212016_1_2024-04-16.pdf', 'Legal_Notice\\data\\MLHC010004232016_1_2024-04-16.pdf', 'Legal_Notice\\data\\MLHC010004272016_1_2024-04-16.pdf', 'Legal_Notice\\data\\MLHC010004282016_1_2024-04-16.pdf']
  - `6d7e37afe993…`: ['Affidavit\\b1be69dc-875b-43f3-8dee-e5e9ee3bd6d7 (1).pdf', 'Affidavit\\b1be69dc-875b-43f3-8dee-e5e9ee3bd6d7.pdf']
  - `9b9be7ae113c…`: ['Legal_Notice\\data\\MLHC010003932023_1_2024-04-05.pdf', 'Legal_Notice\\data\\MLHC010010862022_1_2024-04-05.pdf', 'Legal_Notice\\data\\MLHC010011092022_1_2024-04-05.pdf', 'Legal_Notice\\data\\MLHC010011182022_1_2024-04-05.pdf']
  - `a9aff404e4b2…`: ['Legal_Notice\\data\\MLHC010004172016_1_2024-06-03.pdf', 'Legal_Notice\\data\\MLHC010004242016_1_2024-06-03.pdf']
  - `adadf2ee1839…`: ['Legal_Notice\\data\\MLHC010000732024_1_2024-11-05.pdf', 'Legal_Notice\\data\\MLHC010012952023_1_2024-11-05.pdf']
  - `bde54ce2a54b…`: ['Legal_Notice\\data\\MLHC010012232023_1_2024-08-16.pdf', 'Legal_Notice\\data\\MLHC010012242023_1_2024-08-16.pdf']
  - `bea053b5c150…`: ['Legal_Notice\\data\\MLHC010007242024_1_2024-11-28.pdf', 'Legal_Notice\\data\\MLHC010007252024_1_2024-11-28.pdf', 'Legal_Notice\\data\\MLHC010007262024_1_2024-11-28.pdf', 'Legal_Notice\\data\\MLHC010008212024_1_2024-11-28.pdf', 'Legal_Notice\\data\\MLHC010008222024_1_2024-11-28.pdf', 'Legal_Notice\\data\\MLHC010008232024_1_2024-11-28.pdf']
  - `e0e1465f9e53…`: ['Legal_Notice\\data\\MLHC010008472023_1_2024-05-20.pdf', 'Legal_Notice\\data\\MLHC010010802023_1_2024-05-20.pdf']
  - `eb579a5feb39…`: ['Legal_Notice\\data\\MLHC010008332023_1_2024-02-15.pdf', 'Legal_Notice\\data\\MLHC010008342023_1_2024-02-15.pdf', 'Legal_Notice\\data\\MLHC010008352023_1_2024-02-15.pdf', 'Legal_Notice\\data\\MLHC010008362023_1_2024-02-15.pdf', 'Legal_Notice\\data\\MLHC010008372023_1_2024-02-15.pdf', 'Legal_Notice\\data\\MLHC010008402023_1_2024-02-15.pdf', 'Legal_Notice\\data\\MLHC010008412023_1_2024-02-15.pdf', 'Legal_Notice\\data\\MLHC010008432023_1_2024-02-15.pdf', 'Legal_Notice\\data\\MLHC010008442023_1_2024-02-15.pdf']
  - `f0ee8adac71c…`: ['Legal_Notice\\data\\MLHC010000212024_1_2024-02-22.pdf', 'Legal_Notice\\data\\MLHC010014782023_1_2024-02-22.pdf']
  - `f3b0c3f83593…`: ['Legal_Notice\\data\\MLHC010007802022_1_2024-07-11.pdf', 'Legal_Notice\\data\\MLHC010009542021_1_2024-07-11.pdf', 'Legal_Notice\\data\\MLHC010013512022_1_2024-07-11.pdf', 'Legal_Notice\\data\\MLHC010013522022_1_2024-07-11.pdf', 'Legal_Notice\\data\\MLHC010013532022_1_2024-07-11.pdf', 'Legal_Notice\\data\\MLHC010013542022_1_2024-07-11.pdf', 'Legal_Notice\\data\\MLHC010013552022_1_2024-07-11.pdf', 'Legal_Notice\\data\\MLHC010013582022_1_2024-07-11.pdf', 'Legal_Notice\\data\\MLHC010013592022_1_2024-07-11.pdf', 'Legal_Notice\\data\\MLHC010013602022_1_2024-07-11.pdf', 'Legal_Notice\\data\\MLHC010013712022_1_2024-07-11.pdf', 'Legal_Notice\\data\\MLHC010013722022_1_2024-07-11.pdf', 'Legal_Notice\\data\\MLHC010013732022_1_2024-07-11.pdf', 'Legal_Notice\\data\\MLHC010013742022_1_2024-07-11.pdf', 'Legal_Notice\\data\\MLHC010013752022_1_2024-07-11.pdf']
- **Filename-pattern duplicates** (same name modulo a trailing ` (n)` — a secondary, weaker signal, not merged with exact duplicates): 53 group(s).

## Corrupted / unreadable PDFs

0 file(s) could not be opened or read by PyMuPDF:

## Empty documents (no meaningfully extractable text)

32 file(s) opened successfully but yielded under 20 characters of extractable text.

## OCR requirements

32/4020 (0.8%) files have under 40 extractable chars/page on average — almost certainly scanned images with no embedded text layer, needing OCR before any text-based extraction (entity/section/citation extraction, language ID, summarization) can run on them. This build's extraction phase (`build_from_corpus.py`) SKIPS these — no OCR engine is wired into this pipeline (pytesseract exists in `backend/lex_validator.py` for image uploads, but is not invoked here) — see the gap list in NSLB_REPORT.md.

## Non-PDF files present (out of scope for this pipeline)

- Property_Deed: 27 non-PDF file(s) (e.g. .doc/.docx) — not processed; this pipeline only reads PDFs via PyMuPDF.
