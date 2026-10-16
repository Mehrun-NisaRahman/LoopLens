# LoopLens

**Human-in-the-loop multi-agent coding of customer reviews that include photos.**

LoopLens takes product reviews with customer photos, lets a small team of AI agents suggest qualitative codes and themes, and puts a human reviewer in control at two checkpoints (accept, edit or reject). Every code links back to its evidence in the text or the photo.

The project also answers a research question with numbers: *does an agent team with a human in the loop code multimodal reviews better than a single vision-language model, at the same token cost?*

> Status: **week 1 of 6**. The project skeleton, the data sampler, a draft codebook and the single-model baseline are in place. The agent pipeline and the review UI come next.

## How it will work

```
Web app (React)  <->  API (FastAPI)  <->  Storage
                         |
                  Agent pipeline (background job)
   Preprocessing -> Coding -> [You review] -> Cross-modal -> Themes
   -> [You review] -> Validation -> Explainability -> Report
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
# open http://127.0.0.1:8000/docs to try the API
```

Out of the box LoopLens uses the **mock** model: no network and no cost. It runs on 6 synthetic demo reviews, so you can build and test everything offline.

## Real data

```bash
python -m scripts.sample_reviews --category All_Beauty --n 300
```

This streams the [Amazon Reviews 2023](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023) dataset (McAuley Lab, UCSD), keeps reviews that have a customer photo, samples 300 with a fixed seed and downloads their photos to `data/images/`. The data stays local and is not committed. Check the dataset's terms before publishing any of it.

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
python -m scripts.run_baseline --limit 10
```

Every model response is cached in `data/cache/`, so re-running an experiment costs nothing.

## Project layout

| Path | What it is |
| --- | --- |
| `looplens/codebook.py` | Loads and validates the codebook |
| `looplens/model.py` | Vision-language model client (mock + OpenAI-compatible) with a disk cache |
| `looplens/baseline.py` | Setup 1: the single-model baseline and a strict JSON parser |
| `app/main.py` | FastAPI app: `/health`, `/codebook`, `/reviews`, `/reviews/{id}/baseline` |
| `scripts/sample_reviews.py` | Downloads and samples reviews with photos |
| `scripts/run_baseline.py` | Runs the baseline over the sample and reports tokens |
| `data/codebook/codebook.yaml` | The codebook: draft v0.1 |
| `tests/` | pytest suite, run by GitHub Actions on every push |

## Roadmap

- [x] Week 1: foundations, data sampler, codebook draft, single-model baseline
- [ ] Week 2: seven agent functions, pipeline runner, job queue
- [ ] Week 3: review UI (upload, accept, edit, reject, both checkpoints)
- [ ] Week 4: themes dashboard, evidence view, export, **live demo**
- [ ] Week 5: 100-review gold set, three-way evaluation (F1, kappa, cost)
- [ ] Week 6: results, video, write-up

## Author

Built by [Mehrun-Nisa Rahman](https://github.com/Mehrun-NisaRahman) as an independent solo project related to her undergraduate thesis on human-in-the-loop multi-agent vision-language AI.
