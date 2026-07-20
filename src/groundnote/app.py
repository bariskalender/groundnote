"""GroundNote Streamlit application entrypoint."""

from __future__ import annotations

import streamlit as st

from groundnote.ui import ApplicationContext, build_application_context
from groundnote.ui.components.header import render_header
from groundnote.ui.components.notices import render_local_notice, render_message
from groundnote.ui.components.sidebar import render_sidebar
from groundnote.ui.errors import DatabaseBootstrapError, map_exception
from groundnote.ui.pages.ask import render_ask_page
from groundnote.ui.pages.documents import render_documents_page
from groundnote.ui.state import initialize_session_state


@st.cache_resource(show_spinner=False)
def get_application_context() -> ApplicationContext:
    """Cache stateless service composition, never private request data or models."""
    return build_application_context()


def main() -> None:
    """Render the Phase 7 local document and grounded Q&A workflow."""
    st.set_page_config(
        page_title="GroundNote",
        page_icon="📓",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    initialize_session_state(st.session_state)
    render_header()
    try:
        context = get_application_context()
    except Exception as exc:
        error = DatabaseBootstrapError("Application bootstrap failed.")
        error.__cause__ = exc
        render_message(map_exception(error))
        return
    page = render_sidebar(context)
    if page == "Documents":
        render_documents_page(context)
    else:
        render_ask_page(context)
    render_local_notice()


if __name__ == "__main__":
    main()
