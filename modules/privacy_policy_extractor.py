"""
Privacy policy extraction module for Shopify stores
Handles extraction of privacy policies, terms of service, and related legal documents
"""
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
import re
import logging
from urllib.parse import urljoin, urlparse
from core.models import PolicyModel
from .base_extractor import BaseExtractor, safe_get_attr, safe_get_text, safe_find_all, safe_find

logger = logging.getLogger(__name__)

class PrivacyPolicyExtractor(BaseExtractor):
    """Extract privacy policies and related legal documents from Shopify stores"""
    
    def extract(self) -> List[PolicyModel]:
        """Extract all privacy-related policies"""
        policies = []
        
        # Extract different types of policies
        policies.extend(self._extract_privacy_policies())
        policies.extend(self._extract_terms_of_service())
        policies.extend(self._extract_cookie_policies())
        policies.extend(self._extract_data_protection_policies())
        policies.extend(self._extract_refund_policies())
        policies.extend(self._extract_shipping_policies())
        
        # Remove duplicates
        unique_policies = self._deduplicate_policies(policies)
        
        logger.info(f"Extracted {len(unique_policies)} policy documents")
        return unique_policies
    
    def _extract_privacy_policies(self) -> List[PolicyModel]:
        """Extract privacy policy documents"""
        policies = []
        
        # Look for privacy policy links
        privacy_links = self._find_policy_links(['privacy', 'privacy-policy', 'privacy_policy'])
        
        for link in privacy_links:
            policy = self._extract_policy_from_link(link, "Privacy Policy")
            if policy:
                policies.append(policy)
        
        # Look for embedded privacy policy content
        privacy_content = self._find_embedded_policy_content(['privacy', 'data protection'])
        if privacy_content:
            policy = PolicyModel(
                title="Privacy Policy",
                content=privacy_content,
                url=self.base_url
            )
            policies.append(policy)
        
        return policies
    
    def _extract_terms_of_service(self) -> List[PolicyModel]:
        """Extract terms of service documents"""
        policies = []
        
        # Look for terms of service links
        terms_patterns = [
            'terms', 'terms-of-service', 'terms_of_service', 'terms-and-conditions',
            'terms_and_conditions', 'tos', 'legal', 'conditions'
        ]
        terms_links = self._find_policy_links(terms_patterns)
        
        for link in terms_links:
            policy = self._extract_policy_from_link(link, "Terms of Service")
            if policy:
                policies.append(policy)
        
        # Look for embedded terms content
        terms_content = self._find_embedded_policy_content(['terms', 'conditions', 'agreement'])
        if terms_content:
            policy = PolicyModel(
                title="Terms of Service",
                content=terms_content,
                url=self.base_url
            )
            policies.append(policy)
        
        return policies
    
    def _extract_cookie_policies(self) -> List[PolicyModel]:
        """Extract cookie policy documents"""
        policies = []
        
        # Look for cookie policy links
        cookie_patterns = ['cookie', 'cookies', 'cookie-policy', 'cookie_policy']
        cookie_links = self._find_policy_links(cookie_patterns)
        
        for link in cookie_links:
            policy = self._extract_policy_from_link(link, "Cookie Policy")
            if policy:
                policies.append(policy)
        
        return policies
    
    def _extract_data_protection_policies(self) -> List[PolicyModel]:
        """Extract data protection and GDPR policies"""
        policies = []
        
        # Look for data protection links
        data_patterns = [
            'data-protection', 'data_protection', 'gdpr', 'ccpa',
            'data-privacy', 'data_privacy'
        ]
        data_links = self._find_policy_links(data_patterns)
        
        for link in data_links:
            policy = self._extract_policy_from_link(link, "Data Protection Policy")
            if policy:
                policies.append(policy)
        
        return policies
    
    def _extract_refund_policies(self) -> List[PolicyModel]:
        """Extract refund and return policies"""
        policies = []
        
        # Look for refund policy links
        refund_patterns = [
            'refund', 'refunds', 'return', 'returns', 'refund-policy',
            'refund_policy', 'return-policy', 'return_policy',
            'exchange', 'exchanges'
        ]
        refund_links = self._find_policy_links(refund_patterns)
        
        for link in refund_links:
            policy = self._extract_policy_from_link(link, "Refund Policy")
            if policy:
                policies.append(policy)
        
        return policies
    
    def _extract_shipping_policies(self) -> List[PolicyModel]:
        """Extract shipping and delivery policies"""
        policies = []
        
        # Look for shipping policy links
        shipping_patterns = [
            'shipping', 'delivery', 'shipping-policy', 'shipping_policy',
            'delivery-policy', 'delivery_policy', 'fulfillment'
        ]
        shipping_links = self._find_policy_links(shipping_patterns)
        
        for link in shipping_links:
            policy = self._extract_policy_from_link(link, "Shipping Policy")
            if policy:
                policies.append(policy)
        
        return policies
    
    def _find_policy_links(self, patterns: List[str]) -> List:
        """Find links that match policy patterns"""
        policy_links = []
        
        # Create regex pattern
        pattern_regex = '|'.join(patterns)
        
        # Look in footer links
        footer_links = self._find_footer_links(pattern_regex)
        policy_links.extend(footer_links)
        
        # Look in navigation links
        nav_links = self._find_navigation_links(pattern_regex)
        policy_links.extend(nav_links)
        
        # Look in general page links
        general_links = self._find_general_links(pattern_regex)
        policy_links.extend(general_links)
        
        return policy_links
    
    def _find_footer_links(self, pattern: str) -> List:
        """Find policy links in footer"""
        footer_links = []
        
        # Common footer selectors
        footer_selectors = [
            'footer',
            '.footer',
            '.site-footer',
            '.page-footer',
            '#footer'
        ]
        
        for selector in footer_selectors:
            footer = safe_find(self.soup, 'css', selector)
            if footer:
                links = safe_find_all(footer, 'a', href=re.compile(pattern, re.IGNORECASE))
                footer_links.extend(links)
                
                # Also check link text
                all_links = safe_find_all(footer, 'a')
                for link in all_links:
                    link_text = safe_get_text(link).lower()
                    if re.search(pattern, link_text, re.IGNORECASE):
                        footer_links.append(link)
        
        return footer_links
    
    def _find_navigation_links(self, pattern: str) -> List:
        """Find policy links in navigation"""
        nav_links = []
        
        # Common navigation selectors
        nav_selectors = [
            'nav',
            '.nav',
            '.navigation',
            '.main-nav',
            '.site-nav',
            '#navigation'
        ]
        
        for selector in nav_selectors:
            nav = safe_find(self.soup, 'css', selector)
            if nav:
                links = safe_find_all(nav, 'a', href=re.compile(pattern, re.IGNORECASE))
                nav_links.extend(links)
                
                # Also check link text
                all_links = safe_find_all(nav, 'a')
                for link in all_links:
                    link_text = safe_get_text(link).lower()
                    if re.search(pattern, link_text, re.IGNORECASE):
                        nav_links.append(link)
        
        return nav_links
    
    def _find_general_links(self, pattern: str) -> List:
        """Find policy links throughout the page"""
        # Look for links with matching href
        href_links = safe_find_all(self.soup, 'a', href=re.compile(pattern, re.IGNORECASE))
        
        # Look for links with matching text
        text_links = []
        all_links = safe_find_all(self.soup, 'a')
        for link in all_links:
            link_text = safe_get_text(link).lower()
            if re.search(pattern, link_text, re.IGNORECASE):
                text_links.append(link)
        
        return href_links + text_links
    
    def _find_embedded_policy_content(self, keywords: List[str]) -> Optional[str]:
        """Find policy content embedded in the current page"""
        content_parts = []
        
        # Look for sections containing policy keywords
        for keyword in keywords:
            # Look for headings containing the keyword
            headings = safe_find_all(self.soup, re.compile(r'^h[1-6]$'))
            for heading in headings:
                heading_text = safe_get_text(heading).lower()
                if keyword in heading_text:
                    # Extract content after this heading
                    section_content = self._extract_section_content_after_heading(heading)
                    if section_content:
                        content_parts.append(f"## {safe_get_text(heading)}\\n{section_content}")
        
        return "\\n\\n".join(content_parts) if content_parts else None
    
    def _extract_section_content_after_heading(self, heading) -> Optional[str]:
        """Extract content that appears after a heading"""
        content_parts = []
        current = heading.next_sibling
        
        while current and current.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            if hasattr(current, 'get_text'):
                text = safe_get_text(current).strip()
                if text and len(text) > 10:
                    content_parts.append(text)
            current = current.next_sibling
            
            # Limit to prevent infinite loops
            if len(content_parts) > 10:
                break
        
        return "\\n".join(content_parts) if content_parts else None
    
    def _extract_policy_from_link(self, link, default_title: str) -> Optional[PolicyModel]:
        """Extract policy information from a link element"""
        try:
            href = safe_get_attr(link, 'href')
            if not href:
                return None
            
            # Resolve relative URLs
            policy_url = self._resolve_url(href)
            
            # Extract title from link text or use default
            title = safe_get_text(link).strip()
            if not title or len(title) < 3:
                title = default_title
            
            # For links, we only have basic info, no content yet
            return PolicyModel(
                title=self._clean_text(title),
                content="Policy content available at the linked URL",
                url=policy_url
            )
            
        except Exception as e:
            logger.debug(f"Error extracting policy from link: {str(e)}")
            return None
    
    def _determine_policy_type(self, url: str, title: str) -> str:
        """Determine the type of policy based on URL and title"""
        combined_text = f"{url} {title}".lower()
        
        if any(word in combined_text for word in ['privacy', 'data protection', 'gdpr']):
            return "privacy"
        elif any(word in combined_text for word in ['terms', 'conditions', 'agreement']):
            return "terms"
        elif any(word in combined_text for word in ['cookie', 'cookies']):
            return "cookie"
        elif any(word in combined_text for word in ['refund', 'return', 'exchange']):
            return "refund"
        elif any(word in combined_text for word in ['shipping', 'delivery', 'fulfillment']):
            return "shipping"
        else:
            return "legal"
    
    def _deduplicate_policies(self, policies: List[PolicyModel]) -> List[PolicyModel]:
        """Remove duplicate policies based on URL and title"""
        seen = set()
        unique_policies = []
        
        for policy in policies:
            # Create a unique identifier
            identifier = (policy.url.lower() if policy.url else '', 
                         policy.title.lower() if policy.title else '')
            
            if identifier not in seen and policy.title:
                seen.add(identifier)
                unique_policies.append(policy)
        
        return unique_policies

