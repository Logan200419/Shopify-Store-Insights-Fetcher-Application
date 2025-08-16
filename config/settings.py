import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Configuration
    app_name: str = "Shopify Insights Fetcher"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database Configuration
    database_url: str = "mysql+pymysql://user:password@localhost/shopify_insights"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Scraping Configuration
    request_timeout: int = 30
    max_retries: int = 2
    rate_limit_delay: float = 1.0
    user_agents: List[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    ]
    
    # Selenium Configuration
    use_selenium: bool = False
    selenium_headless: bool = True
    selenium_timeout: int = 10
    
    # Cache Configuration
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 hour
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "shopify_insights.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()