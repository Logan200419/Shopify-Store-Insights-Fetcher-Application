# Competitor Analysis Feature

## Overview

The Shopify Insights Fetcher now includes a comprehensive competitor analysis feature that can:

1. **Find Competitors**: Automatically discover competitors for a given brand using web search
2. **Validate Shopify Stores**: Only analyze websites that are powered by Shopify
3. **Extract Insights**: Get complete insights from competitor stores using the same extraction logic
4. **Generate Analysis**: Provide comparative analysis and summaries
5. **Store Results**: Save competitor analysis results to the database

## API Endpoints

### 1. Analyze Competitors (POST)

```
POST /competitor-analysis
Content-Type: application/json

{
    "website_url": "https://gfuel.com"
}
```

### 2. Analyze Competitors (GET)

```
GET /competitor-analysis/https://gfuel.com
```

### 3. Get Stored Competitor Analysis

```
GET /stored-competitor-analysis/https://gfuel.com
```

## How It Works

### 1. Competitor Discovery

- Extracts brand category from the original website (gaming, fitness, beauty, etc.)
- Generates targeted search queries like "gaming brands like GFUEL"
- Uses web search to find potential competitors
- Filters results to exclude non-commercial sites

### 2. Shopify Validation

- Checks each potential competitor website for Shopify indicators:
  - Shopify CDN references
  - Shopify-specific JavaScript
  - Shopify headers
  - Domain patterns

### 3. Insights Extraction

- Uses the same comprehensive extraction logic as regular insights
- Extracts all data: products, FAQs, policies, social handles, etc.
- Applies rate limiting between competitor analysis

### 4. Analysis Summary

- Calculates average products per store
- Identifies common social media platforms
- Analyzes common payment methods
- Categorizes FAQ patterns
- Provides competitive intelligence

## Response Format

```json
{
    "success": true,
    "data": {
        "original_brand": "GFUEL",
        "original_url": "https://gfuel.com",
        "competitors_found": 5,
        "competitors_analyzed": 3,
        "competitor_insights": [
            {
                "competitor_name": "Competitor Name",
                "competitor_url": "https://competitor.com",
                "insights": {
                    "brand_name": "Competitor Brand",
                    "product_catalog": [...],
                    "faqs": [...],
                    "social_handles": {...},
                    // ... full insights data
                }
            }
        ],
        "analysis_summary": {
            "total_competitors": 3,
            "avg_products_per_store": 45,
            "common_social_platforms": {
                "instagram": 3,
                "facebook": 2,
                "twitter": 1
            },
            "common_payment_methods": {
                "paypal": 3,
                "stripe": 2
            },
            "common_faq_categories": {
                "Shipping & Orders": 8,
                "Returns & Refunds": 6,
                "Product Information": 4
            }
        }
    },
    "message": "Successfully analyzed competitors for GFUEL",
    "timestamp": "2025-08-16T10:30:00"
}
```

## Database Storage

Competitor analysis results are automatically saved to the `competitor_analysis` table with:

- Original brand information
- Number of competitors found/analyzed
- Complete competitor insights (JSON)
- Analysis summary (JSON)
- Timestamps

## Usage Examples

### Python/Requests

```python
import requests

# Analyze competitors
response = requests.post("http://localhost:8000/competitor-analysis",
                        json={"website_url": "https://gfuel.com"})
analysis = response.json()

# Get stored analysis
stored = requests.get("http://localhost:8000/stored-competitor-analysis/https://gfuel.com")
```

### cURL

```bash
# Analyze competitors
curl -X POST "http://localhost:8000/competitor-analysis" \
     -H "Content-Type: application/json" \
     -d '{"website_url": "https://gfuel.com"}'

# Get stored analysis
curl "http://localhost:8000/stored-competitor-analysis/https://gfuel.com"
```

## Limitations and Considerations

1. **Shopify Only**: Only analyzes competitors that use Shopify
2. **Rate Limiting**: Includes delays to avoid overwhelming competitor sites
3. **Search Accuracy**: Competitor discovery depends on search engine results
4. **Processing Time**: Full competitor analysis can take several minutes
5. **Data Quality**: Analysis quality depends on competitor site structure

## Configuration

The competitor analyzer can be configured for:

- Maximum number of competitors to find (default: 5)
- Search query variations
- Rate limiting delays
- Shopify detection patterns

## Future Enhancements

Potential improvements:

- Support for other e-commerce platforms
- More sophisticated competitor discovery
- Competitive pricing analysis
- Market share estimation
- Trend analysis over time
