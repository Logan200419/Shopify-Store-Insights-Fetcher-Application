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

class ProductExtractor(BaseExtractor):
    """Extract product information from Shopify pages"""
    
    def extract(self) -> List[ProductModel]:
        """Extract products from the page"""
        products = []
        
        # Try multiple selectors for products
        product_selectors = [
            '.product-item',
            '.product-card',
            '.grid-product',
            '.product-block',
            '[data-product-id]',
            '.shopify-product-gallery',
            '.product'
        ]
        
        for selector in product_selectors:
            product_elements = self.soup.select(selector)
            if product_elements:
                for element in product_elements:
                    product = self._extract_single_product(element)
                    if product:
                        products.append(product)
                break
        
        # Also look for JSON-LD structured data
        json_products = self._extract_from_json_ld()
        products.extend(json_products)
        
        return self._deduplicate_products(products)
    
    def _extract_single_product(self, element) -> Optional[ProductModel]:
        """Extract a single product from an element"""
        try:
            # Extract product name
            name_selectors = [
                '.product-title',
                '.product-name',
                'h3',
                'h2',
                '[data-product-title]',
                '.grid-product__title'
            ]
            name = self._find_text_by_selectors(element, name_selectors)
            
            if not name:
                return None
            
            # Extract price
            price_selectors = [
                '.price',
                '.product-price',
                '.money',
                '[data-price]',
                '.price-item--regular'
            ]
            price = self._find_text_by_selectors(element, price_selectors)
            if price:
                price = TextCleaner.extract_price(price)
            
            # Extract original price (sale price)
            original_price_selectors = [
                '.price--compare',
                '.was-price',
                '.compare-at-price',
                '.price-item--sale'
            ]
            original_price = self._find_text_by_selectors(element, original_price_selectors)
            if original_price:
                original_price = TextCleaner.extract_price(original_price)
            
            # Extract image URL
            img_element = element.find('img')
            image_url = None
            if img_element:
                image_url = img_element.get('src') or img_element.get('data-src')
                if image_url:
                    image_url = URLUtils.normalize_url(image_url, self.base_url)
            
            # Extract product URL
            link_element = element.find('a')
            product_url = None
            if link_element:
                product_url = link_element.get('href')
                if product_url:
                    product_url = URLUtils.normalize_url(product_url, self.base_url)
            
            # Extract availability
            availability = "In Stock"  # Default
            availability_indicators = element.find_all(text=re.compile(r'(sold out|out of stock|unavailable)', re.I))
            if availability_indicators:
                availability = "Out of Stock"
            
            return ProductModel(
                name=TextCleaner.clean_text(name),
                price=price,
                original_price=original_price,
                image_url=image_url,
                product_url=product_url,
                availability=availability
            )
            
        except Exception as e:
            logger.error(f"Error extracting product: {str(e)}")
            return None
    
    def _extract_from_json_ld(self) -> List[ProductModel]:
        """Extract products from JSON-LD structured data"""
        products = []
        scripts = self.soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            try:
                data = json.loads(script.get_text())
                if isinstance(data, list):
                    for item in data:
                        product = self._parse_json_ld_product(item)
                        if product:
                            products.append(product)
                else:
                    product = self._parse_json_ld_product(data)
                    if product:
                        products.append(product)
            except (json.JSONDecodeError, Exception) as e:
                logger.debug(f"Error parsing JSON-LD: {str(e)}")
                continue
        
        return products
    
    def _parse_json_ld_product(self, data: Dict) -> Optional[ProductModel]:
        """Parse a single product from JSON-LD data"""
        try:
            if data.get('@type') != 'Product':
                return None
            
            name = data.get('name')
            if not name:
                return None
            
            # Extract price from offers
            price = None
            currency = None
            availability = None
            
            offers = data.get('offers', {})
            if isinstance(offers, list) and offers:
                offers = offers[0]
            
            if isinstance(offers, dict):
                price = offers.get('price')
                currency = offers.get('priceCurrency')
                availability_val = offers.get('availability', '')
                
                if 'InStock' in availability_val:
                    availability = "In Stock"
                elif 'OutOfStock' in availability_val:
                    availability = "Out of Stock"
            
            # Extract image
            image_url = None
            image_data = data.get('image')
            if image_data:
                if isinstance(image_data, list) and image_data:
                    image_url = image_data[0]
                elif isinstance(image_data, str):
                    image_url = image_data
                elif isinstance(image_data, dict):
                    image_url = image_data.get('url')
            
            if image_url:
                image_url = URLUtils.normalize_url(image_url, self.base_url)
            
            # Format price
            if price and currency:
                price = f"{currency} {price}"
            
            return ProductModel(
                name=TextCleaner.clean_text(name),
                price=price,
                currency=currency,
                availability=availability,
                image_url=image_url,
                description=TextCleaner.clean_text(data.get('description', ''))
            )
            
        except Exception as e:
            logger.error(f"Error parsing JSON-LD product: {str(e)}")
            return None
    
    def _find_text_by_selectors(self, element, selectors: List[str]) -> Optional[str]:
        """Find text using multiple CSS selectors"""
        for selector in selectors:
            found = element.select_one(selector)
            if found:
                text = found.get_text(strip=True)
                if text:
                    return text
        return None
    
    def _deduplicate_products(self, products: List[ProductModel]) -> List[ProductModel]:
        """Remove duplicate products based on name"""
        seen_names = set()
        unique_products = []
        
        for product in products:
            if product.name not in seen_names:
                seen_names.add(product.name)
                unique_products.append(product)
        
        return unique_products

