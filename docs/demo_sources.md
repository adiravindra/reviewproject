# Verified demo sources and dataset options

This guide records only pages that the finished `backend.app.collector.collect_reviews`
function successfully collected on 2026-07-17. Counts are an observation from that
run, not a contract with the site. The runtime does not contain source-specific
selectors, copied review text, or hardcoded extraction results.

## Verified live sources

### web-scraping.dev: Box of Chocolate Candy

- **URL:** <https://web-scraping.dev/product/1>
- **Access date:** 2026-07-17
- **Extractor:** `json_ld`
- **Observed review count:** 5
- **Extraction notes:** The page title was `Box of Chocolate Candy`. JSON-LD provided five
  full written reviews; all five normalized with an integer rating (four or five), and
  the collected bodies were 50–86 characters long.
- **Runtime requirements:** No login, browser automation, JavaScript rendering, or anti-bot circumvention required.

### WordPress.org: Contact Form 7

- **URL:** <https://wordpress.org/plugins/contact-form-7/>
- **Access date:** 2026-07-17
- **Extractor:** `html_cards`
- **Observed review count:** 5
- **Extraction notes:** The public plugin page yielded five full written review cards.
  Each normalized with a four- or five-star rating, and the collected bodies were
  148–202 characters long. This demonstrates the conservative static-HTML fallback.
- **Runtime requirements:** No login, browser automation, JavaScript rendering, or anti-bot circumvention required.

### Mozilla Add-ons: Bitwarden Password Manager reviews

- **URL:** <https://addons.mozilla.org/en-US/firefox/addon/bitwarden-password-manager/reviews/>
- **Access date:** 2026-07-17
- **Extractor:** `html_cards`
- **Observed review count:** 13
- **Extraction notes:** The public review page yielded 13 full written review cards
  (42–435 characters). The generic static fallback intentionally left ratings unset
  because this card structure did not expose one of the collector's unambiguous
  rating fields; the written evidence and page title remained available.
- **Runtime requirements:** No login, browser automation, JavaScript rendering, or anti-bot circumvention required.

### Mozilla Add-ons: Dark Reader reviews

- **URL:** <https://addons.mozilla.org/en-US/firefox/addon/darkreader/reviews/>
- **Access date:** 2026-07-17
- **Extractor:** `html_cards`
- **Observed review count:** 7
- **Extraction notes:** The public review page yielded seven full written review cards
  (65–1,359 characters). As with the Bitwarden page, ratings were left unset rather
  than guessing from presentation-only star markup. This validates the generic
  `review` + `card` / `review` + `body` static class fallback.
- **Runtime requirements:** No login, browser automation, JavaScript rendering, or anti-bot circumvention required.

## Excluded candidates

- <https://steamcommunity.com/app/620/reviews/> was publicly reachable during
  verification but produced fewer than two normalized static written reviews, so the
  collector correctly returned `no_reviews`. It is not a demo target.
- Well-known marketplace and reputation sites were intentionally not added when their
  static markup is protected, JavaScript-dependent, login-gated, or inconsistent.
  This MVP does not bypass access controls or use browser automation.

## Open dataset assessment

### Kaggle: Women's E-Commerce Clothing Reviews

