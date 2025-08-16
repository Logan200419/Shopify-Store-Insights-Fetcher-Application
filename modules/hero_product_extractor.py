"""
Hero products extraction module for Shopify stores
Handles extraction of featured/hero products by loading all products and filtering by tags
"""
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
import json
import re
import logging
import asyncio
import aiohttp
from core.models import ProductModel
from core.utils import WebScraper
from .base_extractor import BaseExtractor, safe_get_attr, safe_get_text, safe_find_all, safe_find

logger = logging.getLogger(__name__)

class HeroProductExtractor(BaseExtractor):
    """Extract hero/featured products by loading all products and filtering by homepage tags"""
    
    def __init__(self, soup: BeautifulSoup, base_url: str, scraper: Optional[WebScraper] = None):
        super().__init__(soup, base_url)
        self.scraper = scraper or WebScraper()
    
    async def extract_async(self) -> List[ProductModel]:
        """Extract hero products by loading all products and filtering by tags (async version)"""
        try:
            # First, try to load all products from /products.json
            all_products = await self._load_all_products_from_json()
            
            if not all_products:
                # Fallback to HTML scraping if JSON API doesn't work
                logger.info("JSON API failed, falling back to HTML scraping for hero products")
                all_products = await self._load_all_products_from_html()
            
            # Filter products for homepage/hero tags
            hero_products = self._filter_hero_products_by_tags(all_products)
            
            if not hero_products:
                # If no tagged hero products found, use position-based fallback
                logger.info("No tagged hero products found, using position-based detection")
                hero_products = self._extract_hero_products_by_position()
            
            logger.info(f"Extracted {len(hero_products)} hero products")
            
            # If we have homepage-tagged products, return more of them
            if any('homepage' in (product.tags or []) for product in hero_products):
                return hero_products[:10]  # Return up to 10 homepage products
            else:
                return hero_products[:6]  # Default limit for other hero products
            
        except Exception as e:
            logger.error(f"Error in async hero product extraction: {str(e)}")
            # Fallback to synchronous position-based extraction
            return self._extract_hero_products_by_position()
    
    def extract(self) -> List[ProductModel]:
        """Extract hero products (synchronous version)"""
        try:
            # Run the async version in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.extract_async())
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in hero product extraction: {str(e)}")
            # Fallback to position-based extraction
            return self._extract_hero_products_by_position()
    
    async def _load_all_products_from_json(self) -> List[ProductModel]:
        """Load all products from the Shopify /products.json endpoint"""
        products = []
        page = 1
        max_pages = 10  # Prevent infinite loops
        
        try:
            while page <= max_pages:
                # Construct products.json URL with pagination
                products_url = f"{self.base_url.rstrip('/')}/products.json"
                if page > 1:
                    products_url += f"?page={page}"
                
                logger.info(f"Fetching products from {products_url}")
                
                # Fetch products JSON
                response_data = await self._fetch_json_data(products_url)
                if not response_data or 'products' not in response_data:
                    break
                
                page_products = response_data.get('products', [])
                if not page_products:
                    break
                
                # Convert JSON products to ProductModel objects
                for product_data in page_products:
                    product = self._convert_json_to_product_model(product_data)
                    if product:
                        products.append(product)
                
                # Check if there are more pages
                if len(page_products) < 50:  # Shopify default page size
                    break
                
                page += 1
            
            logger.info(f"Loaded {len(products)} products from JSON API")
            return products
            
        except Exception as e:
            logger.error(f"Error loading products from JSON: {str(e)}")
            return []
    
    async def _fetch_json_data(self, url: str) -> Optional[Dict]:
        """Fetch JSON data from URL"""
        try:
            html_content = await self.scraper.fetch_page(url)
            if html_content:
                return json.loads(html_content)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from {url}: {str(e)}")
        except Exception as e:
            logger.error(f"Error fetching JSON from {url}: {str(e)}")
        return None
    
    def _convert_json_to_product_model(self, product_data: Dict) -> Optional[ProductModel]:
        """Convert Shopify JSON product data to ProductModel"""
        try:
            name = product_data.get('title', '')
            if not name:
                return None
            
            # Extract basic info
            handle = product_data.get('handle', '')
            product_url = f"{self.base_url.rstrip('/')}/products/{handle}" if handle else None
            description = product_data.get('body_html', '')
            
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
            
            # Extract and process tags
            tags = product_data.get('tags', [])
            if isinstance(tags, str):
                tags = [tag.strip().lower() for tag in tags.split(',')]
            else:
                tags = [str(tag).strip().lower() for tag in tags]
            
            return ProductModel(
                name=self._clean_text(name),
                price=price,
                original_price=original_price,
                image_url=self._resolve_url(image_url) if image_url else None,
                product_url=product_url,
                availability=availability,
                description=self._clean_text(description)[:200] if description else None,
                tags=tags[:10] if tags else None
            )
            
        except Exception as e:
            logger.error(f"Error converting JSON product to model: {str(e)}")
            return None
    
    def _filter_hero_products_by_tags(self, products: List[ProductModel]) -> List[ProductModel]:
        """Filter products that have homepage/hero related tags, prioritizing 'homepage' tag"""
        hero_products = []
        homepage_products = []
        
        # Define hero/homepage related tags
        hero_tags = {
            'homepage', 'hero', 'featured', 'main', 'highlight', 'spotlight',
            'bestseller', 'best seller', 'best-seller', 'top seller', 'top-seller',
            'trending', 'popular', 'most popular', 'staff pick', 'staff-pick',
            'editor choice', 'editor-choice', 'recommended', 'must have', 'must-have',
            'signature', 'flagship', 'star product', 'star-product',
            'front page', 'front-page', 'home', 'banner', 'promo', 'promotional'
        }
        
        for product in products:
            if product.tags:
                # Check if any product tag matches hero tags
                product_tags_set = set(product.tags)
                
                # Prioritize products specifically tagged with "homepage"
                if 'homepage' in product_tags_set:
                    homepage_products.append(product)
                    logger.info(f"Found homepage tagged product: {product.name} (tags: {product.tags})")
                elif hero_tags.intersection(product_tags_set):
                    hero_products.append(product)
                    logger.debug(f"Found hero product by tag: {product.name} (tags: {product.tags})")
        
        # Return homepage products first, then other hero products
        all_hero_products = homepage_products + hero_products
        
        # If we found products with homepage tag, prioritize them
        if homepage_products:
            logger.info(f"Found {len(homepage_products)} products with 'homepage' tag, {len(hero_products)} other hero products")
            # Return all homepage products plus some additional hero products if needed
            return all_hero_products
        elif hero_products:
            logger.info(f"No 'homepage' tagged products found, returning {len(hero_products)} other hero products")
            return hero_products
        else:
            logger.info("No hero or homepage tagged products found")
            return []
        
        # If we found tagged hero products, sort by relevance
        if hero_products:
            hero_products = self._sort_hero_products_by_relevance(hero_products, hero_tags)
        
        return hero_products
    
    def _sort_hero_products_by_relevance(self, products: List[ProductModel], hero_tags: set) -> List[ProductModel]:
        """Sort hero products by tag relevance and completeness, prioritizing 'homepage' tag"""
        scored_products = []
        
        for product in products:
            score = 0
            
            if product.tags:
                # Score based on number of matching hero tags
                matching_tags = hero_tags.intersection(set(product.tags))
                score += len(matching_tags) * 10
                
                # Highest boost for homepage tag
                if 'homepage' in product.tags:
                    score += 50  # Highest priority
                # Boost for other specific high-value tags
                elif 'hero' in product.tags:
                    score += 30
                elif 'featured' in product.tags:
                    score += 20
                elif any(tag in product.tags for tag in ['bestseller', 'best seller', 'best-seller']):
                    score += 15
            
            # Boost for products with complete information
            if product.image_url:
                score += 10
            if product.price:
                score += 5
            if product.description:
                score += 5
            
            scored_products.append((score, product))
        
        # Sort by score descending
        scored_products.sort(key=lambda x: x[0], reverse=True)
        return [product for score, product in scored_products]
    
    async def _load_all_products_from_html(self) -> List[ProductModel]:
        """Fallback method to load products by scraping HTML pages"""
        products = []
        
        try:
            # Import ProductCatalogExtractor to avoid circular imports
            from .product_extractor import ProductCatalogExtractor
            
            # Use the existing product catalog extractor
            catalog_extractor = ProductCatalogExtractor(self.soup, self.base_url, max_products=100)
            products = catalog_extractor.extract()
            
            logger.info(f"Loaded {len(products)} products from HTML scraping")
            return products
            
        except Exception as e:
            logger.error(f"Error loading products from HTML: {str(e)}")
            return []
    
    def _extract_hero_products_by_position(self) -> List[ProductModel]:
        """Fallback method to extract hero products based on page position"""
        hero_products = []
        
        try:
            # Try different methods to extract hero products by position
            hero_products.extend(self._extract_from_hero_sections())
            hero_products.extend(self._extract_from_featured_sections())
            hero_products.extend(self._extract_from_banners())
            hero_products.extend(self._extract_from_carousel())
            hero_products.extend(self._extract_from_homepage_collections())
            
            # Remove duplicates and limit to most prominent products
            unique_products = self._deduplicate_products(hero_products)
            
            # Prioritize products based on position and prominence
            prioritized_products = self._prioritize_hero_products(unique_products)
            
            return prioritized_products[:6]  # Limit to top 6 hero products
            
        except Exception as e:
            logger.error(f"Error in position-based hero product extraction: {str(e)}")
            return []
    
    def _extract_from_hero_sections(self) -> List[ProductModel]:
        """Extract products from hero sections"""
        products = []
        
        # Common hero section selectors
        hero_selectors = [
            '.hero',
            '.hero-section',
            '.banner-hero',
            '.main-hero',
            '.homepage-hero',
            '[data-section-type="hero"]',
            '.slideshow',
            '.hero-banner'
        ]
        
        for selector in hero_selectors:
            try:
                hero_sections = self.soup.select(selector)
                for section in hero_sections:
                    section_products = self._extract_products_from_hero_section(section)
                    products.extend(section_products)
            except Exception as e:
                logger.debug(f"Error with hero selector {selector}: {str(e)}")
                continue
        
        return products
    
    def _extract_from_featured_sections(self) -> List[ProductModel]:
        """Extract products from featured product sections"""
        products = []
        
        # Featured product selectors
        featured_selectors = [
            '.featured-products',
            '.featured-collection',
            '.homepage-featured',
            '[data-section-type="featured-products"]',
            '[data-section-type="featured-collection"]',
            '.featured',
            '.best-sellers',
            '.trending-products'
        ]
        
        for selector in featured_selectors:
            try:
                sections = self.soup.select(selector)
                for section in sections:
                    section_products = self._extract_products_from_section(section)
                    products.extend(section_products)
            except Exception as e:
                logger.debug(f"Error with featured selector {selector}: {str(e)}")
                continue
        
        return products
    
    def _extract_from_banners(self) -> List[ProductModel]:
        """Extract products from promotional banners"""
        products = []
        
        # Banner selectors
        banner_selectors = [
            '.banner',
            '.promo-banner',
            '.product-banner',
            '.promotional-banner',
            '.homepage-banner',
            '.collection-banner'
        ]
        
        for selector in banner_selectors:
            try:
                banners = self.soup.select(selector)
                for banner in banners:
                    # Look for product links within banners
                    product_links = safe_find_all(banner, 'a', href=re.compile(r'/products/'))
                    for link in product_links:
                        product = self._extract_product_from_link(link)
                        if product:
                            products.append(product)
            except Exception as e:
                logger.debug(f"Error with banner selector {selector}: {str(e)}")
                continue
        
        return products
    
    def _extract_from_carousel(self) -> List[ProductModel]:
        """Extract products from carousel/slider sections"""
        products = []
        
        # Carousel selectors
        carousel_selectors = [
            '.carousel',
            '.slider',
            '.slideshow',
            '.product-slider',
            '.featured-slider',
            '[data-slick]',
            '[data-carousel]',
            '.swiper-container'
        ]
        
        for selector in carousel_selectors:
            try:
                carousels = self.soup.select(selector)
                for carousel in carousels:
                    section_products = self._extract_products_from_section(carousel)
                    products.extend(section_products)
            except Exception as e:
                logger.debug(f"Error with carousel selector {selector}: {str(e)}")
                continue
        
        return products
    
    def _extract_from_homepage_collections(self) -> List[ProductModel]:
        """Extract products from homepage collection showcases"""
        products = []
        
        # Homepage collection selectors
        collection_selectors = [
            '.homepage-collections',
            '.collection-list',
            '.featured-collections',
            '.collection-grid',
            '.collections-showcase'
        ]
        
        for selector in collection_selectors:
            try:
                sections = self.soup.select(selector)
                for section in sections:
                    # Look for individual collection items
                    collection_items = safe_find_all(section, class_=re.compile(r'collection'))
                    for item in collection_items:
                        item_products = self._extract_products_from_collection_item(item)
                        products.extend(item_products)
            except Exception as e:
                logger.debug(f"Error with collection selector {selector}: {str(e)}")
                continue
        
        return products
    
    def _extract_products_from_hero_section(self, section) -> List[ProductModel]:
        """Extract products from a hero section"""
        products = []
        
        # Look for direct product elements
        product_selectors = [
            '.product',
            '.product-item',
            '.product-card',
            '[data-product]'
        ]
        
        for selector in product_selectors:
            items = safe_find_all(section, 'css', selector)
            for item in items:
                product = self._extract_product_from_element(item)
                if product:
                    products.append(product)
        
        # Look for product links
        product_links = safe_find_all(section, 'a', href=re.compile(r'/products/'))
        for link in product_links:
            product = self._extract_product_from_link(link)
            if product:
                products.append(product)
        
        return products
    
    def _extract_products_from_section(self, section) -> List[ProductModel]:
        """Extract products from any section"""
        products = []
        
        # Standard product selectors
        product_selectors = [
            '.product-item',
            '.product-card',
            '.product',
            '[data-product]',
            '.featured-product'
        ]
        
        for selector in product_selectors:
            items = safe_find_all(section, 'css', selector)
            for item in items:
                product = self._extract_product_from_element(item)
                if product:
                    products.append(product)
        
        return products
    
    def _extract_products_from_collection_item(self, item) -> List[ProductModel]:
        """Extract products from collection showcase items"""
        products = []
        
        # Look for featured products within collection items
        product_items = safe_find_all(item, class_=re.compile(r'product'))
        for product_item in product_items:
            product = self._extract_product_from_element(product_item)
            if product:
                products.append(product)
        
        return products
    
    def _extract_product_from_link(self, link) -> Optional[ProductModel]:
        """Extract product information from a product link"""
        try:
            href = safe_get_attr(link, 'href')
            if not href or '/products/' not in href:
                return None
            
            # Extract product name from link text or title
            name = safe_get_text(link).strip()
            if not name:
                name = safe_get_attr(link, 'title')
            
            if not name:
                # Try to extract from URL
                url_parts = href.split('/products/')
                if len(url_parts) > 1:
                    product_handle = url_parts[1].split('?')[0].split('#')[0]
                    name = product_handle.replace('-', ' ').title()
            
            if not name:
                return None
            
            # Look for image within the link
            img = safe_find(link, 'img')
            image_url = None
            if img:
                for attr in ['data-src', 'src', 'data-original']:
                    img_url = safe_get_attr(img, attr)
                    if img_url:
                        image_url = self._resolve_url(img_url)
                        break
            
            return ProductModel(
                name=self._clean_text(name),
                product_url=self._resolve_url(href),
                image_url=image_url,
                availability="In Stock"  # Default for hero products
            )
            
        except Exception as e:
            logger.debug(f"Error extracting product from link: {str(e)}")
            return None
    
    def _extract_product_from_element(self, element) -> Optional[ProductModel]:
        """Extract product information from a DOM element"""
        try:
            # Extract name
            name = self._extract_product_name(element)
            if not name:
                return None
            
            # Extract price
            price = self._extract_product_price(element)
            
            # Extract original price (for sale items)
            original_price = self._extract_original_price(element)
            
            # Extract image
            image_url = self._extract_product_image(element)
            
            # Extract product URL
            product_url = self._extract_product_url(element)
            
            # Extract availability
            availability = self._extract_availability(element)
            
            # Extract description/snippet
            description = self._extract_product_description(element)
            
            return ProductModel(
                name=name,
                price=price,
                original_price=original_price,
                image_url=image_url,
                product_url=product_url,
                availability=availability,
                description=description
            )
            
        except Exception as e:
            logger.debug(f"Error extracting product from element: {str(e)}")
            return None
    
    def _extract_product_name(self, element) -> Optional[str]:
        """Extract product name from element"""
        name_selectors = [
            '.product-title',
            '.product-name',
            'h1', 'h2', 'h3', 'h4',
            '.title',
            '[data-product-title]',
            'a[href*="/products/"]'
        ]
        
        for selector in name_selectors:
            name_elem = safe_find(element, 'css', selector)
            if name_elem:
                name = safe_get_text(name_elem).strip()
                if name and len(name) > 2:
                    return self._clean_text(name)
        
        return None
    
    def _extract_product_price(self, element) -> Optional[str]:
        """Extract product price from element"""
        price_selectors = [
            '.price',
            '.product-price',
            '.money',
            '[data-price]',
            '.price-current',
            '.sale-price'
        ]
        
        for selector in price_selectors:
            price_elem = safe_find(element, 'css', selector)
            if price_elem:
                price_text = safe_get_text(price_elem).strip()
                if price_text and ('$' in price_text or '€' in price_text or '£' in price_text):
                    return self._clean_text(price_text)
        
        return None
    
    def _extract_original_price(self, element) -> Optional[str]:
        """Extract original price (for sale items) from element"""
        original_price_selectors = [
            '.price-compare',
            '.original-price',
            '.was-price',
            '.compare-price',
            '.price-old'
        ]
        
        for selector in original_price_selectors:
            price_elem = safe_find(element, 'css', selector)
            if price_elem:
                price_text = safe_get_text(price_elem).strip()
                if price_text and ('$' in price_text or '€' in price_text or '£' in price_text):
                    return self._clean_text(price_text)
        
        return None
    
    def _extract_product_image(self, element) -> Optional[str]:
        """Extract product image URL from element"""
        # Look for images
        img_elem = safe_find(element, 'img')
        if img_elem:
            # Try different attributes
            for attr in ['data-src', 'src', 'data-original']:
                img_url = safe_get_attr(img_elem, attr)
                if img_url:
                    return self._resolve_url(img_url)
        
        return None
    
    def _extract_product_url(self, element) -> Optional[str]:
        """Extract product URL from element"""
        # Look for links
        link_elem = safe_find(element, 'a')
        if link_elem:
            href = safe_get_attr(link_elem, 'href')
            if href and '/products/' in href:
                return self._resolve_url(href)
        
        # Look for data attributes
        product_url = safe_get_attr(element, 'data-product-url')
        if product_url:
            return self._resolve_url(product_url)
        
        return None
    
    def _extract_availability(self, element) -> str:
        """Extract availability status from element"""
        # Look for availability indicators
        availability_selectors = [
            '.availability',
            '.stock-status',
            '[data-availability]'
        ]
        
        for selector in availability_selectors:
            avail_elem = safe_find(element, 'css', selector)
            if avail_elem:
                avail_text = safe_get_text(avail_elem).lower()
                if 'out' in avail_text or 'sold' in avail_text:
                    return "Out of Stock"
                elif 'in stock' in avail_text or 'available' in avail_text:
                    return "In Stock"
        
        # Default to in stock for hero products
        return "In Stock"
    
    def _extract_product_description(self, element) -> Optional[str]:
        """Extract product description from element"""
        desc_selectors = [
            '.product-description',
            '.product-summary',
            '.description',
            'p'
        ]
        
        for selector in desc_selectors:
            desc_elem = safe_find(element, 'css', selector)
            if desc_elem:
                description = safe_get_text(desc_elem).strip()
                if description and len(description) > 10:
                    return self._clean_text(description)[:150]  # Shorter for hero products
        
        return None
    
    def _prioritize_hero_products(self, products: List[ProductModel]) -> List[ProductModel]:
        """Prioritize hero products based on position and prominence"""
        # Simple scoring system
        scored_products = []
        
        for i, product in enumerate(products):
            score = 100 - i  # Earlier products get higher scores
            
            # Boost score for products with images
            if product.image_url:
                score += 20
            
            # Boost score for products with prices
            if product.price:
                score += 15
            
            # Boost score for products with descriptions
            if product.description:
                score += 10
            
            scored_products.append((score, product))
        
        # Sort by score and return products
        scored_products.sort(key=lambda x: x[0], reverse=True)
        return [product for score, product in scored_products]
    
    def _deduplicate_products(self, products: List[ProductModel]) -> List[ProductModel]:
        """Remove duplicate products based on name and URL"""
        seen = set()
        unique_products = []
        
        for product in products:
            # Create a unique identifier
            identifier = (product.name.lower() if product.name else '', 
                         product.product_url if product.product_url else '')
            
            if identifier not in seen and product.name:
                seen.add(identifier)
                unique_products.append(product)
        
        return unique_products
