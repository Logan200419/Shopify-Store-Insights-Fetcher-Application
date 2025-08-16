"""
Test script for the new tag-based hero product extraction
"""
import asyncio
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.hero_product_extractor import HeroProductExtractor
from core.utils import WebScraper
from bs4 import BeautifulSoup

async def test_hero_product_extraction():
    """Test the new tag-based hero product extraction"""
    
    print("Testing new tag-based hero product extraction...")
    
    # Test with a mock Shopify store URL
    test_url = "https://allbirds.com"  # Real Shopify store for testing
    
    try:
        # Create scraper and fetch the homepage
        scraper = WebScraper()
        print(f"Fetching homepage: {test_url}")
        
        html_content = await scraper.fetch_page(test_url)
        if not html_content:
            print("❌ Failed to fetch homepage content")
            return False
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Create hero product extractor with scraper
        hero_extractor = HeroProductExtractor(soup, test_url, scraper)
        
        print("🔍 Extracting hero products by loading all products and filtering by tags...")
        hero_products = await hero_extractor.extract_async()
        
        print(f"\n✅ Found {len(hero_products)} hero products")
        
        # Display results
        for i, product in enumerate(hero_products, 1):
            print(f"\n{i}. {product.name}")
            print(f"   Price: {product.price or 'N/A'}")
            print(f"   URL: {product.product_url or 'N/A'}")
            print(f"   Tags: {product.tags or 'N/A'}")
            print(f"   Image: {product.image_url or 'N/A'}")
            if product.description:
                print(f"   Description: {product.description[:100]}...")
        
        # Test tag filtering logic
        print(f"\n🏷️  Testing tag filtering logic...")
        
        # Create some mock products with different tags
        from core.models import ProductModel
        
        mock_products = [
            ProductModel(
                name="Featured Product 1",
                price="$29.99",
                tags=["featured", "clothing", "new"]
            ),
            ProductModel(
                name="Homepage Hero Product",
                price="$49.99", 
                tags=["homepage", "hero", "bestseller"]
            ),
            ProductModel(
                name="Regular Product",
                price="$19.99",
                tags=["clothing", "basic"]
            ),
            ProductModel(
                name="Trending Product",
                price="$39.99",
                tags=["trending", "popular", "staff-pick"]
            )
        ]
        
        hero_filtered = hero_extractor._filter_hero_products_by_tags(mock_products)
        print(f"Mock test: Found {len(hero_filtered)} hero products from {len(mock_products)} total products")
        
        for product in hero_filtered:
            print(f"  - {product.name} (tags: {product.tags})")
        
        print(f"\n🎉 Hero product extraction test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during hero product extraction test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_sync_version():
    """Test the synchronous version as fallback"""
    print("\n🔄 Testing synchronous fallback version...")
    
    try:
        # Mock HTML for testing
        mock_html = """
        <html>
            <head><title>Test Store</title></head>
            <body>
                <div class="hero-section">
                    <div class="product-card">
                        <h3>Hero Product 1</h3>
                        <span class="price">$99.99</span>
                        <img src="/hero-product-1.jpg" alt="Hero Product 1">
                    </div>
                </div>
                <div class="featured-products">
                    <div class="product-item">
                        <h4>Featured Product 2</h4>
                        <span class="price">$79.99</span>
                    </div>
                </div>
            </body>
        </html>
        """
        
        soup = BeautifulSoup(mock_html, 'html.parser')
        hero_extractor = HeroProductExtractor(soup, "https://test-store.com")
        
        # Test position-based fallback
        hero_products = hero_extractor._extract_hero_products_by_position()
        print(f"Position-based extraction found {len(hero_products)} products")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in sync test: {str(e)}")
        return False

async def main():
    """Main test function"""
    print("=" * 60)
    print("HERO PRODUCT EXTRACTION TEST")
    print("=" * 60)
    
    # Test the new async tag-based approach
    success1 = await test_hero_product_extraction()
    
    # Test the sync fallback
    success2 = test_sync_version()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("✅ All hero product extraction tests passed!")
        print("\nNew approach summary:")
        print("1. Load all products from /products.json API")
        print("2. Filter products by homepage/hero tags")
        print("3. Sort by tag relevance and completeness")
        print("4. Fallback to position-based extraction if needed")
    else:
        print("❌ Some tests failed")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
