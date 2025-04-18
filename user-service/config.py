import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/user_db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_IDENTITY_CLAIM = 'sub'  # This is the default, but explicitly set for clarity
    JWT_JSON_KEY = 'access_token'
    JWT_ERROR_MESSAGE_KEY = 'error'
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
    
    # Admin configuration - add your email here
    ADMIN_EMAILS = os.getenv('ADMIN_EMAILS', '').split(',')
    
    # Application Configuration
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'