# Model Research Notes

These notes capture free local Hugging Face options for improving ReviewInsight without requiring paid API calls.

## Summary

- Current default: `Qwen/Qwen2.5-1.5B-Instruct`. It keeps the instruction-following benefits of the Qwen chat family while being much more practical for a 4 GB RTX 3050 Laptop GPU. On this machine, fp16 CUDA inference was faster than 4-bit quantization and still fit in VRAM.
- Higher-quality local option: `Qwen/Qwen2.5-3B-Instruct`. It produced strong summaries, but measured too slowly on CPU for product-review workloads and is less comfortable on 4 GB VRAM.
- Fallback local option: `google/flan-t5-large`. It is easier on the seq2seq path than Qwen-style causal models, but the output is usually less polished and less controllable than a modern chat model.
- Other candidates reviewed: `google/gemma-2-2b-it` and `microsoft/Phi-3.5-mini-instruct`. Both are reasonable local chat-model alternatives, but Qwen is the best default for this demo because it is broadly used, supports long context, follows structured prompts well, and has straightforward Transformers support.
- Avoid as the default: `facebook/bart-large-cnn` or `sshleifer/distilbart-cnn-12-6`. They are strong generic summarizers, but are trained for news-style summarization and are less natural for "explain this customer review" phrasing.

## Sentiment

- Current default: `cardiffnlp/twitter-roberta-base-sentiment-latest`. It is free, local, popular, and returns positive, neutral, and negative labels. The 3-label output maps directly to the app's dashboard and avoids forcing neutral reviews into positive/negative buckets.
- Higher-capacity alternative: `j-hartmann/sentiment-roberta-large-english-3-classes`. It also returns positive, neutral, and negative labels, but it is heavier and trained on a smaller manually annotated social-media dataset. Good to evaluate later if the default misses too many nuanced cases.
- Review-rating alternative: `nlptown/bert-base-multilingual-uncased-sentiment` or `LiYuan/amazon-review-sentiment-analysis`. These are useful when star rating is the primary output, but they are less direct for this app's positive/neutral/negative explanation flow.
- Keep the current natural-language explanation layer even if the model changes; it makes the tab easier to understand without requiring another inference call.

## Performance

- The machine has an NVIDIA GeForce RTX 3050 Laptop GPU with 4 GB VRAM. After installing CUDA-enabled PyTorch, `torch.cuda.is_available()` returns `True`.
- CPU baseline with cached Qwen 3B was about 57 seconds cold and 23 seconds warm for one short review. That is acceptable for quality checks, but not scalable.
- The backend now batches sentiment classification so many reviews use one Transformers pipeline call.
- Product-scale report generation should summarize the review set once through `/analysis/batch`, rather than generating one LLM summary per review.
- Summary loading uses `REVIEWINSIGHT_SUMMARY_QUANTIZATION=auto`, which keeps the default 1.5B model in fp16 on CUDA, selects 4-bit quantization for larger model names such as Qwen 3B, and uses plain loading on CPU.

## Topics / Categories

- Candidate approach: zero-shot classification with `facebook/bart-large-mnli` or a lighter DeBERTa zero-shot model. Use the existing topic labels as candidate labels and allow multiple matches.
- Lightweight fallback: keep the current keyword rules only if a future topic model is unavailable.
- Practical next step: evaluate a topic model before changing the default behavior.

## Urgency

- Candidate approach: reuse a zero-shot classifier with labels such as `low urgency`, `medium urgency`, and `high urgency`.
- Lightweight fallback: keep the current urgency scoring rules because they are predictable and easy to inspect.
- Practical next step: combine zero-shot urgency with existing high-risk keyword checks so obvious issues like refunds, lost data, crashes, and login failures remain high priority.

## Sources Reviewed

- https://huggingface.co/google/flan-t5-small
- https://huggingface.co/Qwen/Qwen2.5-3B-Instruct
- https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct
- https://huggingface.co/google/gemma-2-2b-it
- https://huggingface.co/microsoft/Phi-3.5-mini-instruct
- https://huggingface.co/google/flan-t5-large
- https://huggingface.co/facebook/bart-large-cnn
- https://huggingface.co/facebook/bart-large-mnli
- https://huggingface.co/distilbert/distilbert-base-uncased-finetuned-sst-2-english
- https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest
- https://huggingface.co/j-hartmann/sentiment-roberta-large-english-3-classes
- https://huggingface.co/nlptown/bert-base-multilingual-uncased-sentiment
- https://huggingface.co/LiYuan/amazon-review-sentiment-analysis
