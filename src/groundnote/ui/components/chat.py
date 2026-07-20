"""Single-turn question input and answer display."""

from __future__ import annotations

import streamlit as st

from groundnote.ui.components.citations import render_citations
from groundnote.ui.components.notices import render_warnings
from groundnote.ui.formatting import format_duration
from groundnote.ui.models import QuestionOutcome


def render_question_input(maximum_characters: int) -> str | None:
    """Render one independent chat input."""
    return st.chat_input(
        "Ask a question about your indexed documents",
        max_chars=maximum_characters,
    )


def render_question_outcome(outcome: QuestionOutcome) -> None:
    """Render only the current session's latest single-turn result."""
    answer = outcome.answer
    with st.chat_message("user"):
        st.markdown(outcome.question)
    with st.chat_message("assistant"):
        if answer.insufficient_evidence:
            st.info("No relevant evidence was found in the selected indexed documents.")
        elif answer.grounded:
            st.success(f"Grounded answer · {len(answer.citations)} source(s)")
        st.markdown(answer.answer)
        render_citations(answer.citations)
        render_warnings(answer.warnings)
        st.caption(
            f"Local model: {answer.model} · Response time: {format_duration(answer.duration_ms)}"
        )
