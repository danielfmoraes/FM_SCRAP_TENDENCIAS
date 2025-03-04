# src/processors/__init__.py

from .text_processor import TextProcessor
from .translator import translate_text
from .categorizer import categorize_article

__all__ = [
    'TextProcessor',
    'translate_text',
    'categorize_article'
]