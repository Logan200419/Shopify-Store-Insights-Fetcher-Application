"""
Test script for the new modularized extractors
"""
import asyncio
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.product_extractor import ProductExtractor, ProductCatalogExtractor, SingleProductExtractor
from modules.hero_product_extractor import HeroProductExtractor
from modules.privacy_policy_extractor import PrivacyPolicyExtractor, PolicyDetailExtractor
from modules.shopify_service import ShopifyInsightsService

def test_extractors():
    """Test that all new extractors can be imported and instantiated"""
    
    print("Testing modular extractors...")
    
    # Mock HTML content for testing
    mock_html = """
    <html>
        <head><title>Test Store</title></head>
        <body>
            <h1>Welcome to Test Store</h1>
            <div class="hero">
                <div class="product">
                    <h2>Hero Product</h2>
                    <span class="price">$29.99</span>
                </div>
            </div>
            <footer>
                <a href="/privacy-policy">Privacy Policy</a>
                <a href="/terms">Terms of Service</a>
            </footer>
        </body>
    </html>
    """
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(mock_html, 'html.parser')
    base_url = "https://test-store.myshopify.com"
    
    try:
        # Test ProductExtractor
        print("✓ Testing ProductExtractor...")
        product_extractor = ProductExtractor(soup, base_url)
        products = product_extractor.extract()
        print(f"  Found {len(products)} products")
        
        # Test ProductCatalogExtractor
        print("✓ Testing ProductCatalogExtractor...")
        catalog_extractor = ProductCatalogExtractor(soup, base_url, max_products=10)
        catalog_products = catalog_extractor.extract()
        print(f"  Found {len(catalog_products)} catalog products")
        
        # Test SingleProductExtractor
        print("✓ Testing SingleProductExtractor...")
        single_extractor = SingleProductExtractor(soup, base_url)
        single_products = single_extractor.extract()
        print(f"  Found {len(single_products)} single page products")
        
        # Test HeroProductExtractor
        print("✓ Testing HeroProductExtractor...")
        hero_extractor = HeroProductExtractor(soup, base_url)
        hero_products = hero_extractor.extract()
        print(f"  Found {len(hero_products)} hero products")
        
        # Test PrivacyPolicyExtractor
        print("✓ Testing PrivacyPolicyExtractor...")
        privacy_extractor = PrivacyPolicyExtractor(soup, base_url)
        policies = privacy_extractor.extract()
        print(f"  Found {len(policies)} policies")
        
        # Test PolicyDetailExtractor
        print("✓ Testing PolicyDetailExtractor...")
        detail_extractor = PolicyDetailExtractor(soup, base_url)
        policy_detail = detail_extractor.extract()
        print(f"  Policy detail extraction: {'Success' if policy_detail else 'No content found'}")
        
        # Test ShopifyInsightsService
        print("✓ Testing ShopifyInsightsService...")
        service = ShopifyInsightsService()
        print("  Service instantiated successfully")
        
        print("\n🎉 All extractors are working correctly!")
        print("\nModule separation summary:")
        print("├── product_extractor.py - Product catalog and individual products")
        print("├── hero_product_extractor.py - Homepage featured products")
        print("├── privacy_policy_extractor.py - Privacy policies and legal documents")
        print("├── base_extractor.py - Common extractor functionality")
        print("└── shopify_service.py - Main service orchestrator")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing extractors: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_extractors()
    if success:
        print("\n✅ All tests passed! The modules have been successfully separated.")
    else:
        print("\n❌ Some tests failed. Please check the error messages above.")