class PolicyDetailExtractor(BaseExtractor):
    """Specialized extractor for detailed policy content from policy pages"""
    
    def extract(self) -> Optional[PolicyModel]:
        """Extract detailed policy content from a policy page"""
        # Extract title
        title = self._extract_policy_title()
        
        # Extract main content
        content = self._extract_policy_content()
        
        if title and content:
            return PolicyModel(
                title=title,
                content=content,
                url=self.base_url
            )
        
        return None
    
    def _extract_policy_title(self) -> Optional[str]:
        """Extract the policy title from the page"""
        # Try different title selectors
        title_selectors = [
            'h1',
            '.page-title',
            '.policy-title',
            '.legal-title',
            'title'
        ]
        
        for selector in title_selectors:
            title_elem = safe_find(self.soup, selector)
            if title_elem:
                title = safe_get_text(title_elem).strip()
                if title and len(title) > 3:
                    return self._clean_text(title)
        
        return None
    
    def _extract_policy_content(self) -> Optional[str]:
        """Extract the main policy content"""
        content_parts = []
        
        # Try different content selectors
        content_selectors = [
            '.policy-content',
            '.legal-content',
            '.page-content',
            '.main-content',
            '.content',
            'main',
            '.rte'  # Rich text editor content in Shopify
        ]
        
        for selector in content_selectors:
            content_elem = safe_find(self.soup, selector)
            if content_elem:
                # Extract text while preserving structure
                content = self._extract_structured_text(content_elem)
                if content and len(content) > 100:
                    content_parts.append(content)
        
        # If no structured content found, try extracting from body
        if not content_parts:
            body_content = self._extract_body_content()
            if body_content:
                content_parts.append(body_content)
        
        return "\\n\\n".join(content_parts) if content_parts else None
    
    def _extract_structured_text(self, element) -> str:
        """Extract text while preserving basic structure"""
        text_parts = []
        
        for child in element.children:
            if hasattr(child, 'name'):
                if child.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    text_parts.append(f"\\n## {safe_get_text(child)}\\n")
                elif child.name in ['p', 'div']:
                    text = safe_get_text(child).strip()
                    if text:
                        text_parts.append(text)
                elif child.name == 'ul':
                    list_items = safe_find_all(child, 'li')
                    for item in list_items:
                        item_text = safe_get_text(item).strip()
                        if item_text:
                            text_parts.append(f"• {item_text}")
                elif child.name == 'ol':
                    list_items = safe_find_all(child, 'li')
                    for i, item in enumerate(list_items, 1):
                        item_text = safe_get_text(item).strip()
                        if item_text:
                            text_parts.append(f"{i}. {item_text}")
            elif hasattr(child, 'string') and child.string:
                text = child.string.strip()
                if text:
                    text_parts.append(text)
        
        return "\\n".join(text_parts)
    
    def _extract_body_content(self) -> Optional[str]:
        """Extract content from body as fallback"""
        # Remove navigation, header, footer
        for elem in self.soup(['nav', 'header', 'footer', 'script', 'style']):
            elem.decompose()
        
        # Extract remaining text
        body = safe_find(self.soup, 'body')
        if body:
            text = safe_get_text(body)
            # Clean up excessive whitespace
            text = re.sub(r'\\n\\s*\\n', '\\n\\n', text)
            text = re.sub(r' +', ' ', text)
            return text.strip()
        
        return None
    
    def _extract_last_updated_date(self) -> Optional[str]:
        """Extract the last updated date if available"""
        date_patterns = [
            r'last updated:?\\s*([\\d/\\-\\.]+)',
            r'updated:?\\s*([\\d/\\-\\.]+)',
            r'effective:?\\s*([\\d/\\-\\.]+)',
            r'revised:?\\s*([\\d/\\-\\.]+)'
        ]
        
        page_text = safe_get_text(self.soup).lower()
        
        for pattern in date_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _determine_policy_type_from_content(self, title: str, content: str) -> str:
        """Determine policy type from title and content"""
        combined_text = f"{title} {content}".lower() if title and content else ""
        
        if any(word in combined_text for word in ['privacy', 'personal data', 'gdpr', 'data protection']):
            return "privacy"
        elif any(word in combined_text for word in ['terms of service', 'terms and conditions', 'user agreement']):
            return "terms"
        elif any(word in combined_text for word in ['cookie', 'cookies', 'tracking']):
            return "cookie"
        elif any(word in combined_text for word in ['refund', 'return', 'exchange', 'money back']):
            return "refund"
        elif any(word in combined_text for word in ['shipping', 'delivery', 'fulfillment']):
            return "shipping"
        else:
            return "legal"
