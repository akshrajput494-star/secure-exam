from flask import Blueprint, request, jsonify, current_app, send_file
from models import db, Exam, ExamPaper, ActivityLog
import os
import werkzeug.utils
from datetime import datetime

exams_bp = Blueprint('exams', __name__)

@exams_bp.route('/', methods=['GET'])
def get_exams():
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

@exams_bp.route('/', methods=['POST'])
def create_exam():
    data = request.get_json()
    try:
        date_obj = datetime.strptime(data['exam_date'], '%Y-%m-%d').date()
        time_obj = datetime.strptime(data['start_time'], '%H:%M').time()
        
        exam = Exam(
            exam_code=data['exam_code'],
            exam_name=data['exam_name'],
            subject=data['subject'],
            exam_date=date_obj,
            start_time=time_obj,
            duration=int(data['duration']),
            status=data.get('status', 'scheduled')
        )
        db.session.add(exam)
        db.session.commit()
        return jsonify({'message': 'Exam created successfully', 'id': exam.id}), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 400

@exams_bp.route('/<int:id>', methods=['PUT'])
def update_exam(id):
    exam = Exam.query.get_or_404(id)
    data = request.get_json()
    try:
        if 'exam_code' in data: exam.exam_code = data['exam_code']
        if 'exam_name' in data: exam.exam_name = data['exam_name']
        if 'subject' in data: exam.subject = data['subject']
        if 'exam_date' in data: 
            exam.exam_date = datetime.strptime(data['exam_date'], '%Y-%m-%d').date()
        if 'start_time' in data:
            exam.start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        if 'duration' in data: exam.duration = int(data['duration'])
        if 'status' in data: exam.status = data['status']
        
        db.session.commit()
        return jsonify({'message': 'Exam updated successfully'})
    except Exception as e:
        return jsonify({'message': str(e)}), 400

@exams_bp.route('/<int:id>', methods=['DELETE'])
def delete_exam(id):
    exam = Exam.query.get_or_404(id)
    # Also delete associated papers
    for paper in exam.exam_papers:
        if os.path.exists(paper.file_path):
            try:
                os.remove(paper.file_path)
            except:
                pass
        db.session.delete(paper)
        
    db.session.delete(exam)
    db.session.commit()
    return jsonify({'message': 'Exam deleted successfully'})

@exams_bp.route('/<int:exam_id>/upload', methods=['POST'])
def upload_paper(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
        
    if file and file.filename.endswith('.pdf'):
        filename = werkzeug.utils.secure_filename(file.filename)
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, f"{exam_id}_{filename}")
        file.save(filepath)
        
        paper = ExamPaper(
            exam_id=exam_id,
            file_name=filename,
            file_path=filepath,
            file_size=os.path.getsize(filepath)
        )
        db.session.add(paper)
        db.session.commit()
        
        log = ActivityLog(action='Paper Uploaded', exam_id=exam_id, status='Success', ip_address=request.remote_addr)
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'message': 'File uploaded successfully', 'id': paper.id}), 201
    
    return jsonify({'message': 'Invalid file type. Only PDF allowed.'}), 400

@exams_bp.route('/<int:exam_id>/papers', methods=['GET'])
def get_exam_papers(exam_id):
    papers = ExamPaper.query.filter_by(exam_id=exam_id).all()
    return jsonify([{
        'id': p.id,
        'file_name': p.file_name,
        'file_size': p.file_size,
        'uploaded_at': p.uploaded_at.isoformat(),
        'status': p.status
    } for p in papers])

@exams_bp.route('/papers/<int:paper_id>/download', methods=['GET'])
def download_paper(paper_id):
    paper = ExamPaper.query.get_or_404(paper_id)
    if os.path.exists(paper.file_path):
        log = ActivityLog(action='Paper Downloaded', exam_id=paper.exam_id, status='Success', ip_address=request.remote_addr)
        db.session.add(log)
        db.session.commit()
        return send_file(paper.file_path, as_attachment=True, download_name=paper.file_name)
    return jsonify({'message': 'File not found'}), 404
