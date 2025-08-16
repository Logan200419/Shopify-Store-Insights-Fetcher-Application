from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
import json
import re
import logging
from urllib.parse import urljoin, urlparse
from core.models import ProductModel, SocialHandles, ContactDetails, PolicyModel, FAQModel, ImportantLinks
from core.utils import WebScraper, ShopifyDetector, URLUtils, TextCleaner

logger = logging.getLogger(__name__)

def safe_get_attr(element, attr: str, default: str = '') -> str:
    """Safely get attribute from BeautifulSoup element"""
    if hasattr(element, 'get'):
        value = element.get(attr, default)
        return str(value) if value else default
    return default

def safe_get_text(element, strip: bool = True) -> str:
    """Safely get text from BeautifulSoup element"""
    if element and hasattr(element, 'get_text'):
        return element.get_text(strip=strip)
    return str(element) if element else ''

def safe_find_all(element, *args, **kwargs):
    """Safely call find_all on BeautifulSoup element"""
    if hasattr(element, 'find_all'):
        return element.find_all(*args, **kwargs)
    return []

def safe_find(element, *args, **kwargs):
    """Safely call find on BeautifulSoup element"""
    if hasattr(element, 'find'):
        return element.find(*args, **kwargs)
    return None

class BaseExtractor(ABC):
    """Abstract base class for data extractors"""
    
    def __init__(self, soup: BeautifulSoup, base_url: str):
        self.soup = soup
        self.base_url = base_url
        self.domain = URLUtils.get_domain(base_url)
    
    @abstractmethod
    def extract(self) -> Any:
        """Extract specific data from the soup"""
        pass
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        return TextCleaner.clean_text(text) if text else ""
    
    def _resolve_url(self, url: str) -> str:
        """Resolve relative URLs to absolute URLs"""
        if not url:
            return ""
        return urljoin(self.base_url, url)
    
    def _extract_json_ld(self) -> List[Dict]:
        """Extract JSON-LD structured data"""
        json_ld_scripts = safe_find_all(self.soup, 'script', {'type': 'application/ld+json'})
        structured_data = []
        
        for script in json_ld_scripts:
            try:
                data = json.loads(safe_get_text(script))
                if isinstance(data, list):
                    structured_data.extend(data)
                else:
                    structured_data.append(data)
            except json.JSONDecodeError:
                continue
        
        return structured_data
