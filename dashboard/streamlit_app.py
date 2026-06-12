import streamlit as st

from api_client import ApiClientError, fetch_health
from ui import backend_url_input, configure_page, render_error


configure_page("Overview")

st.title("ReviewInsight Dashboard")
st.write("Customer review intelligence workspace for analysis, themes, summaries, and business action items.")

api_base_url = backend_url_input()

st.subheader("Backend Connection")
try:
    health = fetch_health(api_base_url=api_base_url)
except ApiClientError as exc:
    render_error(exc)
else:
    status_col, project_col, version_col = st.columns(3)
    status_col.metric("Status", str(health["status"]).upper())
    project_col.metric("Project", health["project"])
    version_col.metric("Version", health["version"])

st.subheader("Analysis Workspace")
kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
kpi_col1.metric("Reviews Loaded", "Placeholder")
kpi_col2.metric("Positive Share", "Placeholder")
kpi_col3.metric("Top Theme", "Placeholder")
kpi_col4.metric("Open Actions", "Placeholder")

st.subheader("Pages")
st.write(
    "- Review Input: clean and validate single or batch review text.\n"
    "- Sentiment Analysis: classify one review with the current rule-based service.\n"
    "- Keyword / Themes: extract recurring words and business themes.\n"
    "- Summarization: summarize one or more reviews.\n"
    "- Insights Dashboard: combine sentiment, themes, complaints, summary, and action items.\n"
    "- API Health: check backend status during development."
)

st.caption("Use the sidebar navigation to move through the analysis workflow.")
