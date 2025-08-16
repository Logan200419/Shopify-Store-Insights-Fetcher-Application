# Competitor Analysis API Response Integration

## ✅ **Competitor Analysis is now fully integrated into API responses!**

### **Available Endpoints:**

#### 1. **Regular Insights with Optional Competitor Analysis**

```bash
POST /insights
Content-Type: application/json

{
    "website_url": "https://gfuel.com",
    "include_competitor_analysis": true
}
```

**Response includes:**

- All regular insights (products, FAQs, policies, etc.)
- PLUS competitor analysis data when `include_competitor_analysis: true`

#### 2. **Dedicated Competitor Analysis**

```bash
POST /competitor-analysis
Content-Type: application/json

{
    "website_url": "https://gfuel.com"
}
```

**Response includes:**

- Complete competitor analysis
- List of competitors found
- Detailed insights from each competitor's Shopify store

#### 3. **Comprehensive Analysis (Everything)**

```bash
POST /comprehensive-analysis
Content-Type: application/json

{
    "website_url": "https://gfuel.com"
}
```

**Response includes:**

- All brand insights
- Complete competitor analysis
- Everything in one API call

#### 4. **Retrieve Stored Analysis**

```bash
GET /stored-competitor-analysis/{website_url}
```

**Response includes:**

- Previously stored competitor analysis results
- Avoids re-running analysis for the same brand

### **Response Structure:**

#### With Competitor Analysis Included:

```json
{
    "success": true,
    "data": {
        "website_url": "https://gfuel.com",
        "brand_name": "G FUEL",
        "brand_description": "...",
        "product_catalog": [...],
        "hero_products": [...],
        "social_handles": {...},
        "contact_details": {...},
        "privacy_policy": {...},
        "return_policy": {...},
        "refund_policy": {...},
        "faqs": [...],
        "important_links": {...},
        "competitor_analysis": {
            "original_brand": "G FUEL",
            "original_url": "https://gfuel.com",
            "competitors_found": 5,
            "competitors_analyzed": 3,
            "competitor_insights": [
                {
                    "brand_name": "Competitor 1",
                    "website_url": "https://competitor1.com",
                    "is_shopify": true,
                    "analysis_status": "success",
                    "insights": {
                        "brand_name": "...",
                        "product_catalog": [...],
                        "faqs": [...],
                        // ... all insights data
                    }
                }
            ],
            "analysis_summary": {
                "total_competitors": 5,
                "shopify_competitors": 3,
                "successful_analyses": 2,
                "comparison_metrics": {...}
            }
        }
    },
    "message": "Successfully extracted insights for https://gfuel.com",
    "timestamp": "2025-08-16T10:30:00Z"
}
```

### **Database Storage:**

Both insights and competitor analysis are automatically saved to your MySQL database:

- **`store`** table: Regular insights data
- **`competitor_analysis`** table: Competitor analysis results

### **Key Features:**

1. **Smart Caching**: Checks for existing competitor analysis before running new analysis
2. **Error Handling**: Graceful fallback if competitor analysis fails
3. **Shopify Detection**: Only analyzes competitors that use Shopify
4. **Complete Integration**: Works with existing insights extraction
5. **Database Persistence**: All results stored for future retrieval

### **Usage Tips:**

- Use `include_competitor_analysis: false` for faster regular insights
- Use `include_competitor_analysis: true` for complete analysis
- Use `/comprehensive-analysis` for the most complete data
- Use stored analysis endpoints to retrieve previous results quickly

The competitor analysis is now fully integrated and will be included in your application responses based on the endpoint and parameters you choose!
