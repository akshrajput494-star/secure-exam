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
    try:
        hashed_pw = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        user = User(
            username=data['username'],
            password_hash=hashed_pw,
            role=data.get('role', 'center'),
            center_id=data.get('center_id')
        )
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'User created successfully', 'id': user.id}), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 400

@users_bp.route('/<int:id>', methods=['DELETE'])
def delete_user(id):
    user = User.query.get_or_404(id)
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User deleted successfully'})
    except Exception as e:
        return jsonify({'message': str(e)}), 400
