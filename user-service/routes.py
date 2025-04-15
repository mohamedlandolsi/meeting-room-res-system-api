from flask import Blueprint, request, jsonify, redirect, url_for, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import requests
from models import db, User

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
        user = User(google_id=google_id, email=email, name=name, role='Employee')
        db.session.add(user)
        db.session.commit()
    
    # Generate JWT access token
    access_token = create_access_token(
        identity={"user_id": user.id, "email": user.email, "role": user.role}
    )
    
    return jsonify({"access_token": access_token, "user": user.to_dict()}), 200

@user_bp.route('/me', methods=['GET'])
@jwt_required()
def get_user_profile():
    """Get the current user's profile (protected route)"""
    current_user = get_jwt_identity()
    user_id = current_user.get('user_id')
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify(user.to_dict()), 200