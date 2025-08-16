from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

class ProductModel(BaseModel):
    name: str
    price: Optional[str] = None
    original_price: Optional[str] = None
    currency: Optional[str] = None
    availability: Optional[str] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    description: Optional[str] = None
    variants: Optional[List[str]] = []
    tags: Optional[List[str]] = []

class SocialHandles(BaseModel):
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    twitter: Optional[str] = None
    tiktok: Optional[str] = None
    youtube: Optional[str] = None
    linkedin: Optional[str] = None
    pinterest: Optional[str] = None

class ContactDetails(BaseModel):
    emails: List[str] = []
    phone_numbers: List[str] = []
    address: Optional[str] = None
    contact_form_url: Optional[str] = None

class PolicyModel(BaseModel):
    title: str
    content: str
    url: Optional[str] = None

class FAQModel(BaseModel):
    question: str
    answer: str
    category: Optional[str] = "General"

class ImportantLinks(BaseModel):
    order_tracking: Optional[str] = None
    contact_us: Optional[str] = None
    blogs: Optional[str] = None
    about_us: Optional[str] = None
    shipping_info: Optional[str] = None
    size_guide: Optional[str] = None
    careers: Optional[str] = None

class BrandInsights(BaseModel):
    website_url: str
    brand_name: Optional[str] = None
    brand_description: Optional[str] = None
    logo_url: Optional[str] = None
    hero_products: List[ProductModel] = []
    product_catalog: List[ProductModel] = []
    social_handles: SocialHandles = SocialHandles()
    contact_details: ContactDetails = ContactDetails()
    privacy_policy: Optional[PolicyModel] = None
    return_policy: Optional[PolicyModel] = None
    refund_policy: Optional[PolicyModel] = None
    terms_of_service: Optional[PolicyModel] = None
    faqs: List[FAQModel] = []
    important_links: ImportantLinks = ImportantLinks()
    currencies_supported: List[str] = []
    payment_methods: List[str] = []
    shipping_countries: List[str] = []
    total_products: int = 0
    scraped_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
class ErrorResponse(BaseModel):
    error: str
    status_code: int
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SuccessResponse(BaseModel):
    success: bool = True
    data: BrandInsights
    message: str = "Successfully fetched brand insights"
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class CompetitorAnalysisResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]
    message: str = "Successfully completed competitor analysis"
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }