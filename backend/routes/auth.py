from flask import Blueprint, request, jsonify
from models import db, User, ActivityLog
from flask_bcrypt import Bcrypt
import datetime

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    
    if user and bcrypt.check_password_hash(user.password_hash, password):
        user.last_login = datetime.datetime.utcnow()
        db.session.commit()
        
        # Log activity
        log = ActivityLog(
            user_id=user.id,
            center_id=user.center_id,
            action='User Login',
            ip_address=request.remote_addr,
            status='Success'
        )
        db.session.add(log)
        db.session.commit()
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'center_id': user.center_id
        }
        
        if user.center:
            user_data['center_code'] = user.center.center_code
            user_data['center_name'] = user.center.center_name
        
        return jsonify({
            'message': 'Login successful',
            'user': user_data,
            'token': 'dummy-jwt-token'
        }), 200
    
    return jsonify({'message': 'Invalid credentials'}), 401

@auth_bp.route('/logout', methods=['POST'])
def logout():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    
    if user_id:
        user = User.query.get(user_id)
        if user:
            log = ActivityLog(
                user_id=user.id,
                center_id=user.center_id,
                action='User Logout',
                ip_address=request.remote_addr,
                status='Success'
            )
            db.session.add(log)
            db.session.commit()
            
    return jsonify({'message': 'Logged out successfully'}), 200
