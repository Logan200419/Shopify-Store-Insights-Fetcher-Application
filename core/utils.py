import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, urlparse
import re
import logging
from fake_useragent import UserAgent
from config.settings import settings
import ssl
import certifi

logger = logging.getLogger(__name__)

class WebScraper:
    """Base web scraper with retry logic and error handling"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = None
        
    async def __aenter__(self):
        # Create SSL context with proper certificate verification
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Try to use AsyncResolver if aiodns is available, otherwise fall back to default
        try:
            resolver = aiohttp.AsyncResolver()
        except RuntimeError:
            logger.warning("aiodns not available, using default resolver")
            resolver = None
        
        connector = aiohttp.TCPConnector(
            limit=10, 
            limit_per_host=5,
            ssl=ssl_context,
            resolver=resolver,
            use_dns_cache=True
        )
        
        timeout = aiohttp.ClientTimeout(total=settings.request_timeout)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': self.ua.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_page(self, url: str, retries: Optional[int] = None) -> Optional[str]:
        """Fetch a single page with retry logic and fallback mechanisms"""
        if retries is None:
            retries = settings.max_retries
            
        # Check if session is available
        if not self.session:
            logger.error("Session not initialized. Use async context manager.")
            return None
            
        # Try async approach first
        for attempt in range(retries + 1):
            try:
                async with self.session.get(url, allow_redirects=True) as response:
                    if response.status == 200:
                        content = await response.text()
                        await asyncio.sleep(settings.rate_limit_delay)
                        return content
                    elif response.status == 404:
                        logger.warning(f"Page not found: {url}")
                        break
                    elif response.status in [403, 429]:
                        logger.warning(f"Access denied or rate limited for {url}, attempt {attempt + 1}")
                    else:
                        logger.warning(f"HTTP {response.status} for {url}, attempt {attempt + 1}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"Timeout for {url}, attempt {attempt + 1}")
            except aiohttp.ClientError as e:
                logger.warning(f"Client error for {url}: {str(e)}, attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {str(e)}, attempt {attempt + 1}")
                
            if attempt < retries:
                wait_time = min(2 ** attempt, 10)  # Exponential backoff with max 10 seconds
                await asyncio.sleep(wait_time)
        
        # Fallback to synchronous requests if async fails
        logger.info(f"Async fetch failed for {url}, trying synchronous fallback")
        return self.fetch_page_sync(url)
    
    def fetch_page_sync(self, url: str) -> Optional[str]:
        """Synchronous fallback for fetching pages with better error handling"""
        try:
            headers = {
                'User-Agent': self.ua.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Try with different verification settings
            for verify_ssl in [True, False]:
                try:
                    response = requests.get(
                        url, 
                        headers=headers, 
                        timeout=settings.request_timeout,
                        verify=verify_ssl,
                        allow_redirects=True
                    )
                    response.raise_for_status()
                    return response.text
                except requests.exceptions.SSLError:
                    if verify_ssl:
                        logger.warning(f"SSL verification failed for {url}, trying without verification")
                        continue
                    else:
                        raise
                except requests.exceptions.RequestException as e:
                    logger.error(f"Request error for {url}: {str(e)}")
                    if verify_ssl:
                        continue
                    else:
                        break
                        
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            
        return None

class ShopifyDetector:
    """Utility class to detect and validate Shopify stores"""
    
    @staticmethod
    def is_shopify_store(html_content: str, url: str) -> bool:
        """Check if the website is a Shopify store"""
        if not html_content:
            return False
            
        shopify_indicators = [
            'Shopify.theme',
            'shopify.com',
            'cdn.shopify.com',
            'Shopify.shop',
            'shopify-features',
            'shopify-section',
            'myshopify.com'
        ]
        
        # Check URL for myshopify.com
        if 'myshopify.com' in url:
            return True
            
        # Check HTML content for Shopify indicators
        html_lower = html_content.lower()
        return any(indicator.lower() in html_lower for indicator in shopify_indicators)
    
    @staticmethod
    def extract_shopify_data(soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract Shopify-specific data from parsed HTML"""
        data = {}
        
        # Look for Shopify script tags
        scripts = soup.find_all('script')
        for script in scripts:
            # Get script content safely
            content = script.get_text() if script else None
            if content:
                # Extract shop data
                if 'Shopify.shop' in content:
                    shop_match = re.search(r'Shopify\.shop\s*=\s*"([^"]+)"', content)
                    if shop_match:
                        data['shop_domain'] = shop_match.group(1)
                
                # Extract currency
                if 'Shopify.currency' in content:
                    currency_match = re.search(r'Shopify\.currency\s*=\s*["\']([^"\']+)["\']', content)
                    if currency_match:
                        data['currency'] = currency_match.group(1)
        
        return data

class URLUtils:
    """Utility class for URL operations"""
    
    @staticmethod
    def normalize_url(url: str, base_url: str) -> str:
        """Normalize and join URLs"""
        if url.startswith('http'):
            return url
        return urljoin(base_url, url)
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if URL is valid"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    @staticmethod
    def get_domain(url: str) -> str:
        """Extract domain from URL"""
        try:
            return urlparse(url).netloc
        except Exception:
            return ""

class TextCleaner:
    """Utility class for text cleaning and processing"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\-\(\)]', '', text)
        return text.strip()
    
    @staticmethod
    def extract_price(text: str) -> Optional[str]:
        """Extract price from text"""
        if not text:
            return None
            
        # Common price patterns
        price_patterns = [
            r'[\$₹€£¥][\d,]+\.?\d*',
            r'[\d,]+\.?\d*\s*[\$₹€£¥]',
            r'Rs\.?\s*[\d,]+\.?\d*',
            r'USD\s*[\d,]+\.?\d*'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        
        return None
    
    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """Extract email addresses from text"""
        if not text:
            return []
            
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return list(set(emails))  # Remove duplicates
    
    @staticmethod
    def extract_phone_numbers(text: str) -> List[str]:
        """Extract phone numbers from text"""
        if not text:
            return []
            
        phone_patterns = [
            r'\+\d{1,3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}',
            r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}',
            r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\+\d{10,15}'
        ]
        
        phones = []
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            phones.extend(matches)
        
        return list(set(phones))  # Remove duplicates