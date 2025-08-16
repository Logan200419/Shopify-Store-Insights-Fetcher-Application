import requests
import re
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, quote_plus
import time
import logging
import json
import random

logger = logging.getLogger(__name__)

class CompetitorAnalyzer:
    """Analyze competitors for a given brand and extract insights from Shopify stores."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        })
        
        # Known competitor directories and databases
        self.competitor_sources = [
            self._search_web,
            self._search_similar_sites,
            self._search_industry_specific
        ]
        
    def find_competitors(self, brand_name: str, website_url: str, max_competitors: int = 10) -> List[Dict[str, str]]:
        """Find competitors for a given brand using multiple search strategies."""
        logger.info(f"Finding competitors for {brand_name} ({website_url})")
        competitors = []
        
        # Extract brand category/industry from website
        category = self._extract_brand_category(website_url)
        logger.info(f"Detected category: {category}")
        
        # Use multiple search strategies
        all_competitors = []
        
        # Strategy 1: Web search with various queries
        web_competitors = self._search_web(brand_name, category, website_url)
        all_competitors.extend(web_competitors)
        logger.info(f"Found {len(web_competitors)} competitors from web search")
        
        # Strategy 2: Search for similar sites
        similar_competitors = self._search_similar_sites(brand_name, website_url)
        all_competitors.extend(similar_competitors)
        logger.info(f"Found {len(similar_competitors)} competitors from similar sites search")
        
        # Strategy 3: Industry-specific search
        industry_competitors = self._search_industry_specific(category, brand_name, website_url)
        all_competitors.extend(industry_competitors)
        logger.info(f"Found {len(industry_competitors)} competitors from industry search")
        
        # Remove duplicates and filter valid Shopify stores
        unique_competitors = self._deduplicate_and_validate_competitors(all_competitors, website_url)
        
        # Fallback: If no competitors found, add some popular Shopify stores from the same category
        if len(unique_competitors) == 0:
            logger.info("No competitors found through search, using fallback stores")
            fallback_competitors = self._get_fallback_competitors(category, website_url)
            unique_competitors.extend(fallback_competitors)
        
        logger.info(f"Total unique competitors found: {len(unique_competitors)}")
        return unique_competitors[:max_competitors]
    
    def _extract_brand_category(self, website_url: str) -> str:
        """Extract brand category/industry from website content."""
        try:
            response = requests.get(website_url, timeout=1)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for category indicators in meta tags, title, or content
            meta_description = soup.find('meta', attrs={'name': 'description'})
            title = soup.find('title')
            
            text_content = ""
            if meta_description:
                try:
                    content = meta_description.get('content')  # type: ignore
                    if content:
                        text_content += str(content) + " "
                except:
                    pass
            if title:
                text_content += title.get_text() + " "
            
            # Extract first few paragraphs for context
            paragraphs = soup.find_all('p')[:3]
            for p in paragraphs:
                text_content += p.get_text() + " "
            
            # Identify category keywords
            category = self._categorize_brand(text_content)
            return category
            
        except Exception as e:
            logger.warning(f"Could not extract category from {website_url}: {e}")
            return "ecommerce"
    
    def _categorize_brand(self, text_content: str) -> str:
        """Categorize brand based on text content."""
        text_lower = text_content.lower()
        
        categories = {
            "fashion": ["fashion", "clothing", "apparel", "style", "wear", "dress", "shirt"],
            "beauty": ["beauty", "cosmetics", "skincare", "makeup", "fragrance", "perfume"],
            "fitness": ["fitness", "gym", "workout", "supplement", "protein", "nutrition"],
            "gaming": ["gaming", "gamer", "esports", "energy drink", "gfuel"],
            "electronics": ["electronics", "tech", "gadget", "device", "smartphone"],
            "home": ["home", "furniture", "decor", "kitchen", "living"],
            "jewelry": ["jewelry", "watch", "ring", "necklace", "bracelet"],
            "sports": ["sports", "athletic", "outdoor", "running", "basketball"],
            "food": ["food", "snack", "drink", "beverage", "organic"],
            "pet": ["pet", "dog", "cat", "animal", "puppy"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in text_lower for keyword in keywords):
                return category
        
        return "ecommerce"
    
    def _search_web(self, brand_name: str, category: str, website_url: str) -> List[Dict[str, str]]:
        """Search for competitors using web search with multiple queries."""
        competitors = []
        
        # Generate comprehensive search queries
        search_queries = [
            f"{category} brands like {brand_name}",
            f"best {category} websites",
            f"{category} alternatives to {brand_name}",
            f"top {category} stores online",
            f"{brand_name} competitors",
            f"{category} ecommerce sites",
            f"similar to {brand_name}",
            f"{category} online shopping",
            f"best {category} brands 2024",
            f"{category} marketplace stores"
        ]
        
        for query in search_queries:
            try:
                logger.info(f"Searching for: {query}")
                found_competitors = self._perform_web_search(query, website_url)
                competitors.extend(found_competitors)
                time.sleep(random.uniform(0.5, 1))  # Random delay to avoid rate limiting
                
                if len(competitors) >= 20:  # Collect enough candidates
                    break
                    
            except Exception as e:
                logger.warning(f"Search failed for query '{query}': {e}")
                continue
        
        return competitors
    
    def _search_similar_sites(self, brand_name: str, website_url: str) -> List[Dict[str, str]]:
        """Search for similar sites using alternative approaches."""
        competitors = []
        
        try:
            # Extract domain for similar site searches
            domain = urlparse(website_url).netloc
            
            # Search for "sites like" queries
            similar_queries = [
                f"sites like {domain}",
                f"websites similar to {domain}",
                f"alternatives to {domain}",
                f"{brand_name} similar websites"
            ]
            
            for query in similar_queries:
                found_competitors = self._perform_web_search(query, website_url)
                competitors.extend(found_competitors)
                time.sleep(random.uniform(0.5, 1))
                
        except Exception as e:
            logger.warning(f"Similar sites search failed: {e}")
        
        return competitors
    
    def _search_industry_specific(self, category: str, brand_name: str, website_url: str) -> List[Dict[str, str]]:
        """Search for competitors using industry-specific terms."""
        competitors = []
        
        # Industry-specific competitor databases and directories
        industry_queries = {
            "gaming": [
                "gaming supplement brands",
                "esports energy drinks",
                "gamer nutrition companies",
                "gaming lifestyle brands"
            ],
            "fashion": [
                "fashion ecommerce brands",
                "clothing online stores",
                "fashion retailers",
                "apparel brands"
            ],
            "beauty": [
                "beauty ecommerce sites",
                "cosmetics brands online",
                "skincare companies",
                "makeup retailers"
            ],
            "fitness": [
                "fitness supplement brands",
                "workout nutrition companies",
                "fitness apparel stores",
                "health supplement retailers"
            ],
            "default": [
                f"{category} online brands",
                f"{category} ecommerce companies",
                f"{category} retail stores",
                f"{category} direct to consumer brands"
            ]
        }
        
        queries = industry_queries.get(category, industry_queries["default"])
        
        for query in queries:
            try:
                found_competitors = self._perform_web_search(query, website_url)
                competitors.extend(found_competitors)
                time.sleep(random.uniform(0.5, 1))
                
            except Exception as e:
                logger.warning(f"Industry search failed for '{query}': {e}")
                continue
        
        return competitors
    
    def _get_fallback_competitors(self, category: str, original_url: str) -> List[Dict[str, str]]:
        """Get fallback competitors from known popular Shopify stores by category."""
        fallback_stores = {
            "gaming": [
                {"name": "Razer", "url": "https://www.razer.com"},
                {"name": "SteelSeries", "url": "https://steelseries.com"},
                {"name": "HyperX", "url": "https://www.hyperxgaming.com"},
                {"name": "Corsair", "url": "https://www.corsair.com"}
            ],
            "fashion": [
                {"name": "Allbirds", "url": "https://www.allbirds.com"},
                {"name": "Everlane", "url": "https://www.everlane.com"},
                {"name": "Bombas", "url": "https://bombas.com"},
                {"name": "Outdoor Voices", "url": "https://outdoorvoices.com"}
            ],
            "beauty": [
                {"name": "Glossier", "url": "https://www.glossier.com"},
                {"name": "ColourPop", "url": "https://colourpop.com"},
                {"name": "Fenty Beauty", "url": "https://fentybeauty.com"},
                {"name": "Kylie Cosmetics", "url": "https://kyliecosmetics.com"}
            ],
            "fitness": [
                {"name": "Gymshark", "url": "https://www.gymshark.com"},
                {"name": "Lululemon", "url": "https://shop.lululemon.com"},
                {"name": "Alo Yoga", "url": "https://www.aloyoga.com"},
                {"name": "Athletic Greens", "url": "https://athleticgreens.com"}
            ],
            "default": [
                {"name": "Allbirds", "url": "https://www.allbirds.com"},
                {"name": "ColourPop", "url": "https://colourpop.com"},
                {"name": "Gymshark", "url": "https://www.gymshark.com"},
                {"name": "Bombas", "url": "https://bombas.com"}
            ]
        }
        
        stores = fallback_stores.get(category, fallback_stores["default"])
        competitors = []
        
        for store in stores:
            if self._is_valid_competitor_url(store["url"], original_url):
                competitors.append({
                    'name': store["name"],
                    'url': store["url"],
                    'source': 'fallback'
                })
        
        return competitors
    
    def _perform_web_search(self, query: str, original_url: str) -> List[Dict[str, str]]:
        """Perform actual web search and extract competitor URLs."""
        competitors = []
        
        try:
            # Use multiple search engines and methods
            search_methods = [
                self._search_duckduckgo,
                self._search_bing,
                self._search_startpage
            ]
            
            for search_method in search_methods:
                try:
                    results = search_method(query)
                    for url in results:
                        if self._is_valid_competitor_url(url, original_url):
                            # Check if it's a Shopify store
                            if self._is_shopify_store(url):
                                competitor_name = self._extract_brand_name_from_url(url)
                                competitors.append({
                                    'name': competitor_name,
                                    'url': url,
                                    'source': f'search_{search_method.__name__}'
                                })
                                logger.info(f"Found Shopify competitor: {competitor_name} ({url})")
                    
                    if competitors:  # If we found some, don't try other engines
                        break
                        
                except Exception as e:
                    logger.warning(f"Search method {search_method.__name__} failed: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"Web search failed for query '{query}': {e}")
        
        return competitors
    
    def _search_duckduckgo(self, query: str) -> List[str]:
        """Search using DuckDuckGo."""
        urls = []
        try:
            search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
            response = self.session.get(search_url, timeout=1)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract search result links
            for link in soup.find_all('a', class_='result__a')[:15]:
                href = link.get('href')  # type: ignore
                if href and isinstance(href, str) and href.startswith('http'):
                    urls.append(href)
                    
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
        
        return urls
    
    def _search_bing(self, query: str) -> List[str]:
        """Search using Bing."""
        urls = []
        try:
            search_url = f"https://www.bing.com/search?q={quote_plus(query)}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(search_url, headers=headers, timeout=1)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract Bing search results
            for link in soup.find_all('a', href=True)[:20]:
                href = link.get('href')  # type: ignore
                if href and isinstance(href, str) and href.startswith('http') and 'bing.com' not in href:
                    urls.append(href)
                    
        except Exception as e:
            logger.warning(f"Bing search failed: {e}")
        
        return urls
    
    def _search_startpage(self, query: str) -> List[str]:
        """Search using Startpage."""
        urls = []
        try:
            search_url = f"https://www.startpage.com/sp/search?query={quote_plus(query)}"
            response = self.session.get(search_url, timeout=1)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract Startpage search results
            for link in soup.find_all('a', class_='w-gl__result-title')[:15]:
                href = link.get('href')  # type: ignore
                if href and isinstance(href, str) and href.startswith('http'):
                    urls.append(href)
                    
        except Exception as e:
            logger.warning(f"Startpage search failed: {e}")
        
        return urls
    
    def _deduplicate_and_validate_competitors(self, competitors: List[Dict[str, str]], original_url: str) -> List[Dict[str, str]]:
        """Remove duplicates and validate competitors."""
        seen_urls = set()
        seen_names = set()
        unique_competitors = []
        
        for competitor in competitors:
            url = competitor.get('url', '').lower()
            name = competitor.get('name', '').lower()
            
            # Skip if we've seen this URL or name
            if url in seen_urls or name in seen_names:
                continue
                
            # Skip if not valid
            if not self._is_valid_competitor_url(competitor.get('url', ''), original_url):
                continue
                
            seen_urls.add(url)
            seen_names.add(name)
            unique_competitors.append(competitor)
        
        return unique_competitors

    def _is_valid_competitor_url(self, url: str, original_url: str) -> bool:
        """Check if URL is a valid competitor (not the original site)."""
        try:
            parsed_original = urlparse(original_url)
            parsed_url = urlparse(url)
            
            # Skip if same domain
            if parsed_original.netloc == parsed_url.netloc:
                return False
            
            # Skip non-commercial domains
            excluded_domains = [
                'google.com', 'facebook.com', 'instagram.com', 'twitter.com',
                'youtube.com', 'wikipedia.org', 'amazon.com', 'ebay.com',
                'linkedin.com', 'reddit.com', 'pinterest.com'
            ]
            
            for excluded in excluded_domains:
                if excluded in parsed_url.netloc:
                    return False
            
            # Must be HTTPS and have valid TLD
            if not url.startswith('http'):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _is_shopify_store(self, url: str) -> bool:
        """Check if a website is powered by Shopify."""
        try:
            response = requests.get(url, timeout=1)
            content = response.text.lower()
            
            # Check for Shopify indicators
            shopify_indicators = [
                'shopify',
                'cdn.shopify.com',
                'myshopify.com',
                'shopify-analytics',
                'shopify_stats',
                'shop_id',
                'shopify.theme',
                'shopifycdn.com'
            ]
            
            for indicator in shopify_indicators:
                if indicator in content:
                    return True
            
            # Check response headers
            headers = response.headers
            if 'x-shopify-stage' in headers or 'x-shopid' in headers:
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Could not verify Shopify for {url}: {e}")
            return False
    
    def _extract_brand_name_from_url(self, url: str) -> str:
        """Extract brand name from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            
            # Remove TLD
            name = domain.split('.')[0]
            
            # Clean up the name
            name = re.sub(r'[^a-zA-Z0-9]', ' ', name)
            name = ' '.join(word.capitalize() for word in name.split())
            
            return name
            
        except Exception:
            return url
    
    def _deduplicate_competitors(self, competitors: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Remove duplicate competitors."""
        seen_urls = set()
        unique_competitors = []
        
        for competitor in competitors:
            url = competitor['url']
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            if domain not in seen_urls:
                seen_urls.add(domain)
                unique_competitors.append(competitor)
        
        return unique_competitors

    async def analyze_competitors(self, brand_name: str, website_url: str, insights_service) -> Dict[str, Any]:
        """Find competitors and extract insights from their Shopify stores."""
        logger.info(f"Starting competitor analysis for {brand_name}")
        
        # Find competitors
        competitors = self.find_competitors(brand_name, website_url)
        logger.info(f"Found {len(competitors)} potential competitors")
        
        competitor_insights = []
        
        for competitor in competitors:
            try:
                logger.info(f"Analyzing competitor: {competitor['name']} ({competitor['url']})")
                
                # Extract insights from competitor's store
                insights = await insights_service.fetch_insights(competitor['url'])
                
                competitor_data = {
                    'competitor_name': competitor['name'],
                    'competitor_url': competitor['url'],
                    'insights': insights.model_dump()
                }
                
                competitor_insights.append(competitor_data)
                
                # Rate limiting between competitor analysis
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to analyze competitor {competitor['name']}: {e}")
                continue
        
        analysis_result = {
            'original_brand': brand_name,
            'original_url': website_url,
            'competitors_found': len(competitors),
            'competitors_analyzed': len(competitor_insights),
            'competitor_insights': competitor_insights,
            'analysis_summary': self._generate_analysis_summary(competitor_insights)
        }
        
        return analysis_result
    
    def _generate_analysis_summary(self, competitor_insights: List[Dict]) -> Dict[str, Any]:
        """Generate a summary of competitor analysis."""
        if not competitor_insights:
            return {"message": "No competitor insights available"}
        
        summary = {
            'total_competitors': len(competitor_insights),
            'avg_products_per_store': 0,
            'common_social_platforms': {},
            'common_payment_methods': {},
            'common_faq_categories': {},
            'price_range_analysis': []
        }
        
        total_products = 0
        all_social_platforms = []
        all_payment_methods = []
        all_faq_categories = []
        
        for comp in competitor_insights:
            insights = comp.get('insights', {})
            
            # Count products
            products = insights.get('product_catalog', [])
            total_products += len(products)
            
            # Collect social platforms
            social_handles = insights.get('social_handles', {})
            for platform, handle in social_handles.items():
                if handle:
                    all_social_platforms.append(platform)
            
            # Collect payment methods
            payment_methods = insights.get('payment_methods', [])
            all_payment_methods.extend(payment_methods)
            
            # Collect FAQ categories
            faqs = insights.get('faqs', [])
            for faq in faqs:
                category = faq.get('category', 'General')
                all_faq_categories.append(category)
        
        # Calculate averages and frequencies
        if competitor_insights:
            summary['avg_products_per_store'] = total_products // len(competitor_insights)
        
        # Count frequencies
        from collections import Counter
        summary['common_social_platforms'] = dict(Counter(all_social_platforms).most_common(5))
        summary['common_payment_methods'] = dict(Counter(all_payment_methods).most_common(5))
        summary['common_faq_categories'] = dict(Counter(all_faq_categories).most_common(5))
        
        return summary