class SocialMediaExtractor(BaseExtractor):
    """Extract social media handles"""
    
    def extract(self) -> SocialHandles:
        """Extract social media links"""
        social_handles = SocialHandles()
        
        # Find all links
        links = self.soup.find_all('a', href=True)
        
        for link in links:
            href_attr = safe_get_attr(link, 'href')
            if not href_attr:
                continue
                
            href = href_attr.lower()
            
            if 'instagram.com' in href:
                social_handles.instagram = self._clean_social_url(href_attr)
            elif 'facebook.com' in href:
                social_handles.facebook = self._clean_social_url(href_attr)
            elif 'twitter.com' in href or 'x.com' in href:
                social_handles.twitter = self._clean_social_url(href_attr)
            elif 'tiktok.com' in href:
                social_handles.tiktok = self._clean_social_url(href_attr)
            elif 'youtube.com' in href:
                social_handles.youtube = self._clean_social_url(href_attr)
            elif 'linkedin.com' in href:
                social_handles.linkedin = self._clean_social_url(href_attr)
            elif 'pinterest.com' in href:
                social_handles.pinterest = self._clean_social_url(href_attr)
        
        return social_handles
    
    def _clean_social_url(self, url: str) -> str:
        """Clean and normalize social media URL"""
        # Remove tracking parameters
        url = re.sub(r'\?.*$', '', url)
        return url.strip()

class ContactExtractor(BaseExtractor):
    """Extract contact information"""
    
    def extract(self) -> ContactDetails:
        """Extract contact details"""
        contact_details = ContactDetails()
        
        # Get all text content
        text_content = self.soup.get_text()
        
        # Extract emails
        contact_details.emails = TextCleaner.extract_emails(text_content)
        
        # Extract phone numbers
        contact_details.phone_numbers = TextCleaner.extract_phone_numbers(text_content)
        
        # Look for contact form
        contact_form = self.soup.find('form', {'action': re.compile(r'contact', re.I)})
        if contact_form:
            contact_details.contact_form_url = self.base_url
        
        # Look for address
        address_selectors = [
            '.address',
            '.contact-address',
            '[class*="address"]'
        ]
        
        for selector in address_selectors:
            element = self.soup.select_one(selector)
            if element:
                address_text = element.get_text(strip=True)
                if len(address_text) > 20:  # Likely to be a real address
                    contact_details.address = TextCleaner.clean_text(address_text)
                    break
        
        return contact_details

