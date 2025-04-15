from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from models import db, Reservation
from routes import reservations_bp, availability_bp
import os
import threading
import json
from kafka import KafkaConsumer

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('config.Config')
    
    # Initialize extensions
    db.init_app(app)
    jwt = JWTManager(app)
    
    # Register blueprints
    app.register_blueprint(reservations_bp)
    app.register_blueprint(availability_bp)
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad Request", "message": str(error)}), 400
        
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({"error": "Unauthorized", "message": str(error)}), 401
        
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({"error": "Forbidden", "message": str(error)}), 403
        
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not Found", "message": str(error)}), 404
        
    @app.errorhandler(409)
    def conflict(error):
        return jsonify({"error": "Conflict", "message": str(error)}), 409
        
    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": "Internal Server Error", "message": str(error)}), 500
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app

def start_kafka_consumer(app):
    """Start Kafka consumer in a separate thread"""
    def consume_room_events():
        with app.app_context():
            try:
                consumer = KafkaConsumer(
                    'room_events',
                    bootstrap_servers=app.config['KAFKA_BROKER_URL'],
                    group_id=app.config['KAFKA_CONSUMER_GROUP'],
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    auto_offset_reset='earliest',
                    enable_auto_commit=True
                )
                
                print("Kafka consumer started. Listening for room events...")
                
                for message in consumer:
                    event = message.value
                    event_type = event.get('event_type')
                    
                    if event_type == 'room_deleted':
                        room_id = event.get('room_id')
                        if room_id:
                            # Delete all reservations associated with the deleted room
                            reservations = Reservation.query.filter_by(room_id=room_id).all()
                            if reservations:
                                print(f"Deleting {len(reservations)} reservations for room_id {room_id}")
                                for reservation in reservations:
                                    db.session.delete(reservation)
                                db.session.commit()
            except Exception as e:
                print(f"Error in Kafka consumer: {str(e)}")
    
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