- **Access method:** Public [Kaggle dataset page](https://www.kaggle.com/datasets/nicapotato/womens-ecommerce-clothing-reviews)
  and downloadable archive; Kaggle's public metadata identifies about 23,000 customer
  reviews and ratings.
- **Authentication:** The official [KaggleHub authentication documentation](https://github.com/Kaggle/kagglehub#authenticate)
  says authentication is needed for public resources requiring user consent or for
  private resources. Treat a Kaggle account/token or consent step as a possible
  download prerequisite, not as an anonymous product-query API.
- **License/source:** Kaggle reports `CC0: Public Domain` on the
  [dataset page](https://www.kaggle.com/datasets/nicapotato/womens-ecommerce-clothing-reviews).
- **Product identifiers:** Its `Clothing ID` identifies the specific catalog piece in
  this dataset, but it is not a public retailer URL or an Amazon ASIN.
- **Suitability:** Good optional local demo corpus after a deliberate download and
  curation step; unsuitable as a direct live URL-scraper target or anonymous
  arbitrary-product retrieval service.

### McAuley Amazon Reviews 2023

- **Access method:** Public category archives and the
  [Hugging Face dataset card](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023)
  support bulk/category loading. The card reports a 750 GB total and its quick start
  uses `load_dataset(..., trust_remote_code=True)`.
- **Authentication:** The public card does not publish an account-token requirement,
  but its Dataset Viewer is disabled because the repository requires arbitrary Python
  code. This is bulk data loading, not an anonymous product lookup service.
- **License/source:** Use the [dataset card](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023)
  and [project documentation](https://amazon-reviews-2023.github.io/) as the source;
  the card does not declare a separate distribution license, so downstream use needs
  an independent rights review.
- **Product identifiers:** Review records include `asin` and `parent_asin`; the card
  explains that the parent ASIN groups color/style/size variants.
- **Suitability:** Useful only for an intentionally selected, locally stored corpus.
  Its scale and loading requirements make it unsuitable for this MVP's live scraper
  or a lightweight anonymous per-product retrieval flow.

### Stanford SNAP Amazon Fine Foods

- **Access method:** The [Stanford SNAP source page](https://snap.stanford.edu/data/web-FineFoods.html)
  exposes a direct `finefoods.txt.gz` archive with 568,454 reviews.
- **Authentication:** No login or API token is indicated for the direct archive
  download on the Stanford source page.
- **License/source:** The [Stanford SNAP source page](https://snap.stanford.edu/data/web-FineFoods.html)
  provides the original academic citation; it does not state a separate redistribution
  license, so retain the source citation and review terms before redistributing data.
- **Product identifiers:** `product/productId` is documented as an Amazon ASIN, so
  reviews can be grouped locally by product.
- **Suitability:** A reasonable optional offline corpus for a narrow food-review demo;
  it is historical (through October 2012) and is not a direct live URL-scraper source
  or an anonymous product-review API.

### Hugging Face Amazon Reviews Multi

- **Access method:** The public
  [dataset card](https://huggingface.co/datasets/goosmanlei/amazon_reviews_multi)
  provides raw `jsonl.gz` files and a Dataset Viewer. The viewer's documented
  read-only API supports filtering, and its public capability endpoint exposed
  `filter: true` without credentials during this research.
- **Authentication:** No token was needed for the public viewer-capability check on
  2026-07-17. Availability and terms can change, so a future integration must handle
  errors and terms rather than assume permanent anonymous access.
- **License/source:** The card labels the license `other` and directs users to the
  [original Amazon Reviews Multi terms](https://huggingface.co/datasets/amazon_reviews_multi),
  rather than granting a simple open redistribution license.
- **Product identifiers:** Records have a `product_id`, but the published values are
  opaque dataset IDs (for example, language-prefixed `product_...` values), not public
  store URLs or ASINs.
- **Suitability:** The closest free, publicly hosted option for retrieving reviews by
  a *known dataset* product ID. It can support a future curated-corpus or Dataset
  Viewer adapter, but cannot resolve an arbitrary product URL and is outside this
  MVP's static-scraper scope.

## Recommendation

Keep the bundled synthetic demo as the presentation-safe fallback: it is explicit,
mixed-sentiment, small, and never substitutes for a failed live scrape. Treat Kaggle,
SNAP, and McAuley data as optional future local-corpus ingestion after source and
license review. A product-specific hosted API (for example, Steam's documented
[app review endpoint](https://partner.steamgames.com/doc/store/getreviews)) would need
a separate JSON adapter and source-specific product ID handling; it is deliberately
outside the current Groq-only FastAPI + Streamlit MVP.
