from backend.app.schemas.website import (
    AnalysisMetadata,
    CollectionMetadata,
    EvidenceItem,
    NormalizedReview,
    RepresentativeReview,
    ReviewMetrics,
    SentimentCounts,
    SourceMetadata,
    WebsiteAnalysisResponse,
    WebsiteInsights,
)


def complete_response(
    *,
    run_id: str = "run_test",
    completed_at: str = "2026-07-10T15:00:00Z",
) -> WebsiteAnalysisResponse:
    first = NormalizedReview(
        id="r1",
        text="Excellent quality and simple setup.",
        rating=5,
        author="Ada",
        publication_date="2026-06-01",
        source_url="https://public.example/reviews#r1",
    )
    second = NormalizedReview(
        id="r2",
        text="Support was slow to respond.",
        rating=2,
        author="Grace",
        publication_date="2026-06-02",
        source_url="https://public.example/reviews#r2",
    )
    evidence = EvidenceItem(
        label="Quality",
        summary="Quality is a consistent strength.",
        review_ids=["r1"],
    )
    return WebsiteAnalysisResponse(
        id=run_id,
        source=SourceMetadata(
            requested_url="https://public.example/reviews",
            canonical_url="https://public.example/product",
            entity_name="Example Product",
            entity_type="Product",
            page_title="Example Product Reviews",
            scraper_name="json_ld",
            pages_attempted=1,
            pages_succeeded=1,
        ),
        collection=CollectionMetadata(
            found=2,
            valid=2,
            analyzed=2,
            duplicates_removed=0,
            invalid_removed=0,
            omitted_by_cap=0,
            low_sample=True,
            warnings=["Only 2 reviews were available, so insights may be less reliable."],
        ),
        metrics=ReviewMetrics(
            reviews_found=2,
            reviews_valid=2,
            reviews_analyzed=2,
            reviews_skipped=0,
            rated_reviews=2,
            average_rating=3.5,
            rating_distribution={"1": 0, "2": 1, "3": 0, "4": 0, "5": 1},
            sentiment_counts=SentimentCounts(positive=1, neutral=0, negative=1),
            overall_sentiment="mixed",
        ),
        insights=WebsiteInsights(
            executive_summary="Customers value quality but want faster support.",
            strengths=[evidence],
            complaints=[evidence],
            aspects=[evidence],
            opportunities=[evidence],
            representative_reviews=[
                RepresentativeReview(
                    review_id="r1",
                    text=first.text,
                    sentiment="positive",
                    rating=first.rating,
                    publication_date=first.publication_date,
                    source_url=first.source_url,
                )
            ],
        ),
        reviews=[first, second],
        analysis=AnalysisMetadata(
            provider="google",
            model="gemini-2.5-flash-lite",
            batch_count=1,
            llm_call_count=2,
            completed_at=completed_at,
        ),
    )
