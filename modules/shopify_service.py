import asyncio
import logging
from typing import Optional, List
from bs4 import BeautifulSoup
from datetime import datetime
import validators

from core.models import BrandInsights, ErrorResponse, ProductModel
from core.utils import WebScraper, ShopifyDetector, URLUtils
from modules.extractors import (
    ProductExtractor, SocialMediaExtractor, ContactExtractor,
    PolicyExtractor, FAQExtractor, ImportantLinksExtractor, BrandExtractor
)
from config.settings import settings

logger = logging.getLogger(__name__)

def safe_get_attr(element, attr: str, default: str = '') -> str:
    """Safely get attribute from BeautifulSoup element"""
    if hasattr(element, 'get'):
        value = element.get(attr, default)
        return str(value) if value else default
    return default

class ShopifyInsightsService:
    """Main service for extracting Shopify store insights"""
    
    def __init__(self):
        self.scraper = WebScraper()
    
    async def fetch_insights(self, website_url: str) -> BrandInsights:
        """
        Main method to fetch comprehensive insights from a Shopify store
        
        Args:
            website_url: The URL of the Shopify store
            
        Returns:
            BrandInsights: Complete insights data
            
        Raises:
            Exception: For various error conditions (404, not Shopify, etc.)
        """
        # Validate URL
        if not self._validate_url(website_url):
            raise Exception("Invalid URL format")
        
        # Normalize URL
        normalized_url = self._normalize_url(website_url)
        
        async with WebScraper() as scraper:
            # Fetch main page
            logger.info(f"Fetching main page: {normalized_url}")
            html_content = await scraper.fetch_page(normalized_url)
            
            if not html_content:
                raise Exception("Failed to fetch website content")
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Verify it's a Shopify store
            if not ShopifyDetector.is_shopify_store(html_content, normalized_url):
                logger.warning(f"Website {normalized_url} may not be a Shopify store")
                # Continue anyway, but log warning
            
            # Initialize insights object
            insights = BrandInsights(website_url=normalized_url)
            
            # Extract basic brand information
            brand_extractor = BrandExtractor(soup, normalized_url)
            brand_info = brand_extractor.extract()
            
            insights.brand_name = brand_info['name']
            insights.brand_description = brand_info['description']
            insights.logo_url = brand_info['logo_url']
            insights.currencies_supported = brand_info['currencies']
            insights.payment_methods = brand_info['payment_methods']
            
            # Extract hero products (from homepage)
            logger.info("Extracting hero products from homepage")
            product_extractor = ProductExtractor(soup, normalized_url)
            insights.hero_products = product_extractor.extract()
            
            # Extract social media handles
            logger.info("Extracting social media handles")
            social_extractor = SocialMediaExtractor(soup, normalized_url)
            insights.social_handles = social_extractor.extract()
            
            # Extract contact details
            logger.info("Extracting contact details")
            contact_extractor = ContactExtractor(soup, normalized_url)
            insights.contact_details = contact_extractor.extract()
            
            # Extract policies
            logger.info("Extracting policies")
            policy_extractor = PolicyExtractor(soup, normalized_url)
            policies = policy_extractor.extract()
            
            insights.privacy_policy = policies['privacy_policy']
            insights.return_policy = policies['return_policy']
            insights.refund_policy = policies['refund_policy']
            insights.terms_of_service = policies['terms_of_service']
            
            # Extract FAQs
            logger.info("Extracting FAQs")
            faq_extractor = FAQExtractor(soup, normalized_url)
            insights.faqs = faq_extractor.extract()
            
            # Extract important links
            logger.info("Extracting important links")
            links_extractor = ImportantLinksExtractor(soup, normalized_url)
            insights.important_links = links_extractor.extract()
            
            # Fetch complete product catalog
            logger.info("Fetching complete product catalog")
            catalog_products = await self._fetch_product_catalog(scraper, normalized_url, soup)
            insights.product_catalog = catalog_products
            insights.total_products = len(catalog_products)
            
            # Set timestamp
            insights.scraped_at = datetime.now()
            
            logger.info(f"Successfully extracted insights for {normalized_url}")
            return insights
    
    async def _fetch_product_catalog(self, scraper: WebScraper, base_url: str, main_soup: BeautifulSoup) -> List[ProductModel]:
        """
        Fetch complete product catalog by discovering and scraping product pages
        """
        all_products = []
        
        # Common Shopify product page patterns
        product_urls = await self._discover_product_urls(scraper, base_url, main_soup)
        
        # Limit concurrent requests to avoid overwhelming the server
        semaphore = asyncio.Semaphore(5)
        
        async def fetch_product_page(url):
            async with semaphore:
                try:
                    html_content = await scraper.fetch_page(url)
                    if html_content:
                        soup = BeautifulSoup(html_content, 'html.parser')
                        extractor = ProductExtractor(soup, url)
                        return extractor.extract()
                except Exception as e:
                    logger.error(f"Error fetching product page {url}: {str(e)}")
                return []
        
        # Fetch product pages concurrently
        if product_urls:
            logger.info(f"Fetching {len(product_urls)} product pages")
            tasks = [fetch_product_page(url) for url in product_urls[:50]]  # Limit to 50 pages
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_products.extend(result)
        
        # Remove duplicates
        unique_products = self._deduplicate_products(all_products)
        
        return unique_products
    
    async def _discover_product_urls(self, scraper: WebScraper, base_url: str, main_soup: BeautifulSoup) -> List[str]:
        """
        Discover product URLs from various sources
        """
        product_urls = set()
        
        # 1. Try collections page
        collections_urls = [
            f"{base_url}/collections/all",
            f"{base_url}/collections",
            f"{base_url}/products"
        ]
        
        for collections_url in collections_urls:
            try:
                html_content = await scraper.fetch_page(collections_url)
                if html_content:
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Find product links
                    product_links = soup.find_all('a', href=True)
                    for link in product_links[:10]:  # Limit to first 10 product pages
                        href_attr = safe_get_attr(link, 'href')
                        if href_attr:
                            product_url = URLUtils.normalize_url(href_attr, base_url)
                            logger.info(f"Fetching product page: {product_url}")
                            product_content = await scraper.fetch_page(product_url)
                            if product_content:
                                product_soup = BeautifulSoup(product_content, 'html.parser')
                                product_extractor = ProductExtractor(product_soup, product_url)
                                page_products = product_extractor.extract()
                                product_urls.update(page_products)
                    
                    # If we found products, we can break
                    if product_urls:
                        break
                        
            except Exception as e:
                logger.debug(f"Error fetching collections page {collections_url}: {str(e)}")
                continue
        
        # 2. Extract from main page
        main_product_links = main_soup.find_all('a', href=True)
        for link in main_product_links:
            href_attr = safe_get_attr(link, 'href')
            if href_attr and '/products/' in href_attr:
                full_url = URLUtils.normalize_url(href_attr, base_url)
                product_urls.add(full_url)
        
        # 3. Try sitemap (if accessible)
        try:
            sitemap_url = f"{base_url}/sitemap.xml"
            sitemap_content = await scraper.fetch_page(sitemap_url)
            if sitemap_content:
                # Parse sitemap for product URLs
                from xml.etree import ElementTree as ET
                root = ET.fromstring(sitemap_content)
                
                for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                    loc_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc_elem is not None and loc_elem.text and '/products/' in loc_elem.text:
                        product_urls.add(loc_elem.text)
                        
        except Exception as e:
            logger.debug(f"Error fetching sitemap: {str(e)}")
        
        return list(product_urls)[:100]  # Limit to 100 URLs
    
    def _validate_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            result = validators.url(url)
            return result is True  # validators returns True for valid URLs
        except Exception:
            return False
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL (ensure https, remove trailing slash)"""
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        return url.rstrip('/')
    
    def _deduplicate_products(self, products: List[ProductModel]) -> List[ProductModel]:
        """Remove duplicate products based on name and URL"""
        seen = set()
        unique_products = []
        
        for product in products:
            # Create a key based on name and URL
            key = (product.name, product.product_url)
            if key not in seen:
                seen.add(key)
                unique_products.append(product)
        
        return unique_products

class ShopifyInsightsServiceSync:
    """Synchronous version of the insights service for compatibility"""
    
    def __init__(self):
        self.async_service = ShopifyInsightsService()
    
    def fetch_insights(self, website_url: str) -> BrandInsights:
        """Synchronous wrapper for the async fetch_insights method"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.async_service.fetch_insights(website_url))
        finally:
            loop.close()