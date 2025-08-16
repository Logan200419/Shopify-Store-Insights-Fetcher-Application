from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging
import json
from config.settings import Settings

logger = logging.getLogger(__name__)

Base = declarative_base()

class Store(Base):
    __tablename__ = 'store'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    website_url = Column(Text, nullable=False, unique=True)
    brand_name = Column(Text)
    brand_description = Column(Text)
    logo_url = Column(Text)
    hero_products = Column(Text)  # Store as JSON string
    product_catalog = Column(Text)  # Store as JSON string
    social_handles = Column(Text)  # Store as JSON string
    contact_details = Column(Text)  # Store as JSON string
    privacy_policy = Column(Text)  # Store as JSON string
    return_policy = Column(Text)  # Store as JSON string
    refund_policy = Column(Text)  # Store as JSON string
    faqs = Column(Text)  # Store as JSON string
    important_links = Column(Text)  # Store as JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CompetitorAnalysis(Base):
    __tablename__ = 'competitor_analysis'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_brand = Column(Text, nullable=False)
    original_url = Column(Text, nullable=False)
    competitors_found = Column(Integer, default=0)
    competitors_analyzed = Column(Integer, default=0)
    competitor_insights = Column(Text)  # JSON string
    analysis_summary = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DatabaseManager:
    """Database manager for Shopify Insights Fetcher"""
    
    def __init__(self):
        self.settings = Settings()
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database connection and create tables"""
        try:
            self.engine = create_engine(
                self.settings.database_url,
                pool_size=self.settings.database_pool_size,
                max_overflow=self.settings.database_max_overflow,
                echo=False  # Set to True for SQL debugging
            )
            
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            
            # Create session factory
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def get_session(self):
        """Get database session"""
        if self.SessionLocal is None:
            raise RuntimeError("Database not initialized")
        return self.SessionLocal()
    
    def save_store_insights(self, insights_data: Dict[str, Any]) -> Optional[int]:
        """Save complete store insights to database"""
        session = self.get_session()
        try:
            # Create or update store record
            store = session.query(Store).filter_by(website_url=insights_data['website_url']).first()
            
            if store:
                # Update existing store
                if 'brand_name' in insights_data:
                    store.brand_name = insights_data['brand_name']  # type: ignore
                if 'brand_description' in insights_data:
                    store.brand_description = insights_data['brand_description']  # type: ignore
                if 'logo_url' in insights_data:
                    store.logo_url = insights_data['logo_url']  # type: ignore
                if 'hero_products' in insights_data:
                    store.hero_products = json.dumps(insights_data['hero_products']) if insights_data['hero_products'] else None  # type: ignore
                if 'product_catalog' in insights_data:
                    store.product_catalog = json.dumps(insights_data['product_catalog']) if insights_data['product_catalog'] else None  # type: ignore
                if 'social_handles' in insights_data:
                    store.social_handles = json.dumps(insights_data['social_handles']) if insights_data['social_handles'] else None  # type: ignore
                if 'contact_details' in insights_data:
                    store.contact_details = json.dumps(insights_data['contact_details']) if insights_data['contact_details'] else None  # type: ignore
                if 'privacy_policy' in insights_data:
                    store.privacy_policy = json.dumps(insights_data['privacy_policy']) if insights_data['privacy_policy'] else None  # type: ignore
                if 'return_policy' in insights_data:
                    store.return_policy = json.dumps(insights_data['return_policy']) if insights_data['return_policy'] else None  # type: ignore
                if 'refund_policy' in insights_data:
                    store.refund_policy = json.dumps(insights_data['refund_policy']) if insights_data['refund_policy'] else None  # type: ignore
                if 'faqs' in insights_data:
                    store.faqs = json.dumps(insights_data['faqs']) if insights_data['faqs'] else None  # type: ignore
                if 'important_links' in insights_data:
                    store.important_links = json.dumps(insights_data['important_links']) if insights_data['important_links'] else None  # type: ignore
                
                store.updated_at = datetime.utcnow()  # type: ignore
            else:
                # Create new store
                store = Store(
                    website_url=insights_data['website_url'],
                    brand_name=insights_data.get('brand_name'),
                    brand_description=insights_data.get('brand_description'),
                    logo_url=insights_data.get('logo_url'),
                    hero_products=json.dumps(insights_data.get('hero_products', [])) if insights_data.get('hero_products') else None,
                    product_catalog=json.dumps(insights_data.get('product_catalog', [])) if insights_data.get('product_catalog') else None,
                    social_handles=json.dumps(insights_data.get('social_handles', {})) if insights_data.get('social_handles') else None,
                    contact_details=json.dumps(insights_data.get('contact_details', {})) if insights_data.get('contact_details') else None,
                    privacy_policy=json.dumps(insights_data.get('privacy_policy', {})) if insights_data.get('privacy_policy') else None,
                    return_policy=json.dumps(insights_data.get('return_policy', {})) if insights_data.get('return_policy') else None,
                    refund_policy=json.dumps(insights_data.get('refund_policy', {})) if insights_data.get('refund_policy') else None,
                    faqs=json.dumps(insights_data.get('faqs', [])) if insights_data.get('faqs') else None,
                    important_links=json.dumps(insights_data.get('important_links', [])) if insights_data.get('important_links') else None
                )
                session.add(store)
            
            session.commit()
            session.refresh(store)
            store_id = store.id  # type: ignore
            
            logger.info(f"Successfully saved insights for store ID: {store_id}")
            return store_id  # type: ignore
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save store insights: {e}")
            raise
        finally:
            session.close()
    
    def get_store_insights(self, website_url: str) -> Optional[Dict[str, Any]]:
        """Retrieve store insights from database"""
        session = self.get_session()
        try:
            store = session.query(Store).filter_by(website_url=website_url).first()
            if not store:
                return None
            
            # Build response
            insights = {
                'store_id': store.id,  # type: ignore
                'website_url': store.website_url,  # type: ignore
                'brand_name': store.brand_name,  # type: ignore
                'brand_description': store.brand_description,  # type: ignore
                'logo_url': store.logo_url,  # type: ignore
                'hero_products': json.loads(store.hero_products) if store.hero_products else [],  # type: ignore
                'product_catalog': json.loads(store.product_catalog) if store.product_catalog else [],  # type: ignore
                'social_handles': json.loads(store.social_handles) if store.social_handles else {},  # type: ignore
                'contact_details': json.loads(store.contact_details) if store.contact_details else {},  # type: ignore
                'privacy_policy': json.loads(store.privacy_policy) if store.privacy_policy else {},  # type: ignore
                'return_policy': json.loads(store.return_policy) if store.return_policy else {},  # type: ignore
                'refund_policy': json.loads(store.refund_policy) if store.refund_policy else {},  # type: ignore
                'faqs': json.loads(store.faqs) if store.faqs else [],  # type: ignore
                'important_links': json.loads(store.important_links) if store.important_links else [],  # type: ignore
                'created_at': store.created_at.isoformat() if store.created_at else None,  # type: ignore
                'updated_at': store.updated_at.isoformat() if store.updated_at else None  # type: ignore
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to retrieve store insights: {e}")
            return None
        finally:
            session.close()
    
    def list_all_stores(self) -> List[Dict[str, Any]]:
        """List all stores with basic information"""
        session = self.get_session()
        try:
            stores = session.query(Store).all()
            
            stores_list = []
            for store in stores:
                stores_list.append({
                    'id': store.id,  # type: ignore
                    'website_url': store.website_url,  # type: ignore
                    'brand_name': store.brand_name,  # type: ignore
                    'created_at': store.created_at.isoformat() if store.created_at else None,  # type: ignore
                    'updated_at': store.updated_at.isoformat() if store.updated_at else None  # type: ignore
                })
            
            return stores_list
            
        except Exception as e:
            logger.error(f"Failed to list stores: {e}")
            return []
        finally:
            session.close()
    
    def delete_store_insights(self, website_url: str) -> bool:
        """Delete all insights for a specific store"""
        session = self.get_session()
        try:
            store = session.query(Store).filter_by(website_url=website_url).first()
            
            if not store:
                return False
            
            # Delete the store
            session.delete(store)
            session.commit()
            
            logger.info(f"Successfully deleted insights for {website_url}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete store insights: {e}")
            return False
        finally:
            session.close()

    def save_competitor_analysis(self, analysis_data: Dict[str, Any]) -> Optional[int]:
        """Save competitor analysis results to database"""
        session = self.get_session()
        try:
            analysis = CompetitorAnalysis(
                original_brand=analysis_data.get('original_brand', ''),
                original_url=analysis_data.get('original_url', ''),
                competitors_found=analysis_data.get('competitors_found', 0),
                competitors_analyzed=analysis_data.get('competitors_analyzed', 0),
                competitor_insights=json.dumps(analysis_data.get('competitor_insights', [])),
                analysis_summary=json.dumps(analysis_data.get('analysis_summary', {}))
            )
            
            session.add(analysis)
            session.commit()
            session.refresh(analysis)
            
            analysis_id = analysis.id  # type: ignore
            logger.info(f"Successfully saved competitor analysis with ID: {analysis_id}")
            return analysis_id  # type: ignore
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save competitor analysis: {e}")
            raise
        finally:
            session.close()

    def get_competitor_analysis(self, original_url: str) -> Optional[Dict[str, Any]]:
        """Retrieve competitor analysis from database"""
        session = self.get_session()
        try:
            analysis = session.query(CompetitorAnalysis).filter_by(original_url=original_url).first()
            if not analysis:
                return None
            
            result = {
                'id': analysis.id,  # type: ignore
                'original_brand': analysis.original_brand,  # type: ignore
                'original_url': analysis.original_url,  # type: ignore
                'competitors_found': analysis.competitors_found,  # type: ignore
                'competitors_analyzed': analysis.competitors_analyzed,  # type: ignore
                'competitor_insights': json.loads(analysis.competitor_insights) if analysis.competitor_insights else [],  # type: ignore
                'analysis_summary': json.loads(analysis.analysis_summary) if analysis.analysis_summary else {},  # type: ignore
                'created_at': analysis.created_at.isoformat() if analysis.created_at else None,  # type: ignore
                'updated_at': analysis.updated_at.isoformat() if analysis.updated_at else None  # type: ignore
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to retrieve competitor analysis: {e}")
            return None
        finally:
            session.close()

# Global database manager instance
db_manager = DatabaseManager()
