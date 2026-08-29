# core/context.py
import contextvars
from typing import Optional

# Context variable to hold FastMCP session ID for the life of a single request.
_fastmcp_session_id = contextvars.ContextVar("fastmcp_session_id", default=None)


def get_fastmcp_session_id() -> Optional[str]:
    """
    Retrieve the FastMCP session ID for the current request context.
    This is called by authentication layer to get the current session.
    """
    return _fastmcp_session_id.get()


def set_fastmcp_session_id(session_id: Optional[str]):
    """
    Set or clear the FastMCP session ID for the current request context.
    This is called when a FastMCP request starts.
    """
    _fastmcp_session_id.set(session_id)
