import streamlit as st

from api_client import ApiClientError, fetch_health
from ui import backend_url_input, configure_page, render_error


configure_page("API Health")

st.title("API Health")
st.write("Check whether the FastAPI backend is reachable from Streamlit.")

api_base_url = backend_url_input()

if st.button("Check Backend", type="primary"):
    try:
        health = fetch_health(api_base_url=api_base_url)
    except ApiClientError as exc:
        render_error(exc)
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Status", str(health["status"]).upper())
        col2.metric("Project", health["project"])
        col3.metric("Version", health["version"])
        st.success("Backend is reachable.")
