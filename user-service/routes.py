from flask import Blueprint, request, jsonify, redirect, url_for, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
import requests
from models import db, User
from functools import wraps

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
user_bp = Blueprint('user', __name__, url_prefix='/users')

@auth_bp.route('/google/login', methods=['GET'])
def google_login():
    """Redirect to Google OAuth consent screen"""
    client_id = current_app.config['GOOGLE_CLIENT_ID']
    # Prepare the Google OAuth URL
    redirect_uri = url_for('auth.google_callback', _external=True)
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&response_type=code&scope=email%20profile&redirect_uri={redirect_uri}"
    return redirect(google_auth_url)

@auth_bp.route('/google/callback', methods=['GET'])
def google_callback():
    """Handle the callback from Google after user consent"""
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "Authentication failed: No authorization code received"}), 400

    # Exchange authorization code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    client_id = current_app.config['GOOGLE_CLIENT_ID']
    client_secret = current_app.config['GOOGLE_CLIENT_SECRET']
    redirect_uri = url_for('auth.google_callback', _external=True)

    token_payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }

    token_response = requests.post(token_url, data=token_payload)
    if not token_response.ok:
        return jsonify({"error": "Failed to retrieve access token"}), 400
    
    token_data = token_response.json()
    access_token = token_data.get('access_token')
    
    # Get user profile information
    user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    user_info_response = requests.get(user_info_url, headers={"Authorization": f"Bearer {access_token}"})
    if not user_info_response.ok:
        return jsonify({"error": "Failed to retrieve user information"}), 400
        
    user_info = user_info_response.json()
    google_id = user_info.get('sub')
    email = user_info.get('email')
    name = user_info.get('name')
    
    # Find user in DB by google_id or create new user
    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        # Check if email should be granted admin role
        role = 'Admin' if email in current_app.config['ADMIN_EMAILS'] else 'Employee'
        user = User(google_id=google_id, email=email, name=name, role=role)
        db.session.add(user)
        db.session.commit()
    # Update existing user's role if their email is in ADMIN_EMAILS
    elif email in current_app.config['ADMIN_EMAILS'] and user.role != 'Admin':
        user.role = 'Admin'
        db.session.commit()
    
    # Generate JWT access token - use str(user.id) as identity
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"email": user.email, "role": user.role}
    )
    
    return jsonify({"access_token": access_token, "user": user.to_dict()}), 200

# Add admin required decorator
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        jwt_data = get_jwt()
        if jwt_data.get('role') != 'Admin':
            return jsonify({"error": "Admin privileges required"}), 403
        return fn(*args, **kwargs)
    return wrapper

@user_bp.route('/me', methods=['GET'])
@jwt_required()
def get_user_profile():
    """Get the current user's profile (protected route)"""
    try:
        user_id = get_jwt_identity()
        if user_id is None:
            return jsonify({"error": "Invalid user identity"}), 401
        
        # Ensure user_id is properly handled as a string or int
        if isinstance(user_id, str) and user_id.isdigit():
            user_id = int(user_id)
        elif not isinstance(user_id, int):
            return jsonify({"error": "Invalid user ID format"}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify(user.to_dict()), 200
    except Exception as e:
        current_app.logger.error(f"Error in get_user_profile: {str(e)}")
        return jsonify({"error": "Error retrieving user profile", "message": str(e)}), 500

@user_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_user(user_id):
    """Update a user (Admin only)"""
    # Check if user exists
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": f"User with ID {user_id} not found"}), 404
    
    data = request.json
    if not data:
        return jsonify({"error": "No update data provided"}), 400
    
    # Update fields
    if 'name' in data:
        user.name = data['name']
        
    if 'role' in data:
        # Validate role value
        allowed_roles = ['Employee', 'Admin']
        if data['role'] not in allowed_roles:
            return jsonify({"error": f"Invalid role. Must be one of: {', '.join(allowed_roles)}"}), 400
        user.role = data['role']
    
    # Email can only be updated if the new email is not used by another user
    if 'email' in data and data['email'] != user.email:
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({"error": f"Email {data['email']} is already in use"}), 409
        user.email = data['email']
    
    db.session.commit()
    
    return jsonify(user.to_dict()), 200

@user_bp.route('/', methods=['GET'])
@jwt_required()
@admin_required
def get_all_users():
    """Get a list of all users (Admin only)"""
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200