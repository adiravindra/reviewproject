"""Produce schema-validated insights through the required lazily loaded Groq integration.

Model construction and invocation errors are converted to the safe analysis
boundary, and returned sentiment IDs must exactly match input evidence.
"""

import json
import os

from langchain.agents import create_agent

from backend.app.credentials import get_groq_api_key
from backend.app.errors import AnalysisError
from backend.app.models import AgentInsights, Review

# The prompt explicitly forbids outside facts and asks for one structured result;
# deterministic metrics stay out of the model and are computed by the service.
SYSTEM_PROMPT = """You analyze customer reviews using only the supplied evidence.
Return the requested structured response without inventing facts or product details.
Write a concise overall summary and choose overall sentiment from the schema.
Return 3-6 concise recurring themes with evidence-based descriptions and approximate mention counts.
Provide a positive, neutral, negative, or mixed sentiment for every theme.
Use mixed only when one theme contains meaningful positive and negative evidence.
Return no more than five strengths, five weaknesses, and five actionable recommendations.
For every submitted review ID, return exactly one sentiment entry, with no missing, duplicate, or unknown IDs.
Keep each individual review sentiment positive, neutral, negative, or mixed.
Use mixed for an individual review only when it contains meaningful positive and negative evidence.
Use only the sentiment values permitted by the response schema.
"""


def build_model():
    """Construct the Groq chat model behind a sanitized failure boundary."""

    api_key = get_groq_api_key()
    try:
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=os.getenv("REVIEWINSIGHT_GROQ_MODEL", "llama-3.3-70b-versatile"),
            api_key=api_key,
            temperature=0,
            timeout=30,
            max_retries=0,
        )
    except AnalysisError:
        raise
    except (ImportError, ModuleNotFoundError):
        raise AnalysisError(
            "analysis_failed", "The AI provider could not be initialized."
        ) from None


def analyze_reviews(
    reviews: list[Review],
    *,
    agent_factory=create_agent,
    model_factory=build_model,
) -> AgentInsights:
    """Invoke one tool-free agent and require sentiments for exactly all reviews."""

    model = model_factory()
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
    except (RuntimeError, ValueError, TimeoutError):
        raise AnalysisError("analysis_failed", "The AI analysis could not be completed.") from None

    try:
        insights = AgentInsights.model_validate(state["structured_response"])
    except (ValueError, TypeError):
        raise AnalysisError(
            "model_output_invalid", "The AI analysis returned an invalid result."
        ) from None

    # Schema validation checks shape; this explicit set comparison additionally
    # rejects duplicate, invented, or omitted review identifiers.
    expected = {review.id for review in reviews}
    returned = [item.review_id for item in insights.review_sentiments]
    if len(returned) != len(set(returned)) or set(returned) != expected:
        raise AnalysisError(
            "model_output_invalid", "The AI analysis returned an invalid result."
        )
    return insights
