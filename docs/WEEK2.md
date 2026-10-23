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
- [ ] Later: Explainer agent and the human confirm/overrule step
