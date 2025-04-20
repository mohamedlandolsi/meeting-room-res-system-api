from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from models import db
from routes import rooms_bp
import os

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
    app.register_blueprint(rooms_bp)
    
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
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    app.logger.info("Room service initialized", extra={"event": "service_startup"})
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5001)), debug=app.config['DEBUG'])