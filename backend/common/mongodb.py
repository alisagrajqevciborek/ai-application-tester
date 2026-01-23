"""
MongoDB connection utility using pymongo.
This module provides a connection to MongoDB for direct database operations.
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Global MongoDB client and database instances
_mongo_client = None
_mongo_db = None


def get_mongo_client():
    """
    Get or create MongoDB client connection.
    Returns MongoClient instance.
    """
    global _mongo_client
    
    if _mongo_client is None:
        try:
            host = getattr(settings, 'MONGODB_HOST', 'localhost')
            port = getattr(settings, 'MONGODB_PORT', 27017)
            
            _mongo_client = MongoClient(
                host=host,
                port=port,
                serverSelectionTimeoutMS=5000  # 5 second timeout
            )
            
            # Test connection
            _mongo_client.admin.command('ping')
            logger.info(f"Connected to MongoDB at {host}:{port}")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    return _mongo_client


def get_mongo_db():
    """
    Get MongoDB database instance.
    Returns Database instance.
    """
    global _mongo_db
    
    if _mongo_db is None:
        client = get_mongo_client()
        db_name = getattr(settings, 'MONGODB_DB_NAME', 'ai_app_tester')
        _mongo_db = client[db_name]
        logger.info(f"Using MongoDB database: {db_name}")
    
    return _mongo_db


def get_collection(collection_name):
    """
    Get a MongoDB collection.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        Collection instance
    """
    db = get_mongo_db()
    return db[collection_name]


def close_mongo_connection():
    """
    Close MongoDB connection.
    """
    global _mongo_client, _mongo_db
    
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        _mongo_db = None
        logger.info("MongoDB connection closed")


