# Authorized Real Review Sources

This file tracks sources that can provide real review data for manual model evaluation.

## Amazon Reviews'23

**Source:** https://amazon-reviews-2023.github.io/

**Why use it:** The dataset contains real Amazon review records with star ratings and text across many product categories. It is large enough to sample positive, negative, and neutral examples without scraping live Amazon product pages.

**Local extractor:** `extract_amazon_reviews23_sample.py`

**Default category:** `All_Beauty`

**Default sentiment mapping:**

- 4 or 5 stars: positive
- 3 stars: neutral
- 1 or 2 stars: negative

**Evaluation fields generated:**

- `review_text`
- `source_type`
- `source_dataset`
- `source_category`
- `rating`
- `expected_sentiment`
- `expected_sentiment_keywords_phrases`
- `expected_summary_seed`
- `notes`

## Yelp Open Dataset

**Source:** https://www.yelp.com/dataset

**Why use it:** Yelp publishes a dataset for research and learning that includes local-business reviews. This is preferable to scraping live Yelp business pages.

**Status:** Not downloaded in this workspace. Add a local extractor once `yelp_academic_dataset_review.json` is available under an approved local path.

**Default sentiment mapping:**

- 4 or 5 stars: positive
- 3 stars: neutral
- 1 or 2 stars: negative

## Live Website Scraping

Live website scraping is intentionally not configured here. If the app later needs production ingestion from real businesses, prefer official APIs, customer-owned exports, or platform-approved data feeds.
