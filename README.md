# LoopLens

**Did you get what the listing promised? Human-in-the-loop AI that checks online product listings against what buyers actually received.**

LoopLens pairs each product listing (title, description, seller photo) with a customer review and the customer's own photo. A small team of AI agents compares the two and flags mismatches: wrong item, wrong colour, smaller than listed, damaged, missing parts, or a suspected fake. A human reviewer confirms or overrules every flag, and every verdict links back to its evidence.

It also answers a question with numbers: *does an agent team with a human in the loop catch listing mismatches more accurately than a single vision-language model, at the same token cost?*

> Status: **week 1 of 6**. The API, data builder, mismatch taxonomy and single-model baseline are in place. The agent pipeline and review UI come next.

## How it will work

```
Web app (React)  <->  API (FastAPI)  <->  Storage
                         |
               Agent pipeline (background job)
  Listing reader -> Photo inspector -> Comparer -> Judge -> Explainer
                         |
               [ You confirm or overrule ]
                         |
           Vision-language model (hosted or local)
```

## Quick start

```bash
git clone https://github.com/Mehrun-NisaRahman/LoopLens.git
cd LoopLens
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env

pytest -q                   # 8 tests, no API key needed
uvicorn app.main:app --reload
# open http://127.0.0.1:8000/docs
```

Out of the box LoopLens uses the **mock** model: no network and no cost. It runs on 6 synthetic demo cases, so you can build and test offline.

## Real data

```bash
python -m scripts.sample_reviews --category All_Beauty --n 300
```

This builds 300 cases from [Amazon Reviews 2023](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023) (McAuley Lab, UCSD). Each case pairs a review that has a customer photo with its product listing, joined on `parent_asin`. Half the sample is 1–2 star reviews, so mismatches are well represented. Photos go to `data/images/reviews/` and `data/images/listings/`. The data stays local and is not committed. Check the dataset's terms before publishing any of it.

## Real model

Set these in `.env` for any OpenAI-compatible chat API, such as a local [Ollama](https://ollama.com) server or a hosted provider:

```
LOOPLENS_PROVIDER=openai
LOOPLENS_BASE_URL=http://localhost:11434/v1
LOOPLENS_MODEL=qwen2.5vl:7b
LOOPLENS_API_KEY=
```

Then run the baseline:

```bash
python -m scripts.run_single_model --limit 10
```

Each call sends the listing photo and the customer photo with the text. Every response is cached in `data/cache/`, so re-running an experiment costs nothing.

## Project layout

| Path | What it is |
| --- | --- |
| `data/taxonomy/mismatch_types.yaml` | Verdicts (match / mismatch / unclear) and 8 mismatch types: draft v0.1 |
| `looplens/data.py` | `Case` = listing + customer review, and loaders |
| `looplens/model.py` | Vision-language model client (mock + OpenAI-compatible), multi-image, disk cache |
| `looplens/single_model.py` | Setup 1: the single-model baseline and a strict JSON parser |
| `app/main.py` | FastAPI: `/health`, `/taxonomy`, `/cases`, `/cases/{id}/single-model` |
| `scripts/sample_reviews.py` | Builds the dataset (reviews + listings + photos) |
| `scripts/run_single_model.py` | Runs the baseline over all cases and reports tokens |
| `tests/` | pytest suite, run by GitHub Actions on every push |

## Roadmap

- [x] Week 1: foundations, dataset builder, mismatch taxonomy, single-model baseline
- [ ] Week 2: agent pipeline (listing reader, photo inspector, comparer, judge, explainer)
- [ ] Week 3: review UI (side-by-side listing vs customer photo, confirm or overrule)
- [ ] Week 4: mismatch dashboard, evidence view, export, **live demo**
- [ ] Week 5: 100-case gold set, three-way evaluation (accuracy, F1, kappa, cost)
- [ ] Week 6: results, video, write-up

## Author

Built by [Mehrun-Nisa Rahman](https://github.com/Mehrun-NisaRahman) as an independent solo project.
