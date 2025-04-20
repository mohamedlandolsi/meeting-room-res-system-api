from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from models import db, Reservation
from routes import reservations_bp, availability_bp
import os
import threading
import json
import time
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

def create_app():
    app = Flask(__name__)
    
    # Add this line to disable strict slashes globally
    app.url_map.strict_slashes = False
    
    # Load configuration
    app.config.from_object('config.Config')
    
    # Configure logging
    from config import Config
    Config.configure_logging(app)
    
    # Initialize extensions
    db.init_app(app)
    jwt = JWTManager(app)
    
    # Register blueprints
    app.register_blueprint(reservations_bp)
    app.register_blueprint(availability_bp)
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        app.logger.warning(f"Bad request: {error}", extra={"error_type": "client_error"})
        return jsonify({"error": "Bad Request", "message": str(error)}), 400
        
    @app.errorhandler(401)
    def unauthorized(error):
        app.logger.warning(f"Unauthorized: {error}", extra={"error_type": "auth_error"})
        return jsonify({"error": "Unauthorized", "message": str(error)}), 401
        
    @app.errorhandler(403)
    def forbidden(error):
        app.logger.warning(f"Forbidden: {error}", extra={"error_type": "auth_error"})
        return jsonify({"error": "Forbidden", "message": str(error)}), 403
        
    @app.errorhandler(404)
    def not_found(error):
        app.logger.warning(f"Not found: {error}", extra={"error_type": "client_error"})
        return jsonify({"error": "Not Found", "message": str(error)}), 404
        
    @app.errorhandler(409)
    def conflict(error):
        app.logger.warning(f"Conflict: {error}", extra={"error_type": "client_error"})
        return jsonify({"error": "Conflict", "message": str(error)}), 409
        
    @app.errorhandler(500)
    def server_error(error):
        app.logger.error(f"Server error: {error}", extra={"error_type": "server_error"})
        return jsonify({"error": "Internal Server Error", "message": str(error)}), 500
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    app.logger.info("Reservation service initialized", extra={"event": "service_startup"})
    return app

def start_kafka_consumer(app):
    """Start Kafka consumer in a separate thread with retry mechanism"""
    def consume_room_events():
        with app.app_context():
            retry_count = 0
            max_retries = 5
            retry_delay = 5  # seconds
            logger = app.logger

            while True:
                try:
                    consumer = KafkaConsumer(
                        'room_events',
                        bootstrap_servers=app.config['KAFKA_BROKER_URL'],
                        group_id=app.config['KAFKA_CONSUMER_GROUP'],
                        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                        auto_offset_reset='earliest',
                        enable_auto_commit=True
                    )
                    
                    logger.info("Kafka consumer started", extra={
                        "event": "kafka_consumer_started",
                        "broker": app.config['KAFKA_BROKER_URL'],
                        "group_id": app.config['KAFKA_CONSUMER_GROUP']
                    })
                    retry_count = 0  # Reset retry count on successful connection
                    
                    for message in consumer:
                        event = message.value
                        event_type = event.get('event_type')
                        
                        logger.info(f"Received Kafka event", extra={
                            "event": "kafka_message_received",
                            "event_type": event_type,
                            "topic": message.topic,
                            "partition": message.partition,
                            "offset": message.offset
                        })
                        
                        if event_type == 'room_deleted':
                            room_id = event.get('room_id')
                            if room_id:
                                # Delete all reservations associated with the deleted room
                                reservations = Reservation.query.filter_by(room_id=room_id).all()
                                if reservations:
                                    logger.info(f"Deleting reservations for room_id {room_id}", extra={
                                        "event": "room_deleted_cascade",
                                        "room_id": room_id,
                                        "reservations_count": len(reservations)
                                    })
                                    for reservation in reservations:
                                        db.session.delete(reservation)
                                    db.session.commit()
                
                except NoBrokersAvailable:
                    retry_count += 1
                    if retry_count > max_retries:
                        logger.error("Failed to connect to Kafka after multiple attempts", extra={
                            "event": "kafka_connection_failed",
                            "broker": app.config['KAFKA_BROKER_URL'],
                            "retry_count": retry_count
                        })
                        # Lower the retry frequency after max_retries to reduce log noise
                        time.sleep(60)  # Wait longer between retries after max_retries
                    else:
                        logger.warning(f"Kafka broker not available. Retrying in {retry_delay} seconds", extra={
                            "event": "kafka_connection_retry",
                            "retry_count": retry_count,
                            "max_retries": max_retries
                        })
                        time.sleep(retry_delay)
                
                except Exception as e:
                    logger.error(f"Error in Kafka consumer: {str(e)}", extra={
                        "event": "kafka_consumer_error",
                        "error": str(e)
                    })
                    time.sleep(retry_delay)
    
    # Start consumer in a separate thread
    consumer_thread = threading.Thread(target=consume_room_events, daemon=True)
    consumer_thread.start()
    return consumer_thread

if __name__ == '__main__':
    app = create_app()
    
    # Start Kafka consumer
    consumer_thread = start_kafka_consumer(app)
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5002)), debug=app.config['DEBUG'])