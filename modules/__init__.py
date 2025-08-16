"""
Modules package for Shopify insights extraction.

This package contains specialized extractors for different types of data:
- product_extractor: Product catalog and individual product extraction
- hero_product_extractor: Homepage featured/hero products
- privacy_policy_extractor: Privacy policies and legal documents
- extractors: Other extractors (social media, contacts, FAQs, etc.)
"""

from .product_extractor import (
    ProductExtractor, 
    ProductCatalogExtractor, 
    SingleProductExtractor
)
from .hero_product_extractor import HeroProductExtractor
from .privacy_policy_extractor import (
    PrivacyPolicyExtractor, 
    PolicyDetailExtractor
)
from .base_extractor import BaseExtractor
from .shopify_service import ShopifyInsightsService

__all__ = [
    'ProductExtractor',
    'ProductCatalogExtractor', 
    'SingleProductExtractor',
    'HeroProductExtractor',
    'PrivacyPolicyExtractor',
    'PolicyDetailExtractor',
    'BaseExtractor',
    'ShopifyInsightsService'
]