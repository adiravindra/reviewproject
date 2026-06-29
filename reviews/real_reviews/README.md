# Real Review Evaluation Data

This folder is for real review data used to evaluate summarization and sentiment keyword highlighting.

Do not scrape live Amazon, Yelp, Google, TripAdvisor, or similar pages directly into this repository unless you have explicit permission and the scrape complies with the site's terms. Live review pages often contain user-generated copyrighted text and automated-access restrictions.

## Current Real-Data Path

Use `extract_amazon_reviews23_sample.py` to create a local sample from the public Amazon Reviews'23 dataset by McAuley Lab. The dataset page describes review records with ratings, text, timestamps, helpfulness votes, ASINs, and user IDs, and provides category-level download links.

The generated output is written to `reviews/real_reviews/generated/real_review_samples.jsonl`. For this demo project, the generated sample can stay in the workspace as reference material.

## Source Notes

- Amazon Reviews'23: public dataset collected by McAuley Lab with review text, ratings, helpfulness votes, timestamps, and item metadata.
- Yelp Open Dataset: useful real local-business review source, but it requires downloading through Yelp's dataset process and accepting its terms. If you download it locally, a similar extractor can be added for `yelp_academic_dataset_review.json`.

## Recommended Manual Evaluation Workflow

1. Run the extractor after confirming the dataset source is acceptable for your use.
2. Open `generated/real_review_samples.jsonl`.
3. Paste each `review_text` into the app.
4. Compare app output against the record's `expected_sentiment`, `expected_sentiment_keywords_phrases`, and `expected_summary_seed`.
5. Update notes when the model misses phrase-level sentiment evidence or produces a summary that drops important customer-experience details.
