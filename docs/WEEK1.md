# Week 1 checklist

Goal: by the end of the week you can code real reviews with one model call each and see the token cost.

- [ ] Message your supervisor and teammates about this solo project
- [ ] Install Python 3.11+, Git and VS Code; clone the repo; `pip install -r requirements.txt`
- [ ] `pytest -q` passes (8 tests)
- [ ] `uvicorn app.main:app --reload` → open `/docs` and try every endpoint
- [ ] Run `python -m scripts.sample_reviews` → 300 reviews and photos in `data/`
- [ ] Read 30 of the sampled reviews and **edit `data/codebook/codebook.yaml`**: add, remove or rename codes so they fit what you actually see (aim for 8–12)
- [ ] Choose a model: local (Ollama + a vision model) or a hosted API with a free tier; fill in `.env`
- [ ] `python -m scripts.run_baseline --limit 10` works with the real model
- [ ] Look at the 10 results by hand: which codes look wrong? Write 3 notes in this file
- [ ] Commit and push; the green "tests" check appears on GitHub

## Notes

(write what you noticed here)
