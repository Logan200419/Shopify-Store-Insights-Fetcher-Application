import asyncio
import logging
from typing import Optional, List
from bs4 import BeautifulSoup
from datetime import datetime
import validators

from core.models import BrandInsights, ErrorResponse, ProductModel
from core.utils import WebScraper, ShopifyDetector, URLUtils
from modules.product_extractor import ProductExtractor, ProductCatalogExtractor
from modules.hero_product_extractor import HeroProductExtractor
from modules.privacy_policy_extractor import PrivacyPolicyExtractor
from modules.extractors import (
    SocialMediaExtractor, ContactExtractor,
    PolicyExtractor, FAQExtractor, ImportantLinksExtractor, BrandExtractor
)
from config.settings import settings
from database.models import db_manager

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
            
            # Extract hero products (by loading all products and filtering by tags)
            logger.info("Extracting hero products by loading all products and filtering by homepage tags")
            hero_extractor = HeroProductExtractor(soup, normalized_url, scraper)
            insights.hero_products = await hero_extractor.extract_async()
            
            # Extract social media handles
            logger.info("Extracting social media handles")
            social_extractor = SocialMediaExtractor(soup, normalized_url)
            insights.social_handles = social_extractor.extract()
            
            # Extract contact details
            logger.info("Extracting contact details")
            contact_extractor = ContactExtractor(soup, normalized_url)
            insights.contact_details = contact_extractor.extract()
            
            # Extract policies using the new privacy policy extractor
            logger.info("Extracting policies")
            privacy_extractor = PrivacyPolicyExtractor(soup, normalized_url)
            all_policies = privacy_extractor.extract()
            
            # Organize policies by type
            for policy in all_policies:
                policy_title_lower = policy.title.lower()
                if 'privacy' in policy_title_lower:
                    insights.privacy_policy = policy
                elif 'return' in policy_title_lower:
                    insights.return_policy = policy
                elif 'refund' in policy_title_lower:
                    insights.refund_policy = policy
                elif 'terms' in policy_title_lower or 'conditions' in policy_title_lower:
                    insights.terms_of_service = policy
            
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
            
            # Save insights to database
            try:
                logger.info("Saving insights to database")
                insights_dict = insights.model_dump()
                store_id = db_manager.save_store_insights(insights_dict)
                logger.info(f"Successfully saved insights to database with store ID: {store_id}")
            except Exception as e:
                logger.error(f"Failed to save insights to database: {e}")
                # Continue without failing the request
            
            logger.info(f"Successfully extracted insights for {normalized_url}")
            return insights
    
    async def _fetch_product_catalog(self, scraper: WebScraper, base_url: str, main_soup: BeautifulSoup) -> List[ProductModel]:
        """
        Fetch complete product catalog using Shopify's products.json API endpoint
        """
        all_products = []
        
        # Try to fetch products using Shopify's JSON API
        products_json_url = f"{base_url}/products.json"
        logger.info(f"Fetching products from JSON API: {products_json_url}")
        
        try:
            json_content = await scraper.fetch_page(products_json_url)
            if json_content:
                import json
                products_data = json.loads(json_content)
                
                if 'products' in products_data:
                    logger.info(f"Found {len(products_data['products'])} products in JSON API")
                    
                    for product_data in products_data['products']:
                        product = self._parse_shopify_product_json(product_data, base_url)
                        if product:
                            all_products.append(product)
                
                # Handle pagination - Shopify limits to 250 products per page
                page = 1
                while len(products_data.get('products', [])) == 250:  # Max products per page
                    page += 1
                    paginated_url = f"{base_url}/products.json?page={page}"
                    logger.info(f"Fetching page {page} of products")
                    
                    try:
                        paginated_content = await scraper.fetch_page(paginated_url)
                        if paginated_content:
                            paginated_data = json.loads(paginated_content)
                            if 'products' in paginated_data and paginated_data['products']:
                                for product_data in paginated_data['products']:
                                    product = self._parse_shopify_product_json(product_data, base_url)
                                    if product:
                                        all_products.append(product)
                                products_data = paginated_data
                            else:
                                break
                        else:
                            break
                    except Exception as e:
                        logger.warning(f"Error fetching page {page}: {str(e)}")
                        break
                        
        except Exception as e:
            logger.warning(f"Error fetching products from JSON API: {str(e)}")
            # Fallback to HTML scraping if JSON API fails
            logger.info("Falling back to HTML scraping method")
            return await self._fetch_product_catalog_fallback(scraper, base_url, main_soup)
        
        logger.info(f"Successfully fetched {len(all_products)} products from JSON API")
        return all_products
    
    def _parse_shopify_product_json(self, product_data: dict, base_url: str) -> Optional[ProductModel]:
        """Parse a single product from Shopify's JSON API response"""
        try:
            # Extract basic product info
            name = product_data.get('title', '')
            if not name:
                return None
            
            description = product_data.get('body_html', '')
            handle = product_data.get('handle', '')
            product_url = f"{base_url}/products/{handle}" if handle else None
            
            # Extract images
            images = product_data.get('images', [])
            image_url = images[0].get('src') if images else None
            
            # Extract variants for pricing
            variants = product_data.get('variants', [])
            price = None
            original_price = None
            availability = "In Stock"
            
            if variants:
                first_variant = variants[0]
                price_value = first_variant.get('price')
                compare_price = first_variant.get('compare_at_price')
                available = first_variant.get('available', True)
                
                if price_value:
                    price = f"${price_value}"
                if compare_price and float(compare_price) > float(price_value or 0):
                    original_price = f"${compare_price}"
                
                availability = "In Stock" if available else "Out of Stock"
            
            # Extract tags
            tags = product_data.get('tags', [])
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(',')]
            
            return ProductModel(
                name=name,
                price=price,
                original_price=original_price,
                image_url=image_url,
                product_url=product_url,
                availability=availability,
                description=description[:500] if description else None,  # Limit description length
                tags=tags[:10] if tags else None  # Limit number of tags
            )
            
        except Exception as e:
            logger.error(f"Error parsing product JSON: {str(e)}")
            return None
    
    async def _fetch_product_catalog_fallback(self, scraper: WebScraper, base_url: str, main_soup: BeautifulSoup) -> List[ProductModel]:
        """
        Fallback method using HTML scraping when JSON API fails
        """
        all_products = []
        
        # Extract products from main page first using the catalog extractor
        catalog_extractor = ProductCatalogExtractor(main_soup, base_url, max_products=50)
        main_page_products = catalog_extractor.extract()
        all_products.extend(main_page_products)
        
        # Try to discover more product URLs
        product_urls = await self._discover_product_urls(scraper, base_url, main_soup)
        
        # Limit concurrent requests to avoid overwhelming the server
        semaphore = asyncio.Semaphore(3)  # Reduced concurrency for fallback
        
        async def fetch_product_page(url):
            async with semaphore:
                try:
                    html_content = await scraper.fetch_page(url)
                    if html_content:
                        soup = BeautifulSoup(html_content, 'html.parser')
                        extractor = ProductCatalogExtractor(soup, url, max_products=10)
                        return extractor.extract()
                except Exception as e:
                    logger.error(f"Error fetching product page {url}: {str(e)}")
                return []
        
        # Fetch product pages concurrently (limited number for fallback)
        if product_urls:
            logger.info(f"Fallback: Fetching {min(len(product_urls), 20)} product pages")
            tasks = [fetch_product_page(url) for url in product_urls[:20]]  # Limit to 20 pages for fallback
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_products.extend(result)
        
        # Remove duplicates
        unique_products = self._deduplicate_products(all_products)
        
        logger.info(f"Fallback method fetched {len(unique_products)} products")
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
                    for link in product_links:
                        href_attr = safe_get_attr(link, 'href')
                        if href_attr and '/products/' in href_attr:
                            product_url = URLUtils.normalize_url(href_attr, base_url)
                            product_urls.add(product_url)
                    
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