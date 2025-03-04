# src/scrapers/__init__.py

from .abrafac import AbrafacScraper
from .infrafm import InfraFMScraper
from .google_scholar import GoogleScholarScraper

__all__ = [
    'AbrafacScraper',
    'InfraFMScraper',
    'GoogleScholarScraper'
]