class PolicyExtractor(BaseExtractor):
    """Extract policy information (Privacy, Return, Refund)"""
    
    def extract(self) -> Dict[str, Optional[PolicyModel]]:
        """Extract all policy information"""
        policies: Dict[str, Optional[PolicyModel]] = {
            'privacy_policy': None,
            'return_policy': None,
            'refund_policy': None,
            'terms_of_service': None
        }
        
        # Find all links
        links = self.soup.find_all('a', href=True)
        
        for link in links:
            href_attr = safe_get_attr(link, 'href')
            if not href_attr:
                continue
                
            href = href_attr.lower()
            link_text = safe_get_text(link, strip=True).lower()
            
            # Privacy Policy
            if any(term in href or term in link_text for term in ['privacy', 'privacy-policy']):
                if not policies['privacy_policy']:
                    policies['privacy_policy'] = self._extract_policy_content(link, 'Privacy Policy')
            
            # Return Policy
            elif any(term in href or term in link_text for term in ['return', 'returns', 'return-policy']):
                if not policies['return_policy']:
                    policies['return_policy'] = self._extract_policy_content(link, 'Return Policy')
            
            # Refund Policy
            elif any(term in href or term in link_text for term in ['refund', 'refunds', 'refund-policy']):
                if not policies['refund_policy']:
                    policies['refund_policy'] = self._extract_policy_content(link, 'Refund Policy')
            
            # Terms of Service
            elif any(term in href or term in link_text for term in ['terms', 'tos', 'terms-of-service', 'terms-conditions']):
                if not policies['terms_of_service']:
                    policies['terms_of_service'] = self._extract_policy_content(link, 'Terms of Service')
        
        return policies
    
    def _extract_policy_content(self, link_element, policy_type: str) -> Optional[PolicyModel]:
        """Extract content from a policy page"""
        try:
            href_attr = safe_get_attr(link_element, 'href')
            if not href_attr:
                return None
                
            url = URLUtils.normalize_url(href_attr, self.base_url)
            
            # For now, we'll just return the URL and basic info
            # In a production system, you might want to fetch and parse the actual policy content
            return PolicyModel(
                title=policy_type,
                content=f"Policy available at: {url}",
                url=url
            )
        except Exception as e:
            logger.error(f"Error extracting policy content: {str(e)}")
            return None

