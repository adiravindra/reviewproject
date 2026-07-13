"""Produce schema-validated insights from supplied review evidence only.

Provider integrations are imported lazily so an unused provider remains an
optional dependency. Model construction and invocation errors are converted to
the safe analysis boundary, and returned sentiment IDs must exactly match input.
"""

import json
import os

from langchain.agents import create_agent

from backend.app.errors import AnalysisError
from backend.app.models import AgentInsights, Provider, Review


# The prompt explicitly forbids outside facts and asks for one structured result;
# deterministic metrics stay out of the model and are computed by the service.
SYSTEM_PROMPT = """You analyze customer reviews using only the supplied evidence.
Return the requested structured response without inventing facts or product details.
Write a concise overall summary and choose overall sentiment from the schema.
Return 3-6 concise recurring themes with evidence-based descriptions and approximate mention counts.
Return no more than five strengths, five weaknesses, and five actionable recommendations.
For every submitted review ID, return exactly one sentiment entry, with no missing, duplicate, or unknown IDs.
Use only the sentiment values permitted by the response schema.
"""


def build_model(provider: Provider):
    """Construct the selected chat model behind a sanitized failure boundary."""

    if provider == "google":
        if not os.getenv("GOOGLE_API_KEY"):
            raise AnalysisError("missing_api_key", "Set GOOGLE_API_KEY before using Gemini.")
        try:
            # Lazy imports let deployments install only the provider they use.
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=os.getenv("REVIEWINSIGHT_GOOGLE_MODEL", "gemini-2.5-flash-lite"),
                temperature=0,
                timeout=30,
                max_retries=0,
            )
        except AnalysisError:
            raise
        except Exception:
            raise AnalysisError("analysis_failed", "The AI provider could not be initialized.") from None

    if provider != "groq":
        raise AnalysisError("analysis_failed", "The selected AI provider is not supported.")
    if not os.getenv("GROQ_API_KEY"):
        raise AnalysisError("missing_api_key", "Set GROQ_API_KEY before using Groq.")
    try:
        # Keep provider package loading inside the same construction safeguard.
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=os.getenv("REVIEWINSIGHT_GROQ_MODEL", "llama-3.3-70b-versatile"),
            temperature=0,
            timeout=30,
            max_retries=0,
        )
    except AnalysisError:
        raise
    except Exception:
        raise AnalysisError("analysis_failed", "The AI provider could not be initialized.") from None


def analyze_reviews(
    reviews: list[Review],
    provider: Provider,
    *,
    agent_factory=create_agent,
    model_factory=build_model,
) -> AgentInsights:
    """Invoke one tool-free agent and require sentiments for exactly all reviews."""

    model = model_factory(provider)
    # One invocation returns the entire schema, avoiding divergent multi-agent
    # summaries and keeping all claims tied to the same submitted evidence.
    agent = agent_factory(
        model=model,
        tools=[],
        response_format=AgentInsights,
        system_prompt=SYSTEM_PROMPT,
    )
    payload = [
        {"id": review.id, "text": review.text, "rating": review.rating, "date": review.date}
        for review in reviews
    ]
    try:
        state = agent.invoke(
            {"messages": [{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]}
        )
        insights = AgentInsights.model_validate(state["structured_response"])
    except AnalysisError:
        raise
    except Exception:
        raise AnalysisError("analysis_failed", "The AI analysis could not be completed.") from None

    # Schema validation checks shape; this explicit set comparison additionally
    # rejects duplicate, invented, or omitted review identifiers.
    expected = {review.id for review in reviews}
    returned = [item.review_id for item in insights.review_sentiments]
    if len(returned) != len(set(returned)) or set(returned) != expected:
        raise AnalysisError("analysis_failed", "The AI analysis returned an incomplete result.")
    return insights
