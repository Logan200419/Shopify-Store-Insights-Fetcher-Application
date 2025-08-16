#!/usr/bin/env python3
"""
Test script to demonstrate the Shopify Insights Fetcher API functionality
"""

import asyncio
import json
from modules.shopify_service import ShopifyInsightsService

async def test_shopify_service():
    """Test the core service functionality"""
    service = ShopifyInsightsService()
    
    # Test with a known Shopify store (you can replace with any Shopify store URL)
    test_urls = [
        "https://www.gymshark.com/",  # Popular Shopify store
        "https://allbirds.com",       # Another popular Shopify store
    ]
    
    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"Testing URL: {url}")
        print(f"{'='*60}")
        
        try:
            insights = await service.fetch_insights(url)
            
            print(f"✅ Successfully extracted insights!")
            print(f"Brand Name: {insights.brand_name}")
            print(f"Brand Description: {insights.brand_description[:100] if insights.brand_description else 'N/A'}...")
            print(f"Total Products: {insights.total_products}")
            print(f"Hero Products: {len(insights.hero_products)}")
            print(f"Social Handles Found: {bool(insights.social_handles.instagram or insights.social_handles.facebook)}")
            print(f"Contact Emails: {len(insights.contact_details.emails)}")
            print(f"FAQs Found: {len(insights.faqs)}")
            print(f"Currencies: {insights.currencies_supported}")
            print(f"Payment Methods: {insights.payment_methods}")
            
            # Print first few products as example
            if insights.hero_products:
                print(f"\nFirst few hero products:")
                for i, product in enumerate(insights.hero_products[:3], 1):
                    print(f"  {i}. {product.name} - {product.price}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")

def test_sync_service():
    """Test the synchronous service"""
    from modules.shopify_service import ShopifyInsightsServiceSync
    
    service = ShopifyInsightsServiceSync()
    
    print("\n" + "="*60)
    print("Testing Synchronous Service")
    print("="*60)
    
    try:
        # Test with a simple URL validation
        test_url = "https://example.myshopify.com"
        print(f"Testing URL validation for: {test_url}")
        
        # This will likely fail since it's not a real store, but tests the validation
        insights = service.fetch_insights(test_url)
        print("✅ Service works!")
        
    except Exception as e:
        print(f"Expected error for test URL: {str(e)}")

if __name__ == "__main__":
    print("🚀 Shopify Insights Fetcher - Test Script")
    print("=" * 60)
    
    # Test async service
    print("Testing Async Service...")
    asyncio.run(test_shopify_service())
    
    # Test sync service
    test_sync_service()
    
    print("\n✅ Test script completed!")
    print("\n📚 To start the API server, run:")
    print("   .venv\\Scripts\\python.exe main.py")
    print("\n📖 API Documentation will be available at:")
    print("   http://localhost:8000/docs")