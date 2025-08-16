"""
Product extraction module for Shopify stores
Handles extraction of all products from product pages and product listings
"""
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
import json
import re
import logging
from urllib.parse import urljoin, urlparse
from core.models import ProductModel
from .base_extractor import BaseExtractor, safe_get_attr, safe_get_text, safe_find_all, safe_find

logger = logging.getLogger(__name__)

class ProductExtractor(BaseExtractor):
    """Extract product information from Shopify pages"""
    
    def extract(self) -> List[ProductModel]:
        """Extract products from the page"""
        products = []
        
        # Try different methods to extract products
        products.extend(self._extract_from_json_ld())
        products.extend(self._extract_from_product_grid())
        products.extend(self._extract_from_product_list())
        products.extend(self._extract_from_shopify_sections())
        products.extend(self._extract_from_collection_page())
        
        # Remove duplicates
        unique_products = self._deduplicate_products(products)
        
        logger.info(f"Extracted {len(unique_products)} unique products")
        return unique_products
    
    def _extract_from_json_ld(self) -> List[ProductModel]:
        """Extract products from JSON-LD structured data"""
        products = []
        structured_data = self._extract_json_ld()
        
        for data in structured_data:
            if data.get('@type') == 'Product':
                product = self._create_product_from_json_ld(data)
                if product:
                    products.append(product)
        
        return products
    
    def _create_product_from_json_ld(self, data: Dict) -> Optional[ProductModel]:
        """Create ProductModel from JSON-LD data"""
        try:
            name = data.get('name', '')
            if not name:
                return None
            
            # Extract price information
            offers = data.get('offers', {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            
            price = offers.get('price')
            currency = offers.get('priceCurrency', 'USD')
            availability = offers.get('availability', '')
            
            # Format price
            formatted_price = None
            if price:
                try:
                    price_float = float(price)
                    formatted_price = f"${price_float:.2f}" if currency == 'USD' else f"{price_float:.2f} {currency}"
                except (ValueError, TypeError):
                    formatted_price = str(price)
            
            # Extract image
            image_url = None
            image_data = data.get('image')
            if image_data:
                if isinstance(image_data, list):
                    image_url = image_data[0] if image_data else None
                elif isinstance(image_data, str):
                    image_url = image_data
                elif isinstance(image_data, dict):
                    image_url = image_data.get('url')
            
            # Extract description
            description = data.get('description', '')
            
            # Extract product URL
            product_url = data.get('url', '')
            if product_url and not product_url.startswith('http'):
                product_url = self._resolve_url(product_url)
            
            # Determine availability status
            availability_status = "In Stock"
            if 'outofstock' in availability.lower():
                availability_status = "Out of Stock"
            elif 'instock' in availability.lower():
                availability_status = "In Stock"
            
            return ProductModel(
                name=self._clean_text(name),
                price=formatted_price,
                image_url=self._resolve_url(image_url) if image_url else None,
                product_url=product_url,
                availability=availability_status,
                description=self._clean_text(description) if description else None
            )
            
        except Exception as e:
            logger.error(f"Error creating product from JSON-LD: {str(e)}")
            return None
    
    def _extract_from_product_grid(self) -> List[ProductModel]:
        """Extract products from product grid layouts"""
        products = []
        
        # Common selectors for product grids
        grid_selectors = [
            '.product-grid .product-item',
            '.products-grid .product',
            '.collection-grid .product-card',
            '.product-list .product-item',
            '[data-product-item]',
            '.product-card',
            '.product-tile'
        ]
        
        for selector in grid_selectors:
            product_items = safe_find_all(self.soup, 'css', selector)
            for item in product_items:
                product = self._extract_product_from_element(item)
                if product:
                    products.append(product)
        
        return products
    
    def _extract_from_product_list(self) -> List[ProductModel]:
        """Extract products from list layouts"""
        products = []
        
        # Look for product containers
        product_containers = safe_find_all(self.soup, class_=re.compile(r'product'))
        
        for container in product_containers:
            product = self._extract_product_from_element(container)
            if product:
                products.append(product)
        
        return products
    
    def _extract_from_shopify_sections(self) -> List[ProductModel]:
        """Extract products from Shopify section-based layouts"""
        products = []
        
        # Look for Shopify sections
        sections = safe_find_all(self.soup, attrs={'data-section-type': True})
        
        for section in sections:
            section_type = safe_get_attr(section, 'data-section-type')
            if 'product' in section_type.lower() or 'collection' in section_type.lower():
                section_products = self._extract_products_from_section(section)
                products.extend(section_products)
        
        return products
    
    def _extract_from_collection_page(self) -> List[ProductModel]:
        """Extract products from collection pages"""
        products = []
        
        # Look for collection-specific selectors
        collection_selectors = [
            '.collection .product',
            '.collection-products .product-item',
            '.products .product-card',
            '#CollectionProductGrid .product'
        ]
        
        for selector in collection_selectors:
            try:
                product_items = self.soup.select(selector)
                for item in product_items:
                    product = self._extract_product_from_element(item)
                    if product:
                        products.append(product)
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {str(e)}")
                continue
        
        return products
    
    def _extract_products_from_section(self, section) -> List[ProductModel]:
        """Extract products from a Shopify section"""
        products = []
        
        # Look for product elements within the section
        product_selectors = [
            '.product-item',
            '.product-card',
            '.product',
            '[data-product]'
        ]
        
        for selector in product_selectors:
            items = safe_find_all(section, 'css', selector)
            for item in items:
                product = self._extract_product_from_element(item)
                if product:
                    products.append(product)
        
        return products
    
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
            
            # Extract tags/categories
            tags = self._extract_product_tags(element)
            
            return ProductModel(
                name=name,
                price=price,
                original_price=original_price,
                image_url=image_url,
                product_url=product_url,
                availability=availability,
                description=description,
                tags=tags
            )
            
        except Exception as e:
            logger.debug(f"Error extracting product from element: {str(e)}")
            return None
    
    def _extract_product_name(self, element) -> Optional[str]:
        """Extract product name from element"""
        name_selectors = [
            '.product-title',
            '.product-name',
            'h2', 'h3', 'h4',
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
        
        # Check for disabled add to cart buttons
        add_to_cart = safe_find(element, 'button', class_=re.compile(r'add.*cart|cart.*add'))
        if add_to_cart and safe_get_attr(add_to_cart, 'disabled'):
            return "Out of Stock"
        
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
                    return self._clean_text(description)[:200]  # Limit length
        
        return None
    
    def _extract_product_tags(self, element) -> Optional[List[str]]:
        """Extract product tags/categories from element"""
        tags = []
        
        # Look for tag elements
        tag_selectors = [
            '.product-tags .tag',
            '.tags .tag',
            '.categories .category'
        ]
        
        for selector in tag_selectors:
            tag_elems = safe_find_all(element, 'css', selector)
            for tag_elem in tag_elems:
                tag_text = safe_get_text(tag_elem).strip()
                if tag_text:
                    tags.append(self._clean_text(tag_text))
        
        return tags if tags else None
    
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

class ProductCatalogExtractor(ProductExtractor):
    """Specialized extractor for full product catalogs"""
    
    def __init__(self, soup: BeautifulSoup, base_url: str, max_products: int = 100):
        super().__init__(soup, base_url)
        self.max_products = max_products
    
    def extract(self) -> List[ProductModel]:
        """Extract products with limit"""
        products = super().extract()
        return products[:self.max_products]

class SingleProductExtractor(ProductExtractor):
    """Specialized extractor for single product pages"""
    
    def extract(self) -> List[ProductModel]:
        """Extract single product from product page"""
        # Look for main product container
        product_selectors = [
            '.product',
            '.product-single',
            '.product-details',
            '#product',
            '[data-product-single]'
        ]
        
        for selector in product_selectors:
            product_elem = safe_find(self.soup, 'css', selector)
            if product_elem:
                product = self._extract_product_from_element(product_elem)
                if product:
                    return [product]
        
        # Fallback to extracting from entire page
        products = super().extract()
        return products[:1] if products else []
    
    def extract_single(self) -> Optional[ProductModel]:
        """Extract single product and return as optional"""
        products = self.extract()
        return products[0] if products else None
