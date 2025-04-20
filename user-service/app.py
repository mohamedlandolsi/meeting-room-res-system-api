from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from models import db
from routes import auth_bp, user_bp
import os

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('config.Config')
    
    # Configure logging
    from config import Config
    Config.configure_logging(app)
    
    # Initialize extensions
    db.init_app(app)
    jwt = JWTManager(app)
    
    # JWT error handlers
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        app.logger.warning(f"Invalid token provided: {error}", extra={"error_type": "auth_error"})
        return jsonify({
            "error": "Invalid token",
            "message": "The token provided is invalid or malformed."
        }), 401
        
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        app.logger.warning(f"Missing token: {error}", extra={"error_type": "auth_error"})
        return jsonify({
            "error": "Authorization required",
            "message": "Request does not contain a valid token."
        }), 401
        
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        app.logger.warning("Expired token used", extra={
            "error_type": "auth_error",
            "user_id": jwt_payload.get("sub", "unknown")
        })
        return jsonify({
            "error": "Token expired",
            "message": "The token has expired. Please log in again."
        }), 401
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    
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
        
    @app.errorhandler(500)
    def server_error(error):
        app.logger.error(f"Server error: {error}", extra={"error_type": "server_error"})
        return jsonify({"error": "Internal Server Error", "message": str(error)}), 500
    
    @app.errorhandler(422)
    def unprocessable_entity(error):
        app.logger.warning(f"Unprocessable entity: {error}", extra={"error_type": "client_error"})
        return jsonify({"error": "Unprocessable Entity", "message": str(error)}), 422
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    app.logger.info("User service initialized", extra={"event": "service_startup"})
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=app.config['DEBUG'])