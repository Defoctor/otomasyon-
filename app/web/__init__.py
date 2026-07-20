from typing import Any


def create_web_app(*args: Any, **kwargs: Any) -> Any:
    """Import the application factory lazily to avoid service import cycles."""
    from app.web.app import create_web_app as factory

    return factory(*args, **kwargs)


__all__ = ["create_web_app"]
