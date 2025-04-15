from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
import json
from kafka import KafkaProducer
from models import db, Room
from functools import wraps

# Create blueprint
rooms_bp = Blueprint('rooms', __name__, url_prefix='/rooms')

# Kafka producer
def get_kafka_producer():
    from flask import current_app
    return KafkaProducer(
        bootstrap_servers=current_app.config['KAFKA_BROKER_URL'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

# Custom decorator for admin role check
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        jwt_data = get_jwt()
        if jwt_data.get('role') != 'Admin':
            return jsonify({"error": "Admin privileges required"}), 403
        return fn(*args, **kwargs)
    return wrapper

@rooms_bp.route('/', methods=['POST'])
@jwt_required()
@admin_required
def create_room():
    """Create a new room (Admin only)"""
    data = request.json
    
    # Validate input
    if not data or 'name' not in data or 'capacity' not in data:
        return jsonify({"error": "Missing required fields: name, capacity"}), 400
        
    # Check if room with the same name already exists
    existing_room = Room.query.filter_by(name=data['name']).first()
    if existing_room:
        return jsonify({"error": f"Room with name '{data['name']}' already exists"}), 409
    
    # Create new room
    new_room = Room(
        name=data['name'],
        capacity=data['capacity'],
        equipment=data.get('equipment')
    )
    
    db.session.add(new_room)
    db.session.commit()
    
    # Produce kafka event
    try:
        producer = get_kafka_producer()
        producer.send(
            'room_events',
            {"event_type": "room_created", "room": new_room.to_dict()}
        )
    except Exception as e:
        # Log error but don't fail the API call
        print(f"Kafka producer error: {str(e)}")
    
    return jsonify(new_room.to_dict()), 201

@rooms_bp.route('/', methods=['GET'])
@jwt_required()
def get_all_rooms():
    """Get a list of all rooms (Employee or Admin)"""
    rooms = Room.query.all()
    return jsonify([room.to_dict() for room in rooms]), 200

@rooms_bp.route('/<int:room_id>', methods=['GET'])
@jwt_required()
def get_room(room_id):
    """Get details of a specific room (Employee or Admin)"""
    room = Room.query.get(room_id)
    if not room:
        return jsonify({"error": f"Room with ID {room_id} not found"}), 404
        
    return jsonify(room.to_dict()), 200

@rooms_bp.route('/<int:room_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_room(room_id):
    """Update a room (Admin only)"""
    room = Room.query.get(room_id)
    if not room:
        return jsonify({"error": f"Room with ID {room_id} not found"}), 404
    
    data = request.json
    if not data:
        return jsonify({"error": "No update data provided"}), 400
    
    # Update fields
    if 'name' in data:
        # Check if new name conflicts with existing room
        if data['name'] != room.name:
            existing_room = Room.query.filter_by(name=data['name']).first()
            if existing_room:
                return jsonify({"error": f"Room with name '{data['name']}' already exists"}), 409
        room.name = data['name']
        
    if 'capacity' in data:
        room.capacity = data['capacity']
        
    if 'equipment' in data:
        room.equipment = data['equipment']
    
    db.session.commit()
    
    # Produce kafka event
    try:
        producer = get_kafka_producer()
        producer.send(
            'room_events',
            {"event_type": "room_updated", "room": room.to_dict()}
        )
    except Exception as e:
        # Log error but don't fail the API call
        print(f"Kafka producer error: {str(e)}")
    
    return jsonify(room.to_dict()), 200

@rooms_bp.route('/<int:room_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_room(room_id):
    """Delete a room (Admin only)"""
    room = Room.query.get(room_id)
    if not room:
        return jsonify({"error": f"Room with ID {room_id} not found"}), 404
    
    room_data = room.to_dict()  # Store room data before deletion
    
    db.session.delete(room)
    db.session.commit()
    
    # Produce kafka event
    try:
        producer = get_kafka_producer()
        producer.send(
            'room_events',
            {"event_type": "room_deleted", "room_id": room_id}
        )
    except Exception as e:
        # Log error but don't fail the API call
        print(f"Kafka producer error: {str(e)}")
    
    return jsonify({"message": f"Room '{room_data['name']}' successfully deleted"}), 200