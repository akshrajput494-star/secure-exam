from server import create_app
from models import db, User, Center, Exam, ActivityLog, Biometric
from flask_bcrypt import Bcrypt
from datetime import datetime, date, time, timedelta

app = create_app()
bcrypt = Bcrypt(app)

with app.app_context():
    db.drop_all()
    db.create_all()
    
    # 1. Admin user
    hashed_pw = bcrypt.generate_password_hash('admin123').decode('utf-8')
    admin = User(username='admin', password_hash=hashed_pw, role='admin')
    db.session.add(admin)
    
    # 2. Sample Centers
    c1 = Center(center_code='C001', center_name='Main Test Center', address='123 Education Blvd')
    c2 = Center(center_code='C002', center_name='City Exam Hall', address='456 University Ave')
    c3 = Center(center_code='C003', center_name='District Center', address='789 School Road')
    db.session.add_all([c1, c2, c3])
    db.session.commit()
    
    # 3. Center Users
    hashed_pw_c = bcrypt.generate_password_hash('center123').decode('utf-8')
    u1 = User(username='center_C001', password_hash=hashed_pw_c, role='center', center_id=c1.id)
    u2 = User(username='center_C002', password_hash=hashed_pw_c, role='center', center_id=c2.id)
    u3 = User(username='center_C003', password_hash=hashed_pw_c, role='center', center_id=c3.id)
    db.session.add_all([u1, u2, u3])
    db.session.commit()
    
    # 4. Sample Exams (Future dates)
    today = date.today()
    e1 = Exam(
        exam_code='MATH101', 
        exam_name='Mathematics Advanced', 
        subject='Mathematics', 
        exam_date=today + timedelta(days=7),
        start_time=time(9, 0),
        duration=180
    )
    e2 = Exam(
        exam_code='PHYS201', 
        exam_name='Physics Fundamentals', 
        subject='Physics', 
        exam_date=today + timedelta(days=14),
        start_time=time(14, 0),
        duration=120
    )
    e3 = Exam(
        exam_code='CHEM301', 
        exam_name='Organic Chemistry', 
        subject='Chemistry', 
        exam_date=today + timedelta(days=21),
        start_time=time(10, 30),
        duration=150
    )
    db.session.add_all([e1, e2, e3])
    db.session.commit()
    
    # 5. Sample Logs
    l1 = ActivityLog(user_id=admin.id, action='System Initialized', status='Success')
    l2 = ActivityLog(user_id=admin.id, action='Exam MATH101 Created', exam_id=e1.id, status='Success')
    l3 = ActivityLog(user_id=u1.id, center_id=c1.id, action='User Logged In', status='Success')
    db.session.add_all([l1, l2, l3])
    db.session.commit()

print("Database initialized with:")
print("- Admin user: admin / admin123")
print("- 3 Centers and corresponding users (e.g., center_C001 / center123)")
print("- 3 upcoming Exams")
print("- Sample Activity Logs")
