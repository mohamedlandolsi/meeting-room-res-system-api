import os
import logging
import json
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# Custom JSON formatter for structured logging
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "service": "reservation-service"
        }
        
        # Add exception info if available
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        # Add any extra attributes
        for key, value in record.__dict__.items():
            if key not in ("timestamp", "level", "message", "logger", "service") and not key.startswith("_"):
                if not isinstance(value, (str, int, float, bool, type(None))):
                    value = str(value)
                log_record[key] = value
                
        return json.dumps(log_record)

class Config:
    # Configure logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Database configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/reservation_db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')  # Must be same as user-service
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    
    # Kafka Configuration
    KAFKA_BROKER_URL = os.getenv('KAFKA_BROKER_URL', 'localhost:9092')
    KAFKA_CONSUMER_GROUP = os.getenv('KAFKA_CONSUMER_GROUP', 'reservation-service')
    
    # Application Configuration
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    @staticmethod
    def configure_logging(app):
        """Configure structured logging for the application"""
        # Remove default handlers
        for handler in app.logger.handlers:
            app.logger.removeHandler(handler)
            
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(JsonFormatter())
        
        # Set log level
        app.logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # Add handler to app logger
        app.logger.addHandler(console_handler)
        
        # Also configure root logger for imported modules
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL),
            handlers=[console_handler]
        )