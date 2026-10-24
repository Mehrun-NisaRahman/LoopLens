# Week 2: the agent pipeline

Goal: split the single model call into agents and measure whether it helps, and what it costs.

| Agent | Sees | Job |
|---|---|---|
| Router | text only | list the customer's complaints, first verdict from text |
| Photo inspector | listing photo + customer photo | does the photo confirm, contradict or not show each complaint? |
| Judge | everything above + taxonomy rules | final verdict, types, photo role, explanation |

Modes: `full` (always inspect photos) vs `smart` (skip photos for a confident, complaint-free review).

## Checklist
- [ ] `python -m scripts.run_pipeline --mode smart --limit 30`
- [ ] `python -m scripts.run_pipeline --mode full --limit 30`
- [ ] `python -m scripts.compare` and save the table in the README
- [ ] Read the disagreements: where does the pipeline beat / lose to the single model?
- [ ] Label 30 more gold cases (small sets hide real differences)
- [ ] v2 (stricter quality rule): label cases 61-90 blind, then run all setups with --start 61 --limit 30 --tag v2
- [ ] Stronger Judge: --judge-model gemini-3.8-flash --tag v2_judge38
- [ ] Later: Explainer agent and the human confirm/overrule step
