from flask import Blueprint, request, jsonify
from models import db, Center, Exam

centers_bp = Blueprint('centers', __name__)

@centers_bp.route('/', methods=['GET'])
def get_centers():
    centers = Center.query.all()
    return jsonify([{
        'id': c.id,
        'center_code': c.center_code,
        'center_name': c.center_name,
        'address': c.address,
        'status': c.status
    } for c in centers])

@centers_bp.route('/', methods=['POST'])
def create_center():
    data = request.get_json()
    if not data or not data.get('center_code') or not data.get('center_name'):
        return jsonify({'message': 'Center code and name are required'}), 400
    
    # Check if center_code already exists
    existing = Center.query.filter_by(center_code=data['center_code']).first()
    if existing:
        return jsonify({'message': f"Center code '{data['center_code']}' already exists. Please use a different code."}), 400
    
    try:
        center = Center(
            center_code=data['center_code'],
            center_name=data['center_name'],
            address=data.get('address', ''),
            status=data.get('status', 'active')
        )
        db.session.add(center)
        db.session.commit()
        return jsonify({'message': 'Center created successfully', 'id': center.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to create center: ' + str(e)}), 400

@centers_bp.route('/<int:id>', methods=['PUT'])
def update_center(id):
    center = Center.query.get_or_404(id)
    data = request.get_json()
    try:
        if 'center_code' in data:
            # Check uniqueness if code is changing
            if data['center_code'] != center.center_code:
                existing = Center.query.filter_by(center_code=data['center_code']).first()
                if existing:
                    return jsonify({'message': f"Center code '{data['center_code']}' already exists."}), 400
            center.center_code = data['center_code']
        if 'center_name' in data: center.center_name = data['center_name']
        if 'address' in data: center.address = data['address']
        if 'status' in data: center.status = data['status']
        
        db.session.commit()
        return jsonify({'message': 'Center updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update center: ' + str(e)}), 400

@centers_bp.route('/<int:id>', methods=['DELETE'])
def delete_center(id):
    center = Center.query.get_or_404(id)
    try:
        db.session.delete(center)
        db.session.commit()
        return jsonify({'message': 'Center deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Cannot delete center. It may have users or data linked to it.'}), 400

@centers_bp.route('/<int:id>/exams', methods=['GET'])
def get_center_exams(id):
    exams = Exam.query.all()
    return jsonify([{
        'id': e.id,
        'exam_code': e.exam_code,
        'exam_name': e.exam_name,
        'subject': e.subject,
        'exam_date': e.exam_date.isoformat(),
        'start_time': e.start_time.isoformat(),
        'duration': e.duration,
        'status': e.status
    } for e in exams])
