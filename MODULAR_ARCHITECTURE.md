# Modular Extractor Architecture

## Overview

The Shopify Insights Fetcher application has been restructured to use a modular extractor architecture, separating different types of data extraction into specialized modules for better maintainability and extensibility.

## New Module Structure

### 1. `modules/base_extractor.py`

**Purpose**: Common functionality and base class for all extractors

**Key Components**:

- `BaseExtractor` - Abstract base class with common functionality
- Helper functions: `safe_get_attr()`, `safe_get_text()`, `safe_find()`, `safe_find_all()`
- Common methods: `_clean_text()`, `_resolve_url()`, `_extract_json_ld()`

### 2. `modules/product_extractor.py`

**Purpose**: Product catalog and individual product extraction

**Key Classes**:

- `ProductExtractor` - General product extraction from any page
- `ProductCatalogExtractor` - Specialized for product catalog pages with limits
- `SingleProductExtractor` - Specialized for individual product pages

**Extraction Methods**:

- JSON-LD structured data parsing
- Product grid and list layouts
- Shopify section-based layouts
- Collection pages
- Product deduplication

### 3. `modules/hero_product_extractor.py`

**Purpose**: Featured/hero products from homepage and landing pages

**Key Features**:

- Hero section detection
- Featured product sections
- Promotional banners
- Product carousels/sliders
- Homepage collection showcases
- Product prioritization and scoring

### 4. `modules/privacy_policy_extractor.py`

**Purpose**: Privacy policies and legal documents

**Extraction Types**:

- Privacy policies
- Terms of service
- Cookie policies
- Data protection policies (GDPR/CCPA)
- Refund and return policies
- Shipping policies

**Key Classes**:

- `PrivacyPolicyExtractor` - Finds and extracts policy links
- `PolicyDetailExtractor` - Extracts detailed content from policy pages

### 5. `modules/extractors.py` (Unchanged)

**Purpose**: Other specialized extractors

**Contains**:

- `SocialMediaExtractor`
- `ContactExtractor`
- `FAQExtractor`
- `ImportantLinksExtractor`
- `BrandExtractor`

## Usage Examples

### Using the New Product Extractors

```python
from modules.product_extractor import ProductExtractor, ProductCatalogExtractor
from modules.hero_product_extractor import HeroProductExtractor

# Extract all products from a page
extractor = ProductExtractor(soup, base_url)
products = extractor.extract()

# Extract limited product catalog
catalog_extractor = ProductCatalogExtractor(soup, base_url, max_products=50)
catalog_products = catalog_extractor.extract()

# Extract hero products from homepage
hero_extractor = HeroProductExtractor(soup, base_url)
hero_products = hero_extractor.extract()
```

### Using the Privacy Policy Extractor

```python
from modules.privacy_policy_extractor import PrivacyPolicyExtractor

# Extract all policies from a page
policy_extractor = PrivacyPolicyExtractor(soup, base_url)
policies = policy_extractor.extract()

# Policies are automatically categorized by type
for policy in policies:
    print(f"Policy: {policy.title}")
    print(f"URL: {policy.url}")
    print(f"Content: {policy.content[:100]}...")
```

## Benefits of the New Architecture

### 1. **Separation of Concerns**

- Each extractor focuses on a specific type of data
- Easier to maintain and debug individual extractors
- Clear responsibility boundaries

### 2. **Improved Modularity**

- Extractors can be developed and tested independently
- Easy to add new extraction types
- Better code reusability

### 3. **Enhanced Specialization**

- Hero product extraction optimized for homepage layouts
- Privacy policy extraction handles various legal document types
- Product catalog extraction can handle large product sets efficiently

### 4. **Better Performance**

- Specialized extractors can optimize for their specific use cases
- Reduced redundant processing
- Configurable limits and priorities

### 5. **Easier Testing**

- Each extractor can be unit tested independently
- Mock data can be created for specific extractor types
- Better isolation of test failures

## Migration Notes

### Updated ShopifyInsightsService

The main service has been updated to use the new extractors:

```python
# Old approach
product_extractor = ProductExtractor(soup, normalized_url)
insights.hero_products = product_extractor.extract()

# New approach
hero_extractor = HeroProductExtractor(soup, normalized_url)
insights.hero_products = hero_extractor.extract()
```

### Imports

The new modules are available through the updated `modules/__init__.py`:

```python
from modules import (
    ProductExtractor,
    ProductCatalogExtractor,
    HeroProductExtractor,
    PrivacyPolicyExtractor
)
```

## Future Enhancements

The modular architecture makes it easy to add new specialized extractors:

1. **Review Extractor** - Extract customer reviews and ratings
2. **SEO Extractor** - Extract meta tags, structured data, and SEO elements
3. **Analytics Extractor** - Extract tracking codes and analytics information
4. **Performance Extractor** - Extract page load metrics and performance data

## Testing

All new extractors have been tested and verified to work correctly. The test script `test_modular_extractors.py` can be used to verify the functionality of all extractors.

Run the test with:

```bash
python test_modular_extractors.py
```