class FAQExtractor(BaseExtractor):
    """Extract FAQ information"""
    
    def extract(self) -> List[FAQModel]:
        """Extract FAQ items"""
        faqs = []
        
        # Common FAQ selectors
        faq_selectors = [
            '.faq',
            '.faq-item',
            '.accordion',
            '.accordion-item',
            '.question',
            '[class*="faq"]'
        ]
        
        for selector in faq_selectors:
            faq_elements = self.soup.select(selector)
            if faq_elements:
                for element in faq_elements:
                    faq = self._extract_single_faq(element)
                    if faq:
                        faqs.append(faq)
        
        # Also look for dl/dt/dd structure (definition lists)
        dl_elements = self.soup.find_all('dl')
        for dl in dl_elements:
            dt_elements = safe_find_all(dl, 'dt')
            dd_elements = safe_find_all(dl, 'dd')
            
            for dt, dd in zip(dt_elements, dd_elements):
                question = safe_get_text(dt, strip=True)
                answer = safe_get_text(dd, strip=True)
                
                if question and answer and len(question) > 5:
                    faqs.append(FAQModel(
                        question=TextCleaner.clean_text(question),
                        answer=TextCleaner.clean_text(answer)
                    ))
        
        return faqs
    
    def _extract_single_faq(self, element) -> Optional[FAQModel]:
        """Extract a single FAQ from an element"""
        try:
            # Try to find question and answer within the element
            question_selectors = [
                '.question',
                '.faq-question',
                'h3',
                'h4',
                '.accordion-header',
                '[class*="question"]'
            ]
            
            answer_selectors = [
                '.answer',
                '.faq-answer',
                '.accordion-body',
                '.accordion-content',
                '[class*="answer"]'
            ]
            
            question = self._find_text_by_selectors(element, question_selectors)
            answer = self._find_text_by_selectors(element, answer_selectors)
            
            # If we can't find specific selectors, try to extract from text content
            if not question or not answer:
                text_content = element.get_text(strip=True)
                lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                
                if len(lines) >= 2:
                    question = lines[0]
                    answer = ' '.join(lines[1:])
            
            if question and answer and len(question) > 5:
                return FAQModel(
                    question=TextCleaner.clean_text(question),
                    answer=TextCleaner.clean_text(answer)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting FAQ: {str(e)}")
            return None
    
    def _find_text_by_selectors(self, element, selectors: List[str]) -> Optional[str]:
        """Find text using multiple CSS selectors"""
        for selector in selectors:
            found = element.select_one(selector)
            if found:
                text = found.get_text(strip=True)
                if text:
                    return text
        return None

class ImportantLinksExtractor(BaseExtractor):
    """Extract important links like order tracking, contact us, blogs"""
    
    def extract(self) -> ImportantLinks:
        """Extract important links"""
        links = ImportantLinks()
        
        # Find all links
        all_links = self.soup.find_all('a', href=True)
        
        for link in all_links:
            href_attr = safe_get_attr(link, 'href')
            if not href_attr:
                continue
                
            href = href_attr.lower()
            link_text = safe_get_text(link, strip=True).lower()
            full_url = URLUtils.normalize_url(href_attr, self.base_url)
            
            # Order tracking
            if any(term in href or term in link_text for term in ['track', 'tracking', 'order-status', 'track-order']):
                if not links.order_tracking:
                    links.order_tracking = full_url
            
            # Contact us
            elif any(term in href or term in link_text for term in ['contact', 'contact-us', 'get-in-touch']):
                if not links.contact_us:
                    links.contact_us = full_url
            
            # Blogs
            elif any(term in href or term in link_text for term in ['blog', 'blogs', 'news', 'articles']):
                if not links.blogs:
                    links.blogs = full_url
            
            # About us
            elif any(term in href or term in link_text for term in ['about', 'about-us', 'our-story']):
                if not links.about_us:
                    links.about_us = full_url
            
            # Shipping info
            elif any(term in href or term in link_text for term in ['shipping', 'delivery', 'shipping-info']):
                if not links.shipping_info:
                    links.shipping_info = full_url
            
            # Size guide
            elif any(term in href or term in link_text for term in ['size', 'size-guide', 'sizing', 'fit-guide']):
                if not links.size_guide:
                    links.size_guide = full_url
            
            # Careers
            elif any(term in href or term in link_text for term in ['career', 'careers', 'jobs', 'join-us']):
                if not links.careers:
                    links.careers = full_url
        
        return links

class BrandExtractor(BaseExtractor):
    """Extract brand-specific information"""
    
    def extract(self) -> Dict[str, Any]:
        """Extract brand information"""
        brand_info = {
            'name': None,
            'description': None,
            'logo_url': None,
            'currencies': [],
            'payment_methods': []
        }
        
        # Extract brand name
        brand_info['name'] = self._extract_brand_name()
        
        # Extract brand description
        brand_info['description'] = self._extract_brand_description()
        
        # Extract logo
        brand_info['logo_url'] = self._extract_logo()
        
        # Extract currencies and payment methods
        brand_info['currencies'] = self._extract_currencies()
        brand_info['payment_methods'] = self._extract_payment_methods()
        
        return brand_info
    
    def _extract_brand_name(self) -> Optional[str]:
        """Extract brand name from various sources"""
        # Try title tag first
        title_tag = self.soup.find('title')
        if title_tag:
            title_text = safe_get_text(title_tag, strip=True)
            # Remove common suffixes
            title_text = re.sub(r'\s*[-–|]\s*(Shop|Store|Online|Official).*$', '', title_text, flags=re.IGNORECASE)
            if title_text and len(title_text) < 100:
                return TextCleaner.clean_text(title_text)
        
        # Try meta property og:site_name
        og_site_name = self.soup.find('meta', property='og:site_name')
        if og_site_name:
            content = safe_get_attr(og_site_name, 'content')
            if content:
                return TextCleaner.clean_text(content)
        
        # Try to find logo alt text
        logo_selectors = [
            'img[alt*="logo"]',
            '.logo img',
            '.brand img',
            '.site-logo img'
        ]
        
        for selector in logo_selectors:
            logo_img = self.soup.select_one(selector)
            if logo_img:
                alt_text = safe_get_attr(logo_img, 'alt')
                if alt_text and 'logo' not in alt_text.lower():
                    return TextCleaner.clean_text(alt_text)
        
        return None
    
    def _extract_brand_description(self) -> Optional[str]:
        """Extract brand description"""
        # Try meta description
        meta_desc = self.soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            content = safe_get_attr(meta_desc, 'content')
            if content and len(content) > 20:
                return TextCleaner.clean_text(content)
        
        # Try og:description
        og_desc = self.soup.find('meta', property='og:description')
        if og_desc:
            content = safe_get_attr(og_desc, 'content')
            if content and len(content) > 20:
                return TextCleaner.clean_text(content)
        
        return None
    
    def _extract_logo(self) -> Optional[str]:
        """Extract logo URL"""
        logo_selectors = [
            '.logo img',
            '.site-logo img',
            '.brand img',
            'img[alt*="logo" i]',
            '.header img'
        ]
        
        for selector in logo_selectors:
            logo_img = self.soup.select_one(selector)
            if logo_img:
                logo_url = safe_get_attr(logo_img, 'src') or safe_get_attr(logo_img, 'data-src')
                if logo_url:
                    return URLUtils.normalize_url(logo_url, self.base_url)
        
        return None
    
    def _extract_currencies(self) -> List[str]:
        """Extract supported currencies"""
        currencies = set()
        
        # Look for Shopify currency data
        shopify_data = ShopifyDetector.extract_shopify_data(self.soup)
        if shopify_data.get('currency'):
            currencies.add(shopify_data['currency'])
        
        # Look for currency selectors/dropdowns
        currency_elements = self.soup.find_all(['select', 'div'], class_=re.compile(r'currency', re.I))
        for element in currency_elements:
            options = safe_find_all(element, ['option', 'a', 'span'])
            for option in options:
                text = safe_get_text(option, strip=True)
                # Look for currency codes (3 letters)
                currency_match = re.search(r'\b([A-Z]{3})\b', text)
                if currency_match:
                    currencies.add(currency_match.group(1))
        
        return list(currencies)
    
    def _extract_payment_methods(self) -> List[str]:
        """Extract payment methods"""
        payment_methods = set()
        
        # Common payment method indicators
        payment_indicators = {
            'visa': 'Visa',
            'mastercard': 'Mastercard',
            'amex': 'American Express',
            'paypal': 'PayPal',
            'stripe': 'Stripe',
            'apple pay': 'Apple Pay',
            'google pay': 'Google Pay',
            'shopify pay': 'Shopify Pay',
            'klarna': 'Klarna',
            'afterpay': 'Afterpay',
            'cod': 'Cash on Delivery',
            'cash on delivery': 'Cash on Delivery'
        }
        
        # Get all text content
        text_content = self.soup.get_text().lower()
        
        for indicator, method in payment_indicators.items():
            if indicator in text_content:
                payment_methods.add(method)
        
        # Look for payment icons
        payment_imgs = self.soup.find_all('img', src=re.compile(r'(visa|mastercard|paypal|stripe|payment)', re.I))
        for img in payment_imgs:
            src = safe_get_attr(img, 'src', '').lower()
            alt = safe_get_attr(img, 'alt', '').lower()
            
            for indicator, method in payment_indicators.items():
                if indicator in src or indicator in alt:
                    payment_methods.add(method)
        
        return list(payment_methods)