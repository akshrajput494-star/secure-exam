from flask import Blueprint, request, jsonify, current_app
from models import db, Biometric, Center
import os
import werkzeug.utils

biometrics_bp = Blueprint('biometrics', __name__)

@biometrics_bp.route('/', methods=['GET'])
def get_biometrics():
    biometrics = Biometric.query.all()
    return jsonify([{
        'id': b.id,
        'center_id': b.center_id,
        'center_name': b.center.center_name if b.center else '',
        'center_code': b.center.center_code if b.center else '',
        'head_name': b.head_name,
        'designation': b.designation,
        'file_name': b.file_name,
        'file_size': b.file_size,
        'uploaded_at': b.uploaded_at.isoformat(),
        'status': b.status
    } for b in biometrics])

@biometrics_bp.route('/', methods=['POST'])
def upload_biometric():
    if 'file' not in request.files:
        return jsonify({'message': 'No file provided'}), 400
    
    file = request.files['file']
    center_id = request.form.get('center_id')
    head_name = request.form.get('head_name')
    designation = request.form.get('designation', '')
    
    if not center_id or not head_name:
        return jsonify({'message': 'center_id and head_name are required'}), 400
    
    if file.filename == '':
        return jsonify({'message': 'No file selected'}), 400
    
    filename = werkzeug.utils.secure_filename(file.filename)
    upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'biometrics')
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)
    
    bio = Biometric(
        center_id=int(center_id),
        head_name=head_name,
        designation=designation,
        file_name=filename,
        file_path=filepath,
        file_size=os.path.getsize(filepath)
    )
    db.session.add(bio)
    db.session.commit()
    
    return jsonify({'message': 'Biometric uploaded successfully'}), 201

@biometrics_bp.route('/<int:bio_id>', methods=['DELETE'])
def delete_biometric(bio_id):
    bio = Biometric.query.get_or_404(bio_id)
    if os.path.exists(bio.file_path):
        os.remove(bio.file_path)
    db.session.delete(bio)
    db.session.commit()
    return jsonify({'message': 'Biometric deleted'})
