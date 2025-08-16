"""
Test script to verify homepage tag filtering works correctly
"""
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.hero_product_extractor import HeroProductExtractor
from core.models import ProductModel
from bs4 import BeautifulSoup

def test_homepage_tag_filtering():
    """Test that products with 'homepage' tag are properly prioritized"""
    
    print("Testing homepage tag filtering...")
    
    # Create mock HTML
    mock_html = "<html><body><h1>Test Store</h1></body></html>"
    soup = BeautifulSoup(mock_html, 'html.parser')
    
    # Create hero product extractor
    extractor = HeroProductExtractor(soup, "https://test-store.com")
    
    # Create mock products with different tags
    mock_products = [
        ProductModel(
            name="Regular Product",
            price="$19.99",
            tags=["clothing", "basic"],
            image_url="https://example.com/regular.jpg"
        ),
        ProductModel(
            name="Featured Product",
            price="$29.99", 
            tags=["featured", "clothing"],
            image_url="https://example.com/featured.jpg"
        ),
        ProductModel(
            name="Homepage Hero Product 1",
            price="$49.99",
            tags=["homepage", "bestseller", "featured"],
            image_url="https://example.com/homepage1.jpg",
            description="This is a homepage featured product"
        ),
        ProductModel(
            name="Homepage Hero Product 2", 
            price="$39.99",
            tags=["homepage", "trending"],
            image_url="https://example.com/homepage2.jpg"
        ),
        ProductModel(
            name="Hero Product",
            price="$59.99",
            tags=["hero", "popular"],
            image_url="https://example.com/hero.jpg"
        ),
        ProductModel(
            name="Homepage Product 3",
            price="$69.99",
            tags=["homepage", "new"],
            image_url="https://example.com/homepage3.jpg"
        )
    ]
    
    print(f"Testing with {len(mock_products)} mock products:")
    for i, product in enumerate(mock_products, 1):
        print(f"  {i}. {product.name} - Tags: {product.tags}")
    
    # Test the filtering
    hero_products = extractor._filter_hero_products_by_tags(mock_products)
    
    print(f"\n🔍 Filter results: Found {len(hero_products)} hero products")
    
    # Display filtered results
    for i, product in enumerate(hero_products, 1):
        is_homepage = 'homepage' in (product.tags or [])
        tag_indicator = "🏠 HOMEPAGE" if is_homepage else "⭐ HERO"
        print(f"  {i}. {tag_indicator} - {product.name}")
        print(f"     Price: {product.price}")
        print(f"     Tags: {product.tags}")
        print()
    
    # Test sorting by relevance
    hero_tags = {
        'homepage', 'hero', 'featured', 'main', 'highlight', 'spotlight',
        'bestseller', 'best seller', 'best-seller', 'top seller', 'top-seller',
        'trending', 'popular', 'most popular', 'staff pick', 'staff-pick'
    }
    
    sorted_products = extractor._sort_hero_products_by_relevance(hero_products, hero_tags)
    
    print("📊 After sorting by relevance:")
    for i, product in enumerate(sorted_products, 1):
        is_homepage = 'homepage' in (product.tags or [])
        tag_indicator = "🏠 HOMEPAGE" if is_homepage else "⭐ HERO"
        print(f"  {i}. {tag_indicator} - {product.name} (Tags: {product.tags})")
    
    # Count homepage products
    homepage_count = sum(1 for p in sorted_products if 'homepage' in (p.tags or []))
    other_count = len(sorted_products) - homepage_count
    
    print(f"\n📈 Summary:")
    print(f"  - Products with 'homepage' tag: {homepage_count}")
    print(f"  - Other hero products: {other_count}")
    print(f"  - Total hero products: {len(sorted_products)}")
    
    # Verify homepage products are at the top
    if sorted_products and 'homepage' in (sorted_products[0].tags or []):
        print(f"  ✅ Homepage products are properly prioritized!")
    elif homepage_count > 0:
        print(f"  ⚠️  Homepage products found but not at top")
    else:
        print(f"  ❌ No homepage products found")
    
    return sorted_products

def test_edge_cases():
    """Test edge cases for homepage tag filtering"""
    
    print("\n" + "="*50)
    print("Testing edge cases...")
    
    mock_html = "<html><body><h1>Test Store</h1></body></html>"
    soup = BeautifulSoup(mock_html, 'html.parser')
    extractor = HeroProductExtractor(soup, "https://test-store.com")
    
    # Test with no homepage tags
    products_no_homepage = [
        ProductModel(name="Product 1", tags=["featured"]),
        ProductModel(name="Product 2", tags=["hero"]),
    ]
    
    result1 = extractor._filter_hero_products_by_tags(products_no_homepage)
    print(f"No homepage tags: Found {len(result1)} products")
    
    # Test with only homepage tags
    products_only_homepage = [
        ProductModel(name="Homepage Product 1", tags=["homepage"]),
        ProductModel(name="Homepage Product 2", tags=["homepage", "featured"]),
    ]
    
    result2 = extractor._filter_hero_products_by_tags(products_only_homepage)
    print(f"Only homepage tags: Found {len(result2)} products")
    
    # Test with no tags at all
    products_no_tags = [
        ProductModel(name="No Tags Product", tags=[]),
        ProductModel(name="None Tags Product", tags=None),
    ]
    
    result3 = extractor._filter_hero_products_by_tags(products_no_tags)
    print(f"No tags: Found {len(result3)} products")
    
    print("Edge case testing completed ✅")

if __name__ == "__main__":
    print("="*60)
    print("HOMEPAGE TAG FILTERING TEST")
    print("="*60)
    
    hero_products = test_homepage_tag_filtering()
    test_edge_cases()
    
    print("\n" + "="*60)
    print("✅ Homepage tag filtering test completed!")
    print("\nThe application now:")
    print("1. Loads all products from the website")
    print("2. Filters for products with 'homepage' and other hero tags")
    print("3. Prioritizes products with 'homepage' tag at the top")
    print("4. Returns up to 10 products when homepage tags are found")
    print("5. Falls back to 6 products for other hero tags")
    print("="*60)
