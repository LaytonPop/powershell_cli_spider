"""Reusable core modules for the spider CLI and future agent integrations."""

from .cli import main
from .service import save_article

__all__ = ["main", "save_article"]
