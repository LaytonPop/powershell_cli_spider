"""Reusable core modules for the spider CLI and future agent integrations."""

from .cli import VERSION, main
from .service import SaveResult, save_article

__version__ = VERSION

__all__ = ["VERSION", "SaveResult", "__version__", "main", "save_article"]
