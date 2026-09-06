from flask import Blueprint, request, jsonify
from models import db, User, Center
from flask_bcrypt import Bcrypt

users_bp = Blueprint('users', __name__)
bcrypt = Bcrypt()

@users_bp.route('/', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'role': u.role,
        'center_id': u.center_id,
        'center_name': u.center.center_name if u.center else None,
        'created_at': u.created_at.isoformat(),
        'last_login': u.last_login.isoformat() if u.last_login else None
    } for u in users])

@users_bp.route('/', methods=['POST'])
def create_user():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Username and password are required'}), 400
    
    # Check if username already exists
    existing = User.query.filter_by(username=data['username']).first()
    if existing:
        return jsonify({'message': f"Username '{data['username']}' already exists. Please choose a different username."}), 400
    
    # If role is center, validate center_id
    center_id = data.get('center_id')
    if data.get('role') == 'center' and center_id:
        center = Center.query.get(center_id)
        if not center:
            return jsonify({'message': 'Selected center does not exist'}), 400
    
    try:
        hashed_pw = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        user = User(
            username=data['username'],
            password_hash=hashed_pw,
            role=data.get('role', 'center'),
            center_id=center_id if center_id else None
        )
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'User created successfully', 'id': user.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to create user: ' + str(e)}), 400

@users_bp.route('/<int:id>', methods=['DELETE'])
def delete_user(id):
    user = User.query.get_or_404(id)
    if user.username == 'admin':
        return jsonify({'message': 'Cannot delete the admin user'}), 400
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to delete user: ' + str(e)}), 400
