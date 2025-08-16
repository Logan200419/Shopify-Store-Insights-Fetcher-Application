import re
import html
import requests
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from .base_extractor import BaseExtractor, safe_get_text, safe_find_all, safe_find


class FAQExtractor(BaseExtractor):
    """Extract FAQ information from Shopify stores."""
    
    def extract(self) -> List[Dict]:
        """Extract FAQ data from the store."""
        faq_data = []
        
        print(f"[DEBUG] Starting FAQ extraction for: {self.base_url}")
        
        # First try to extract from current page
        page_faqs = self._extract_from_current_page()
        print(f"[DEBUG] Found {len(page_faqs)} FAQs from current page")
        if page_faqs:
            faq_data.extend(page_faqs)
        
        # Try to find dedicated FAQ pages
        dedicated_faqs = self._extract_from_dedicated_pages()
        print(f"[DEBUG] Found {len(dedicated_faqs)} FAQs from dedicated pages")
        if dedicated_faqs:
            faq_data.extend(dedicated_faqs)
        
        # Remove duplicates
        unique_faqs = self._remove_duplicate_faqs(faq_data)
        print(f"[DEBUG] Final FAQ count after deduplication: {len(unique_faqs)}")
        
        # Show sample FAQs for debugging
        if unique_faqs:
            print(f"[DEBUG] Sample FAQ: {unique_faqs[0]}")
        
        return unique_faqs
    
    def _extract_from_current_page(self) -> List[Dict]:
        """Extract FAQ data from the current page soup."""
        faqs = []
        
        # Look for FAQ sections in current page
        faq_containers = safe_find_all(self.soup, ['div', 'section'], class_=re.compile(r'faq|question|help', re.I))
        
        if not faq_containers:
            # Try to find by ID
            faq_containers = safe_find_all(self.soup, ['div', 'section'], id=re.compile(r'faq|question|help', re.I))
        
        for container in faq_containers:
            container_faqs = self._parse_faq_html(container)
            faqs.extend(container_faqs)
        
        return faqs
    
    def _extract_from_dedicated_pages(self) -> List[Dict]:
        """Extract FAQ data from dedicated FAQ pages."""
        faq_urls = self._get_faq_urls()
        all_faqs = []
        
        for faq_url in faq_urls:
            try:
                # First try JSON endpoint
                json_url = f"{faq_url}.json"
                json_faqs = self._extract_from_json_endpoint(json_url)
                if json_faqs:
                    all_faqs.extend(json_faqs)
                    continue
                
                # Fallback to HTML parsing
                html_faqs = self._extract_from_html(faq_url)
                if html_faqs:
                    all_faqs.extend(html_faqs)
                    
            except Exception as e:
                # Silently continue to next URL
                continue
        
        return all_faqs
    
    def _get_faq_urls(self) -> List[str]:
        """Generate possible FAQ URLs."""
        base_domain = self.base_url.rstrip('/')
        return [
            f"{base_domain}/pages/faq",
            f"{base_domain}/pages/frequently-asked-questions", 
            f"{base_domain}/pages/help",
            f"{base_domain}/pages/support",
            f"{base_domain}/pages/customer-service",
            f"{base_domain}/faq",
            f"{base_domain}/help",
            f"{base_domain}/support"
        ]
    
    def _extract_from_json_endpoint(self, json_url: str) -> Optional[List[Dict]]:
        """Extract FAQ data from JSON endpoint."""
        try:
            response = requests.get(json_url, timeout=30)
            if response.status_code != 200:
                return None
            
            data = response.json()
            page_data = data.get('page', {})
            
            if not page_data:
                return None
            
            # Parse the HTML content from the JSON response
            body_html = page_data.get('body_html', '')
            if not body_html:
                return None
            
            # Decode HTML entities
            body_html = html.unescape(body_html)
            
            # Parse FAQ content
            soup = BeautifulSoup(body_html, 'html.parser')
            return self._parse_faq_html(soup)
            
        except Exception:
            return None
    
    def _extract_from_html(self, html_url: str) -> Optional[List[Dict]]:
        """Extract FAQ data from HTML page."""
        try:
            response = requests.get(html_url, timeout=30)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find FAQ content in various containers
            faq_containers = safe_find_all(soup, ['div', 'section'], class_=re.compile(r'faq|question|help', re.I))
            
            if not faq_containers:
                # Try to find content by structure
                faq_containers = safe_find_all(soup, ['main', 'article', 'div'], id=re.compile(r'faq|question|help', re.I))
            
            if not faq_containers:
                # Fallback to main content areas
                main_content = safe_find(soup, 'main') or safe_find(soup, 'article') or safe_find(soup, '.content')
                if main_content:
                    faq_containers = [main_content]
            
            faqs = []
            for container in faq_containers:
                if container:
                    container_faqs = self._parse_faq_html(container)
                    faqs.extend(container_faqs)
            
            return faqs
            
        except Exception:
            return None
    
    def _parse_faq_html(self, element) -> List[Dict]:
        """Parse FAQ items from HTML element."""
        if not element:
            return []
            
        faqs = []
        
        # Method 1: Look for h3/h2 + p patterns (like GFUEL)
        headers = safe_find_all(element, ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        for header in headers:
            if not header:
                continue
                
            question_text = self._clean_text(safe_get_text(header))
            if not question_text or len(question_text) < 5:
                continue
            
            # Skip headers that are just categories
            if self._is_category_header(question_text):
                continue
            
            # Find answer content after the header
            answer_elements = []
            current = header.next_sibling
            
            while current:
                if isinstance(current, str):
                    current = getattr(current, 'next_sibling', None)
                    continue
                
                if hasattr(current, 'name') and current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    break
                
                if hasattr(current, 'name') and current.name in ['p', 'div', 'ul', 'ol', 'li']:
                    answer_elements.append(current)
                
                current = getattr(current, 'next_sibling', None)
            
            if answer_elements:
                answer_text = ' '.join([self._clean_text(safe_get_text(elem)) for elem in answer_elements])
                if answer_text and len(answer_text) > 10:
                    faqs.append({
                        "question": question_text,
                        "answer": answer_text,
                        "category": self._categorize_question(question_text)
                    })
        
        # Method 2: Look for accordion/toggle patterns
        if not faqs:
            faqs.extend(self._parse_accordion_faqs(element))
        
        # Method 3: Look for definition lists (dl/dt/dd)
        if not faqs:
            faqs.extend(self._parse_definition_list_faqs(element))
        
        return faqs
    
    def _parse_accordion_faqs(self, element) -> List[Dict]:
        """Parse FAQ items from accordion/toggle structures."""
        faqs = []
        
        # Look for common accordion patterns
        accordion_items = safe_find_all(element, ['div', 'section'], class_=re.compile(r'accordion|toggle|collaps|expand', re.I))
        
        for item in accordion_items:
            if not item:
                continue
                
            question_elem = safe_find(item, ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'button', 'summary'])
            answer_elem = safe_find(item, ['div', 'p'], class_=re.compile(r'content|answer|body', re.I))
            
            if question_elem and answer_elem:
                question = self._clean_text(safe_get_text(question_elem))
                answer = self._clean_text(safe_get_text(answer_elem))
                
                if question and answer and len(question) > 5 and len(answer) > 10:
                    faqs.append({
                        "question": question,
                        "answer": answer,
                        "category": self._categorize_question(question)
                    })
        
        return faqs
    
    def _parse_definition_list_faqs(self, element) -> List[Dict]:
        """Parse FAQ items from definition lists (dl/dt/dd)."""
        faqs = []
        
        definition_lists = safe_find_all(element, 'dl')
        for dl in definition_lists:
            if not dl:
                continue
                
            terms = safe_find_all(dl, 'dt')
            definitions = safe_find_all(dl, 'dd')
            
            for i, term in enumerate(terms):
                if i < len(definitions) and term and definitions[i]:
                    question = self._clean_text(safe_get_text(term))
                    answer = self._clean_text(safe_get_text(definitions[i]))
                    
                    if question and answer and len(question) > 5 and len(answer) > 10:
                        faqs.append({
                            "question": question,
                            "answer": answer,
                            "category": self._categorize_question(question)
                        })
        
        return faqs
    
    def _categorize_question(self, question: str) -> str:
        """Categorize a question based on its content."""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['ship', 'deliver', 'order', 'track']):
            return "Shipping & Orders"
        elif any(word in question_lower for word in ['return', 'refund', 'exchange', 'warranty']):
            return "Returns & Refunds"
        elif any(word in question_lower for word in ['payment', 'billing', 'credit', 'paypal', 'price']):
            return "Payment & Billing"
        elif any(word in question_lower for word in ['account', 'login', 'password', 'profile']):
            return "Account & Profile"
        elif any(word in question_lower for word in ['product', 'size', 'ingredient', 'material', 'specification']):
            return "Product Information"
        elif any(word in question_lower for word in ['subscription', 'recurring', 'auto', 'membership']):
            return "Subscription"
        elif any(word in question_lower for word in ['contact', 'support', 'help', 'phone', 'email']):
            return "Customer Support"
        else:
            return "General"
    
    def _is_category_header(self, text: str) -> bool:
        """Check if a header is likely a category rather than a question."""
        text_lower = text.lower().strip()
        
        # Common category patterns
        category_patterns = [
            r'^(general|shipping|payment|product|account|subscription|support).*info.*$',
            r'^(faq|faqs)$',
            r'^.*information$',
            r'^additional.*$',
            r'^.*program.*faq.*$'
        ]
        
        for pattern in category_patterns:
            if re.match(pattern, text_lower):
                return True
        
        return False
    
    def _remove_duplicate_faqs(self, faqs: List[Dict]) -> List[Dict]:
        """Remove duplicate FAQ entries."""
        unique_faqs = []
        seen_questions = set()
        
        for faq in faqs:
            question_key = faq['question'].lower().strip()
            if question_key not in seen_questions:
                unique_faqs.append(faq)
                seen_questions.add(question_key)
        
        return unique_faqs
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common HTML artifacts
        text = re.sub(r'[\u00a0\u200b\u200c\u200d\ufeff]', ' ', text)
        
        # Clean up question marks and formatting
        text = re.sub(r'\s*\?\s*$', '?', text)
        text = re.sub(r'\s*:\s*$', ':', text)
        
        return text.strip()
