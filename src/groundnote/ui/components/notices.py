"""Consistent notice rendering."""

from __future__ import annotations

import streamlit as st

from groundnote.ui.errors import MessageSeverity, UiMessage
from groundnote.ui.formatting import format_warning


def render_message(message: UiMessage) -> None:
    """Render one mapped message using its explicit severity and remediation."""
    body = f"**{message.title}**\n\n{message.message}"
    if message.remediation:
        body = f"{body}\n\n{message.remediation}"
    if message.severity is MessageSeverity.INFO:
        st.info(body)
    elif message.severity is MessageSeverity.WARNING:
        st.warning(body)
    else:
        st.error(body)


def render_warnings(warnings: list[str]) -> None:
    """Render safe warning codes without technical payloads."""
    if not warnings:
        return
    with st.expander("Warnings", expanded=False):
        for warning in warnings:
            st.write(f"- {format_warning(warning)}")


def render_local_notice() -> None:
    """Render the concise persistent local-model disclaimer."""
    st.caption(
        "GroundNote runs locally and answers from indexed documents. Local models can make "
        "mistakes—verify important information against the cited sources."
    )
