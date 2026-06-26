# Model Research Notes

These notes capture lightweight Hugging Face options for improving ReviewInsight without turning the MVP into a large ML system.

## Summary

- `google/flan-t5-small`: new default. It is instruction-tuned, relatively small, and works with the existing `AutoTokenizer` / `AutoModelForSeq2SeqLM` code path. Best fit for short customer-review explanations because the app can prompt it directly.
- `google/flan-t5-base`: likely better quality than `flan-t5-small`, but heavier. Good next option if local runtime performance is acceptable.
- `facebook/bart-large-cnn` or `sshleifer/distilbart-cnn-12-6`: strong generic summarizers, but they are trained for news-style summarization. They may compress reviews well, but they are less controllable than FLAN for "explain this customer review" phrasing.

## Sentiment

- Current default: `distilbert/distilbert-base-uncased-finetuned-sst-2-english`. It is fast and simple, but it is mainly positive/negative and does not naturally model neutral sentiment.
- Possible upgrade: a 3-label sentiment model with positive, neutral, and negative labels. This would reduce the amount of custom neutral handling in the backend.
- Keep the current natural-language explanation layer even if the model changes; it makes the tab easier to understand without requiring another inference call.

## Topics / Categories

- Candidate approach: zero-shot classification with `facebook/bart-large-mnli` or a lighter DeBERTa zero-shot model. Use the existing topic labels as candidate labels and allow multiple matches.
- Lightweight fallback: keep the current keyword rules when the zero-shot model is disabled or unavailable.
- Practical next step: add an optional `REVIEWINSIGHT_ENABLE_MODEL_TOPICS` flag before changing the default behavior.

## Urgency

- Candidate approach: reuse a zero-shot classifier with labels such as `low urgency`, `medium urgency`, and `high urgency`.
- Lightweight fallback: keep the current urgency scoring rules because they are predictable and easy to inspect.
- Practical next step: combine zero-shot urgency with existing high-risk keyword checks so obvious issues like refunds, lost data, crashes, and login failures remain high priority.

## Sources Reviewed

- https://huggingface.co/google/flan-t5-small
- https://huggingface.co/facebook/bart-large-cnn
- https://huggingface.co/facebook/bart-large-mnli
- https://huggingface.co/distilbert/distilbert-base-uncased-finetuned-sst-2-english
