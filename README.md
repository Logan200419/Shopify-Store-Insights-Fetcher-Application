# Shopify Insights Fetcher Application

A comprehensive Python FastAPI application that extracts detailed insights from Shopify stores without using the official Shopify API. This application scrapes and organizes brand data into well-structured formats.

## Features

### Mandatory Features ✅
- **Complete Product Catalog**: Extracts all products from the store
- **Hero Products**: Products displayed on the homepage
- **Privacy Policy**: Extracts privacy policy information
- **Return & Refund Policies**: Comprehensive policy extraction
- **Brand FAQs**: Question and answer extraction
- **Social Media Handles**: Instagram, Facebook, Twitter, TikTok, YouTube, LinkedIn, Pinterest
- **Contact Details**: Email addresses, phone numbers, physical addresses
- **Brand Context**: About the brand, descriptions, and key information
- **Important Links**: Order tracking, contact us, blogs, about us, shipping info, size guides, careers

### Additional Features 🚀
- **Brand Logo**: Automatic logo detection and extraction
- **Payment Methods**: Supported payment options (Visa, PayPal, etc.)
- **Currencies**: Multi-currency support detection
- **Product Images**: High-quality product image URLs
- **Availability Status**: Real-time stock information
- **Pricing Information**: Current and original prices
- **Structured Data**: JSON-LD and microdata extraction
- **Error Handling**: Comprehensive error management with proper HTTP status codes

## Technology Stack

- **Framework**: FastAPI (Python 3.8+)
- **Web Scraping**: BeautifulSoup4, aiohttp, requests
- **Data Models**: Pydantic for data validation
- **Async Processing**: asyncio for concurrent operations
- **Documentation**: Auto-generated OpenAPI/Swagger docs
- **Logging**: Comprehensive logging system
- **Configuration**: Environment-based configuration

## Project Structure

```
shopify_insights_fetcher/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── .env.example           # Environment configuration template
├── config/
│   ├── __init__.py
│   └── settings.py        # Application configuration
├── core/
│   ├── __init__.py
│   ├── models.py          # Pydantic data models
│   └── utils.py           # Utility classes and functions
├── modules/
│   ├── __init__.py
│   ├── extractors.py      # Data extraction classes
│   └── shopify_service.py # Main service orchestrator
└── storage/               # For future database/cache implementation
```

## Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd shopify_insights_fetcher
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
```bash
# Copy the example environment file
cp .env.example .env
# Edit .env file with your preferred settings
```

### 5. Run the Application
```bash
# Development mode
python main.py

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints

#### 1. Root Endpoint
```http
GET /
```
Returns API information and available endpoints.

#### 2. Health Check
```http
GET /health
```
Returns the health status of the application.

#### 3. Fetch Insights (POST)
```http
POST /insights
Content-Type: application/json

{
    "website_url": "https://example.myshopify.com"
}
```

#### 4. Fetch Insights (GET)
```http
GET /insights/{website_url}
```
Alternative GET endpoint for easy testing in browsers.

#### 5. Async Processing
```http
POST /insights/async
Content-Type: application/json

{
    "website_url": "https://example.myshopify.com"
}
```
Returns a task ID for background processing.

### Response Format

#### Success Response
```json
{
    "success": true,
    "data": {
        "website_url": "https://example.myshopify.com",
        "brand_name": "Example Brand",
        "brand_description": "Brand description...",
        "logo_url": "https://example.com/logo.png",
        "hero_products": [...],
        "product_catalog": [...],
        "social_handles": {
            "instagram": "https://instagram.com/brand",
            "facebook": "https://facebook.com/brand"
        },
        "contact_details": {
            "emails": ["contact@brand.com"],
            "phone_numbers": ["+1234567890"]
        },
        "privacy_policy": {...},
        "return_policy": {...},
        "refund_policy": {...},
        "faqs": [...],
        "important_links": {...},
        "currencies_supported": ["USD", "EUR"],
        "payment_methods": ["Visa", "PayPal"],
        "total_products": 150,
        "scraped_at": "2024-01-01T12:00:00"
    },
    "message": "Successfully extracted insights",
    "timestamp": "2024-01-01T12:00:00"
}
```

#### Error Response
```json
{
    "error": "Error description",
    "status_code": 404,
    "message": "Website not found or not accessible",
    "timestamp": "2024-01-01T12:00:00"
}
```

### HTTP Status Codes

- **200**: Success
- **400**: Invalid URL format
- **404**: Website not found or not accessible
- **500**: Internal server error

## Testing the API

### Using Postman

1. **Import Collection**: Create a new collection in Postman
2. **Add Request**: 
   - Method: POST
   - URL: `http://localhost:8000/insights`
   - Headers: `Content-Type: application/json`
   - Body: `{"website_url": "https://example.myshopify.com"}`

