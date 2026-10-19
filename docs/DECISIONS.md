# Design decisions

Short log of choices made while building LoopLens, and why.

## 1. Judge with all the evidence (week 1)
Verdicts use the listing (title, description, photo), the review text and the customer photo together.
A specific written complaint is enough for `mismatch`; dislike or a low rating alone is not.

## 2. Arrival damage vs. breaking during use (week 1)
`damaged_defective` = broken when it arrived. Arrived fine but broke during normal use = `quality_far_below`.
Found while labelling case b31ba2f7bc6a (hair-clip flower fell off after use).

## 3. Photo role instead of "photo needed?" (week 1)
Each gold case records what the customer photo did: `decisive`, `confirms`, `contradicts` or `no_help`.
Photos are how we verify a customer's claim, not just how we find problems. `contradicts` cases
(claim not supported by the photo) should be flagged for human review.

## 4. Text-first routing (planned, week 2)
A Router agent reads only the listing and review text first.
- Clearly positive review and high confidence -> `match`, skip the photo check (cheaper, faster).
- Complaint, vague/short review, or low confidence -> run the Photo inspector.

Risk: happy customers who received the wrong item (the `decisive` cases) would be missed.
So both modes are kept and measured on the gold set:
- **full**: always check photos
- **smart**: Router decides

Report accuracy, tokens and cost for each in the README.
