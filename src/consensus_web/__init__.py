"""Web application package for consensus-engine."""

from .server import VERSION, create_server, evaluate_request, main

__all__ = ["VERSION", "create_server", "evaluate_request", "main"]
