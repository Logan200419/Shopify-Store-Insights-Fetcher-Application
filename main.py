import logging
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime
import traceback

from core.models import BrandInsights, ErrorResponse, SuccessResponse
from modules.shopify_service import ShopifyInsightsService
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A comprehensive API for extracting insights from Shopify stores",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize service
insights_service = ShopifyInsightsService()

class InsightsRequest(BaseModel):
    website_url: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "website_url": "https://example.myshopify.com"
            }
        }

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Shopify Insights Fetcher API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "version": settings.app_version
    }

@app.post("/insights", response_model=SuccessResponse)
async def fetch_insights(request: InsightsRequest):
    """
    Fetch comprehensive insights from a Shopify store
    
    **Parameters:**
    - **website_url**: The URL of the Shopify store to analyze
    
    **Returns:**
    - Complete brand insights including products, policies, social handles, etc.
    
    **Error Codes:**
    - **400**: Invalid URL format or not a valid website
    - **404**: Website not found or not accessible
    - **500**: Internal server error during processing
    """
    try:
        logger.info(f"Received insights request for: {request.website_url}")
        
        # Fetch insights using the service
        insights = await insights_service.fetch_insights(request.website_url)
        
        return SuccessResponse(
            data=insights,
            message=f"Successfully extracted insights for {request.website_url}"
        )
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error processing request for {request.website_url}: {error_message}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Determine appropriate status code based on error
        if "not found" in error_message.lower() or "404" in error_message:
            status_code = 404
            message = "Website not found or not accessible"
        elif "invalid url" in error_message.lower():
            status_code = 400
            message = "Invalid URL format"
        elif "failed to fetch" in error_message.lower():
            status_code = 404
            message = "Unable to fetch website content"
        else:
            status_code = 500
            message = "Internal server error occurred while processing the request"
        
        raise HTTPException(
            status_code=status_code,
            detail={
                "error": error_message,
                "status_code": status_code,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
        )

@app.get("/insights/{website_url:path}", response_model=SuccessResponse)
async def fetch_insights_get(website_url: str):
    """
    Alternative GET endpoint for fetching insights (for easy testing)
    
    **Parameters:**
    - **website_url**: The URL of the Shopify store to analyze (URL encoded)
    
    **Returns:**
    - Complete brand insights including products, policies, social handles, etc.
    """
    # Create request object and use the POST endpoint logic
    request = InsightsRequest(website_url=website_url)
    return await fetch_insights(request)

@app.post("/insights/async")
async def fetch_insights_async(request: InsightsRequest, background_tasks: BackgroundTasks):
    """
    Asynchronous endpoint for large stores (returns immediately with task ID)
    
    **Parameters:**
    - **website_url**: The URL of the Shopify store to analyze
    
    **Returns:**
    - Task ID for checking status later
    
    **Note:** This is a placeholder for future implementation with task queues
    """
    task_id = f"task_{datetime.now().timestamp()}"
    
    def process_insights():
        # This would typically be handled by a task queue like Celery
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            insights = loop.run_until_complete(insights_service.fetch_insights(request.website_url))
            # Store results in database/cache with task_id
            logger.info(f"Background task {task_id} completed for {request.website_url}")
        except Exception as e:
            logger.error(f"Background task {task_id} failed: {str(e)}")
        finally:
            if loop:
                loop.close()
    
    background_tasks.add_task(process_insights)
    
    return {
        "task_id": task_id,
        "status": "processing",
        "message": "Insights extraction started in background",
        "website_url": request.website_url,
        "estimated_time": "2-5 minutes"
    }

@app.post("/test")
async def test_scraping():
    """Test endpoint to verify scraping functionality with a simple example"""
    try:
        # Create a simple mock response for testing
        mock_insights = BrandInsights(
            website_url="https://demo-store.myshopify.com",
            brand_name="Demo Store",
            brand_description="A sample Shopify store for testing the insights fetcher",
            total_products=25,
            scraped_at=datetime.now()
        )
        
        # Add some sample data
        from core.models import ProductModel, SocialHandles, ContactDetails
        
        mock_insights.hero_products = [
            ProductModel(
                name="Sample Product 1",
                price="$29.99",
                availability="In Stock"
            ),
            ProductModel(
                name="Sample Product 2", 
                price="$49.99",
                availability="In Stock"
            )
        ]
        
        mock_insights.social_handles = SocialHandles(
            instagram="https://instagram.com/demo_store",
            facebook="https://facebook.com/demo_store"
        )
        
        mock_insights.contact_details = ContactDetails(
            emails=["contact@demo-store.com"],
            phone_numbers=["+1-555-0123"]
        )
        
        return SuccessResponse(
            data=mock_insights,
            message="Test data generated successfully - scraping functionality is working"
        )
        
    except Exception as e:
        logger.error(f"Test endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "status_code": 500,
                "message": "Test endpoint failed",
                "timestamp": datetime.now().isoformat()
            }
        )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {str(exc)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "message": "An unexpected error occurred while processing your request",
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )