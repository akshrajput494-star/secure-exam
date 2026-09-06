import os

basedir = os.path.abspath(os.path.dirname(__file__))
db_dir = os.path.abspath(os.path.join(basedir, '..', 'database'))
os.makedirs(db_dir, exist_ok=True)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'super-secret-exam-key')
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url or f'sqlite:///{os.path.join(db_dir, "secure_exam.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