### Using curl

```bash
# POST request
curl -X POST "http://localhost:8000/insights" \
     -H "Content-Type: application/json" \
     -d '{"website_url": "https://example.myshopify.com"}'

# GET request
curl "http://localhost:8000/insights/https://example.myshopify.com"
```

### Using Python requests

```python
import requests

response = requests.post(
    "http://localhost:8000/insights",
    json={"website_url": "https://example.myshopify.com"}
)

print(response.json())
```

## Interactive API Documentation

Once the application is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These provide interactive documentation where you can test the API directly from your browser.

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | Shopify Insights Fetcher | Application name |
| `DEBUG` | False | Enable debug mode |
| `HOST` | 0.0.0.0 | Server host |
| `PORT` | 8000 | Server port |
| `REQUEST_TIMEOUT` | 30 | HTTP request timeout (seconds) |
| `MAX_RETRIES` | 3 | Maximum retry attempts |
| `RATE_LIMIT_DELAY` | 1.0 | Delay between requests (seconds) |
| `LOG_LEVEL` | INFO | Logging level |

## Architecture & Design Patterns

### SOLID Principles
- **Single Responsibility**: Each extractor handles one type of data
- **Open/Closed**: Easy to extend with new extractors
- **Liskov Substitution**: Base extractor interface
- **Interface Segregation**: Focused extractor interfaces
- **Dependency Inversion**: Service depends on abstractions

### Design Patterns
- **Strategy Pattern**: Different extraction strategies
- **Factory Pattern**: Extractor creation
- **Observer Pattern**: Logging and monitoring
- **Async/Await Pattern**: Non-blocking operations

## Error Handling

The application implements comprehensive error handling:

1. **URL Validation**: Validates URL format before processing
2. **Network Errors**: Handles timeouts, connection errors
3. **Parsing Errors**: Graceful handling of malformed HTML
4. **Rate Limiting**: Prevents overwhelming target servers
5. **Retry Logic**: Automatic retry with exponential backoff

## Performance Considerations

- **Concurrent Processing**: Uses asyncio for parallel requests
- **Rate Limiting**: Configurable delays between requests
- **Connection Pooling**: Reuses HTTP connections
- **Memory Management**: Efficient BeautifulSoup parsing
- **Timeout Handling**: Prevents hanging requests

## Security Features

- **Input Validation**: Validates all input URLs
- **Rate Limiting**: Prevents abuse
- **Error Information**: Limited error disclosure
- **User Agent Rotation**: Randomized user agents
- **CORS Configuration**: Configurable CORS policies

## Logging

The application provides comprehensive logging:

- **Request Logging**: All incoming requests
- **Error Logging**: Detailed error information
- **Performance Logging**: Processing times
- **Debug Logging**: Detailed extraction process

## Future Enhancements

### Database Integration
- MySQL database for caching results
- Redis for session management
- PostgreSQL for analytics

### Advanced Features
- Machine learning for better data extraction
- Image analysis for product categorization
- Sentiment analysis for reviews
- Competitive analysis features

### Scalability
- Docker containerization
- Kubernetes deployment
- Load balancing
- Horizontal scaling

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **URL Access Issues**: Check network connectivity
3. **Parsing Failures**: Website structure may have changed
4. **Rate Limiting**: Increase delay between requests

### Debug Mode

Enable debug mode by setting `DEBUG=True` in your `.env` file for detailed logging.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
1. Check the documentation
2. Review the logs
3. Create an issue in the repository

---

**Note**: This application is designed for educational and research purposes. Please ensure you comply with the terms of service of any websites you scrape and respect robots.txt files.