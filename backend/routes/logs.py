from flask import Blueprint, request, jsonify
from models import db, ActivityLog, User, Center, Exam
from datetime import datetime

logs_bp = Blueprint('logs', __name__)

@logs_bp.route('/', methods=['GET'])
def get_logs():
    query = ActivityLog.query
    
    # Query params
    center_id = request.args.get('center_id')
    user_id = request.args.get('user_id')
    exam_id = request.args.get('exam_id')
    action = request.args.get('action')
    date_str = request.args.get('date')
    
    if center_id:
        query = query.filter_by(center_id=center_id)
    if user_id:
        query = query.filter_by(user_id=user_id)
    if exam_id:
        query = query.filter_by(exam_id=exam_id)
    if action:
        query = query.filter(ActivityLog.action.ilike(f"%{action}%"))
    if date_str:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            # In a real app we'd filter by casting timestamp to date
        except ValueError:
            pass
            
    logs = query.order_by(ActivityLog.timestamp.desc()).limit(100).all()
    
    result = []
    for l in logs:
        result.append({
            'id': l.id,
            'action': l.action,
            'timestamp': l.timestamp.isoformat(),
            'ip_address': l.ip_address,
            'status': l.status,
            'user': l.user.username if l.user else None,
            'center': l.center.center_name if l.center else None,
            'exam': l.exam.exam_code if l.exam else None
        })
        
    return jsonify(result)

@logs_bp.route('/', methods=['POST'])
def create_log():
    data = request.get_json()
    try:
        log = ActivityLog(
            user_id=data.get('user_id'),
            center_id=data.get('center_id'),
            exam_id=data.get('exam_id'),
            action=data.get('action', 'Unknown Action'),
            ip_address=request.remote_addr,
            status=data.get('status', 'Success')
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'message': 'Log created successfully', 'id': log.id}), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 400
