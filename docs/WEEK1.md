# Week 1 checklist

Goal: by the end of the week you have 300 real cases (listing + customer review + both photos) and can check them with one model call each, with the token cost shown.

- [x] Install Python, Git and VS Code; clone the repo; install requirements
- [x] `pytest -q` passes
- [x] API runs and `/docs` works
- [ ] Apply the v0.2 update (listing-mismatch pivot) and re-run `pytest -q`
- [ ] Run `python -m scripts.sample_reviews` → 300 cases in `data/sample/cases.jsonl`
- [ ] Look at 30 cases side by side (listing photo + description vs customer photo + review)
- [ ] **Edit `data/taxonomy/mismatch_types.yaml`**: add, merge or rename types to fit what you actually see
- [ ] Choose a model: local (Ollama + a vision model) or a hosted API with a free tier; fill in `.env`
- [ ] `python -m scripts.run_single_model --limit 10` works with the real model
- [ ] Check those 10 verdicts by hand: which are wrong, and why? Write 3 notes below
- [ ] Commit and push; the green "tests" check appears on GitHub

## Notes

(write what you noticed here)
