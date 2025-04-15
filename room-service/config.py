import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/room_db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')  # Must be same as user-service
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    
    # Kafka Configuration
    KAFKA_BROKER_URL = os.getenv('KAFKA_BROKER_URL', 'localhost:9092')
    
    # Application Configuration
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'