from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from models import db, Reservation
from functools import wraps
from datetime import datetime, date
from sqlalchemy import and_, or_

# Create blueprints
reservations_bp = Blueprint('reservations', __name__, url_prefix='/reservations')
availability_bp = Blueprint('availability', __name__, url_prefix='/availability')

# Custom decorator for checking if user is admin or owner
def admin_or_owner_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        jwt_data = get_jwt()
        user_id = jwt_data.get('user_id')
        role = jwt_data.get('role')
        
        reservation_id = kwargs.get('reservation_id')
        if reservation_id:
            reservation = Reservation.query.get(reservation_id)
            if not reservation:
                return jsonify({"error": "Reservation not found"}), 404
            
            # Allow if admin or owner
            if role == 'Admin' or (reservation.user_id == user_id):
                return fn(*args, **kwargs)
            else:
                return jsonify({"error": "You do not have permission to access this reservation"}), 403
        
        return fn(*args, **kwargs)
    return wrapper

@reservations_bp.route('/', methods=['POST'])
@jwt_required()
def create_reservation():
    """Create a new reservation"""
    data = request.json
    user_id = get_jwt_identity().get('user_id')
    
    # Validate input
    if not data or 'room_id' not in data or 'start_time' not in data or 'end_time' not in data:
        return jsonify({"error": "Missing required fields: room_id, start_time, end_time"}), 400
    
    try:
        start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({"error": "Invalid datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"}), 400
    
    # Validation checks
    if start_time >= end_time:
        return jsonify({"error": "Start time must be before end time"}), 400
        
    if start_time <= datetime.utcnow():
        return jsonify({"error": "Start time must be in the future"}), 400
    
    # Check for conflicting reservations
    conflicting_reservation = Reservation.query.filter(
        Reservation.room_id == data['room_id'],
        or_(
            and_(start_time >= Reservation.start_time, start_time < Reservation.end_time),
            and_(end_time > Reservation.start_time, end_time <= Reservation.end_time),
            and_(start_time <= Reservation.start_time, end_time >= Reservation.end_time)
        )
    ).first()
    
    if conflicting_reservation:
        return jsonify({"error": "Room is already reserved for the selected time slot"}), 409
    
    # Create new reservation
    new_reservation = Reservation(
        room_id=data['room_id'],
        user_id=user_id,
        start_time=start_time,
        end_time=end_time
    )
    
    db.session.add(new_reservation)
    db.session.commit()
    
    return jsonify(new_reservation.to_dict()), 201

@reservations_bp.route('/', methods=['GET'])
@jwt_required()
def get_reservations():
    """Get reservations (filters by user_id for regular employees, all for admin)"""
    jwt_data = get_jwt()
    user_id = jwt_data.get('user_id')
    role = jwt_data.get('role')
    
    # Process query parameters
    filters = []
    
    # Filter by room_id if provided
    room_id = request.args.get('room_id')
    if room_id:
        try:
            filters.append(Reservation.room_id == int(room_id))
        except ValueError:
            return jsonify({"error": "Invalid room_id format"}), 400
    
    # Filter by date if provided
    date_str = request.args.get('date')
    if date_str:
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            filters.append(db.func.date(Reservation.start_time) == filter_date)
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    # Filter by specific user_id if provided and user is Admin
    specific_user_id = request.args.get('user_id')
    if specific_user_id and role == 'Admin':
        try:
            filters.append(Reservation.user_id == int(specific_user_id))
        except ValueError:
            return jsonify({"error": "Invalid user_id format"}), 400
    # Otherwise, if not admin, restrict to own reservations
    elif role != 'Admin':
        filters.append(Reservation.user_id == user_id)
    
    # Get reservations based on filters
    if filters:
        reservations = Reservation.query.filter(*filters).all()
    else:
        reservations = Reservation.query.all()
    
    return jsonify([reservation.to_dict() for reservation in reservations]), 200

@reservations_bp.route('/<int:reservation_id>', methods=['GET'])
@jwt_required()
@admin_or_owner_required
def get_reservation(reservation_id):
    """Get a specific reservation"""
    reservation = Reservation.query.get(reservation_id)
    return jsonify(reservation.to_dict()), 200

@reservations_bp.route('/<int:reservation_id>', methods=['DELETE'])
@jwt_required()
@admin_or_owner_required
def delete_reservation(reservation_id):
    """Delete/cancel a reservation"""
    reservation = Reservation.query.get(reservation_id)
    
    db.session.delete(reservation)
    db.session.commit()
    
    return jsonify({"message": "Reservation successfully cancelled"}), 200

@availability_bp.route('/rooms/<int:room_id>', methods=['GET'])
@jwt_required()
def check_room_availability(room_id):
    """Check room availability for a date range"""
    # Validate query parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    if not start_date_str or not end_date_str:
        return jsonify({"error": "Missing required query parameters: start_date, end_date"}), 400
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        # Set end date to end of day
        end_date = datetime.combine(end_date.date(), datetime.max.time())
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    # Check if start_date is before end_date
    if start_date > end_date:
        return jsonify({"error": "Start date must be before end date"}), 400
    
    # Query existing reservations for the room within the date range
    reservations = Reservation.query.filter(
        Reservation.room_id == room_id,
        Reservation.start_time <= end_date,
        Reservation.end_time >= start_date
    ).all()
    
    # Get booked slots
    booked_slots = [
        {
            'start_time': reservation.start_time.isoformat(),
            'end_time': reservation.end_time.isoformat()
        }
        for reservation in reservations
    ]
    
    return jsonify({
        'room_id': room_id,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'booked_slots': booked_slots
    }), 200