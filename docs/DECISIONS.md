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

## 4. Silent colour/size differences are not mismatches (week 1)
Case cb052cf5fb3f: listing photo shows a pink brush, customer photo shows teal, customer is delighted.
Amazon listings group colour/size variants under one parent; the main photo shows only one of them,
so an unmentioned colour or size difference is most likely a variant the customer chose. Verdict: `match`.
Consequence: the photo's main job is to verify complaints (`confirms` / `contradicts`), not to find
problems the customer never raised. This also makes text-first routing (5) safer.

## 5. Adjudication of the first disagreements (week 1)
After the first real-model run, four disagreements were re-checked by hand:
- 71f8ac7c7002 (listing photo is a "sold out" banner): changed to `match`. The customer is satisfied
  and their photo shows the described product, so a missing listing photo alone does not make a case unclear.
- 6d3b945d2609: changed to `mismatch` / `quality_far_below` - it melted during normal use (rule 2).
- cb052cf5fb3f: kept `match` (rule 4).
- 73563c8f01b4: kept `mismatch` / `wrong_item`.

## 6. Mixed reviews are decided by the star rating (week 1)
Case 5b30f040c437: a happy review that also mentions a rod ripping. A minor complaint inside praise is
`match` at 4-5 stars (the customer accepts it) and `mismatch` / `quality_far_below` at 1-3 stars.
Stars never override a concrete problem: missing parts, wrong item, wrong quantity or damage on arrival
are mismatches whatever the rating. (Week 1 also showed a low rating alone is not a mismatch.)

## 7. Text-first routing (planned, week 2)
A Router agent reads only the listing and review text first.
- Clearly positive review and high confidence -> `match`, skip the photo check (cheaper, faster).
- Complaint, vague/short review, or low confidence -> run the Photo inspector.

Risk: happy customers who received the wrong item (the `decisive` cases) would be missed.
So both modes are kept and measured on the gold set:
- **full**: always check photos
- **smart**: Router decides

Report accuracy, tokens and cost for each in the README.
