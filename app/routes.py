from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from functools import wraps
import os

from app.models import db, Admin, Student, Company, PlacementDrive, Application

# Define blueprints
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
company_bp = Blueprint('company', __name__, url_prefix='/company')
student_bp = Blueprint('student', __name__, url_prefix='/student')

# ======================== HELPER FUNCTIONS ========================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def company_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'company':
            flash('Company access required', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'student':
            flash('Student access required', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ======================== MAIN ROUTES ========================

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))

# ======================== AUTHENTICATION ROUTES ========================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_type = request.form.get('user_type')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if user_type == 'admin':
            user = Admin.query.filter_by(email=email).first()
            if user and check_password_hash(user.password, password):
                session['user_id'] = user.id
                session['user_type'] = 'admin'
                session['username'] = user.username
                session['name'] = user.name
                flash('Admin login successful', 'success')
                return redirect(url_for('admin.dashboard'))
        
        elif user_type == 'company':
            user = Company.query.filter_by(email=email).first()
            if user and check_password_hash(user.password, password):
                if user.is_blacklisted:
                    flash('Your account has been blacklisted', 'danger')
                    return redirect(url_for('auth.login'))
                if user.approval_status != 'Approved':
                    flash('Your account is not yet approved by admin', 'warning')
                    return redirect(url_for('auth.login'))
                session['user_id'] = user.id
                session['user_type'] = 'company'
                session['username'] = user.company_name
                session['name'] = user.hr_name
                flash('Company login successful', 'success')
                return redirect(url_for('company.dashboard'))
        
        elif user_type == 'student':
            user = Student.query.filter_by(email=email).first()
            if user and check_password_hash(user.password, password):
                if user.is_blacklisted:
                    flash('Your account has been blacklisted', 'danger')
                    return redirect(url_for('auth.login'))
                if not user.is_active:
                    flash('Your account is inactive', 'warning')
                    return redirect(url_for('auth.login'))
                session['user_id'] = user.id
                session['user_type'] = 'student'
                session['username'] = user.roll_number
                session['name'] = user.full_name
                flash('Student login successful', 'success')
                return redirect(url_for('student.dashboard'))
        
        flash('Invalid credentials', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/register-company', methods=['GET', 'POST'])
def register_company():
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        email = request.form.get('email')
        password = request.form.get('password')
        hr_name = request.form.get('hr_name')
        hr_contact = request.form.get('hr_contact')
        website = request.form.get('website')
        description = request.form.get('description')
        
        if Company.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.register_company'))
        
        company = Company(
            company_name=company_name,
            email=email,
            password=generate_password_hash(password),
            hr_name=hr_name,
            hr_contact=hr_contact,
            website=website,
            description=description,
            approval_status='Pending'
        )
        
        try:
            db.session.add(company)
            db.session.commit()
            flash(f'Company registered successfully. Awaiting admin approval.', 'success')
            return redirect(url_for('auth.login'))
        except:
            db.session.rollback()
            flash('Error registering company', 'danger')
    
    return render_template('auth/register_company.html')

@auth_bp.route('/register-student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        roll_number = request.form.get('roll_number')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        cgpa = request.form.get('cgpa')
        branch = request.form.get('branch')
        semester = request.form.get('semester')
        
        if Student.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.register_student'))
        
        if Student.query.filter_by(roll_number=roll_number).first():
            flash('Roll number already registered', 'danger')
            return redirect(url_for('auth.register_student'))
        
        student = Student(
            roll_number=roll_number,
            full_name=full_name,
            email=email,
            password=generate_password_hash(password),
            phone=phone,
            cgpa=float(cgpa) if cgpa else None,
            branch=branch,
            semester=int(semester) if semester else None
        )
        
        try:
            db.session.add(student)
            db.session.commit()
            flash('Student registered successfully. You can now login.', 'success')
            return redirect(url_for('auth.login'))
        except:
            db.session.rollback()
            flash('Error registering student', 'danger')
    
    return render_template('auth/register_student.html')

# ======================== ADMIN ROUTES ========================

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    total_students = Student.query.count()
    total_companies = Company.query.count()
    total_drives = PlacementDrive.query.count()
    total_applications = Application.query.count()
    
    pending_companies = Company.query.filter_by(approval_status='Pending').count()
    pending_drives = PlacementDrive.query.filter_by(approval_status='Pending').count()
    
    # Graphs Data
    status_counts = db.session.query(Application.status, db.func.count(Application.id)).group_by(Application.status).all()
    app_status_labels = [row[0] for row in status_counts]
    app_status_data = [row[1] for row in status_counts]
    
    branch_counts = db.session.query(Student.branch, db.func.count(Student.id)).filter(Student.branch != None, Student.branch != '').group_by(Student.branch).all()
    branch_labels = [row[0] for row in branch_counts]
    branch_data = [row[1] for row in branch_counts]
    
    return render_template('admin/dashboard.html',
                          total_students=total_students,
                          total_companies=total_companies,
                          total_drives=total_drives,
                          total_applications=total_applications,
                          pending_companies=pending_companies,
                          pending_drives=pending_drives,
                          app_status_labels=app_status_labels,
                          app_status_data=app_status_data,
                          branch_labels=branch_labels,
                          branch_data=branch_data)

@admin_bp.route('/companies')
@admin_required
def manage_companies():
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    
    query = Company.query
    
    if search:
        query = query.filter(
            (Company.company_name.ilike(f'%{search}%')) |
            (Company.email.ilike(f'%{search}%'))
        )
    
    if status:
        query = query.filter_by(approval_status=status)
    
    companies = query.all()
    return render_template('admin/manage_companies.html', companies=companies, search=search, status=status)

@admin_bp.route('/students')
@admin_required
def manage_students():
    search = request.args.get('search', '')
    
    query = Student.query
    
    if search:
        query = query.filter(
            (Student.full_name.ilike(f'%{search}%')) |
            (Student.roll_number.ilike(f'%{search}%')) |
            (Student.email.ilike(f'%{search}%'))
        )
    
    students = query.all()
    return render_template('admin/manage_students.html', students=students, search=search)

@admin_bp.route('/placement-drives')
@admin_required
def manage_drives():
    status = request.args.get('status', '')
    
    query = PlacementDrive.query
    
    if status:
        query = query.filter_by(approval_status=status)
    
    drives = query.all()
    return render_template('admin/manage_drives.html', drives=drives, status=status)

@admin_bp.route('/approve-company/<int:company_id>', methods=['POST'])
@admin_required
def approve_company(company_id):
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    company.approval_status = 'Approved'
    db.session.commit()
    flash(f'Company {company.company_name} approved', 'success')
    return redirect(url_for('admin.manage_companies'))

@admin_bp.route('/reject-company/<int:company_id>', methods=['POST'])
@admin_required
def reject_company(company_id):
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    company.approval_status = 'Rejected'
    db.session.commit()
    flash(f'Company {company.company_name} rejected', 'warning')
    return redirect(url_for('admin.manage_companies'))

@admin_bp.route('/approve-drive/<int:drive_id>', methods=['POST'])
@admin_required
def approve_drive(drive_id):
    drive = PlacementDrive.query.get(drive_id)
    if not drive:
        return jsonify({'error': 'Drive not found'}), 404
    
    drive.approval_status = 'Approved'
    db.session.commit()
    flash(f'Placement drive {drive.job_title} approved', 'success')
    return redirect(url_for('admin.manage_drives'))

@admin_bp.route('/reject-drive/<int:drive_id>', methods=['POST'])
@admin_required
def reject_drive(drive_id):
    drive = PlacementDrive.query.get(drive_id)
    if not drive:
        return jsonify({'error': 'Drive not found'}), 404
    
    drive.approval_status = 'Rejected'
    db.session.commit()
    flash(f'Placement drive {drive.job_title} rejected', 'warning')
    return redirect(url_for('admin.manage_drives'))

@admin_bp.route('/blacklist-student/<int:student_id>', methods=['POST'])
@admin_required
def blacklist_student(student_id):
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    student.is_blacklisted = True
    db.session.commit()
    flash(f'Student {student.full_name} blacklisted', 'warning')
    return redirect(url_for('admin.manage_students'))

@admin_bp.route('/unblacklist-student/<int:student_id>', methods=['POST'])
@admin_required
def unblacklist_student(student_id):
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    student.is_blacklisted = False
    db.session.commit()
    flash(f'Student {student.full_name} unblacklisted', 'success')
    return redirect(url_for('admin.manage_students'))

@admin_bp.route('/blacklist-company/<int:company_id>', methods=['POST'])
@admin_required
def blacklist_company(company_id):
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    company.is_blacklisted = True
    db.session.commit()
    flash(f'Company {company.company_name} blacklisted', 'warning')
    return redirect(url_for('admin.manage_companies'))

@admin_bp.route('/unblacklist-company/<int:company_id>', methods=['POST'])
@admin_required
def unblacklist_company(company_id):
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    company.is_blacklisted = False
    db.session.commit()
    flash(f'Company {company.company_name} unblacklisted', 'success')
    return redirect(url_for('admin.manage_companies'))

@admin_bp.route('/delete-student/<int:student_id>', methods=['POST'])
@admin_required
def delete_student(student_id):
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    db.session.delete(student)
    db.session.commit()
    flash(f'Student {student.full_name} deleted', 'warning')
    return redirect(url_for('admin.manage_students'))

@admin_bp.route('/delete-company/<int:company_id>', methods=['POST'])
@admin_required
def delete_company(company_id):
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    db.session.delete(company)
    db.session.commit()
    flash(f'Company {company.company_name} deleted', 'warning')
    return redirect(url_for('admin.manage_companies'))

@admin_bp.route('/edit-student/<int:student_id>', methods=['GET', 'POST'])
@admin_required
def edit_student(student_id):
    student = Student.query.get(student_id)
    if not student:
        flash('Student not found', 'danger')
        return redirect(url_for('admin.manage_students'))
    
    if request.method == 'POST':
        student.full_name = request.form.get('full_name')
        student.email = request.form.get('email')
        student.phone = request.form.get('phone')
        student.cgpa = float(request.form.get('cgpa')) if request.form.get('cgpa') else student.cgpa
        student.branch = request.form.get('branch')
        student.semester = int(request.form.get('semester')) if request.form.get('semester') else student.semester
        
        db.session.commit()
        flash('Student profile updated successfully', 'success')
        return redirect(url_for('admin.manage_students'))
        
    return render_template('admin/edit_student.html', student=student)

@admin_bp.route('/edit-company/<int:company_id>', methods=['GET', 'POST'])
@admin_required
def edit_company(company_id):
    company = Company.query.get(company_id)
    if not company:
        flash('Company not found', 'danger')
        return redirect(url_for('admin.manage_companies'))
    
    if request.method == 'POST':
        company.company_name = request.form.get('company_name')
        company.email = request.form.get('email')
        company.hr_name = request.form.get('hr_name')
        company.hr_contact = request.form.get('hr_contact')
        company.website = request.form.get('website')
        company.description = request.form.get('description')
        
        db.session.commit()
        flash('Company profile updated successfully', 'success')
        return redirect(url_for('admin.manage_companies'))
        
    return render_template('admin/edit_company.html', company=company)

@admin_bp.route('/applications')
@admin_required
def manage_applications():
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    
    query = Application.query.join(Student).join(PlacementDrive).join(Company)
    
    if search:
        query = query.filter(
            (Student.full_name.ilike(f'%{search}%')) |
            (Student.roll_number.ilike(f'%{search}%')) |
            (PlacementDrive.job_title.ilike(f'%{search}%')) |
            (Company.company_name.ilike(f'%{search}%'))
        )
        
    if status:
        query = query.filter(Application.status == status)
        
    applications = query.all()
    return render_template('admin/manage_applications.html', applications=applications, search=search, status=status)


# ======================== COMPANY ROUTES ========================

@company_bp.route('/dashboard')
@company_required
def dashboard():
    company_id = session.get('user_id')
    company = Company.query.get(company_id)
    
    drives = PlacementDrive.query.filter_by(company_id=company_id).all()
    total_drives = len(drives)
    
    total_applications = Application.query.join(PlacementDrive).filter(
        PlacementDrive.company_id == company_id
    ).count()
    
    # Graphs Data
    drive_apps = db.session.query(PlacementDrive.job_title, db.func.count(Application.id)).outerjoin(Application).filter(PlacementDrive.company_id == company_id).group_by(PlacementDrive.id).all()
    drive_labels = [row[0] for row in drive_apps]
    drive_data = [row[1] for row in drive_apps]
    
    status_counts = db.session.query(Application.status, db.func.count(Application.id)).join(PlacementDrive).filter(PlacementDrive.company_id == company_id).group_by(Application.status).all()
    company_app_status_labels = [row[0] for row in status_counts]
    company_app_status_data = [row[1] for row in status_counts]
    
    return render_template('company/dashboard.html',
                          company=company,
                          total_drives=total_drives,
                          total_applications=total_applications,
                          drives=drives,
                          drive_labels=drive_labels,
                          drive_data=drive_data,
                          company_app_status_labels=company_app_status_labels,
                          company_app_status_data=company_app_status_data)

@company_bp.route('/create-drive', methods=['GET', 'POST'])
@company_required
def create_drive():
    company_id = session.get('user_id')
    company = Company.query.get(company_id)
    
    if company.approval_status != 'Approved':
        flash('Your company must be approved to create placement drives', 'danger')
        return redirect(url_for('company.dashboard'))
    
    if request.method == 'POST':
        job_title = request.form.get('job_title')
        job_description = request.form.get('job_description')
        eligibility_criteria = request.form.get('eligibility_criteria')
        ctc = request.form.get('ctc')
        positions = request.form.get('positions')
        application_deadline = request.form.get('application_deadline')
        
        try:
            deadline = datetime.strptime(application_deadline, '%Y-%m-%dT%H:%M')
            
            drive = PlacementDrive(
                company_id=company_id,
                job_title=job_title,
                job_description=job_description,
                eligibility_criteria=eligibility_criteria,
                ctc=float(ctc) if ctc else None,
                positions=int(positions) if positions else 1,
                application_deadline=deadline,
                status='Open',
                approval_status='Pending'
            )
            
            db.session.add(drive)
            db.session.commit()
            flash('Placement drive created successfully. Awaiting admin approval.', 'success')
            return redirect(url_for('company.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating drive: {str(e)}', 'danger')
    
    return render_template('company/create_drive.html')

@company_bp.route('/drives')
@company_required
def manage_drives():
    company_id = session.get('user_id')
    drives = PlacementDrive.query.filter_by(company_id=company_id).all()
    return render_template('company/manage_drives.html', drives=drives)

@company_bp.route('/edit-drive/<int:drive_id>', methods=['GET', 'POST'])
@company_required
def edit_drive(drive_id):
    company_id = session.get('user_id')
    drive = PlacementDrive.query.get(drive_id)
    
    if not drive or drive.company_id != company_id:
        flash('Drive not found', 'danger')
        return redirect(url_for('company.manage_drives'))
    
    if request.method == 'POST':
        drive.job_title = request.form.get('job_title')
        drive.job_description = request.form.get('job_description')
        drive.eligibility_criteria = request.form.get('eligibility_criteria')
        drive.ctc = float(request.form.get('ctc')) if request.form.get('ctc') else None
        drive.positions = int(request.form.get('positions')) if request.form.get('positions') else 1
        
        deadline_str = request.form.get('application_deadline')
        if deadline_str:
            try:
                drive.application_deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
            except:
                pass
        
        db.session.commit()
        flash('Drive updated successfully', 'success')
        return redirect(url_for('company.manage_drives'))
    
    return render_template('company/edit_drive.html', drive=drive)

@company_bp.route('/close-drive/<int:drive_id>', methods=['POST'])
@company_required
def close_drive(drive_id):
    company_id = session.get('user_id')
    drive = PlacementDrive.query.get(drive_id)
    
    if not drive or drive.company_id != company_id:
        return jsonify({'error': 'Drive not found'}), 404
    
    drive.status = 'Closed'
    db.session.commit()
    flash('Drive closed successfully', 'success')
    return redirect(url_for('company.manage_drives'))

@company_bp.route('/delete-drive/<int:drive_id>', methods=['POST'])
@company_required
def delete_drive(drive_id):
    company_id = session.get('user_id')
    drive = PlacementDrive.query.get(drive_id)
    
    if not drive or drive.company_id != company_id:
        return jsonify({'error': 'Drive not found'}), 404
    
    db.session.delete(drive)
    db.session.commit()
    flash('Drive deleted successfully', 'warning')
    return redirect(url_for('company.manage_drives'))

@company_bp.route('/applications/<int:drive_id>')
@company_required
def view_applications(drive_id):
    company_id = session.get('user_id')
    drive = PlacementDrive.query.get(drive_id)
    
    if not drive or drive.company_id != company_id:
        flash('Drive not found', 'danger')
        return redirect(url_for('company.dashboard'))
    
    applications = Application.query.filter_by(drive_id=drive_id).all()
    return render_template('company/view_applications.html', drive=drive, applications=applications)

@company_bp.route('/update-application/<int:app_id>/<status>', methods=['POST'])
@company_required
def update_application_status(app_id, status):
    company_id = session.get('user_id')
    app = Application.query.get(app_id)
    
    if not app or app.placement_drive.company_id != company_id:
        return jsonify({'error': 'Application not found'}), 404
    
    if status not in ['Applied', 'Shortlisted', 'Selected', 'Rejected']:
        return jsonify({'error': 'Invalid status'}), 400
    
    app.status = status
    db.session.commit()
    flash(f'Application status updated to {status}', 'success')
    return redirect(request.referrer or url_for('company.dashboard'))

# ======================== STUDENT ROUTES ========================

@student_bp.route('/dashboard')
@student_required
def dashboard():
    student_id = session.get('user_id')
    student = Student.query.get(student_id)
    
    my_applications = Application.query.filter_by(student_id=student_id).all()
    approved_drives = PlacementDrive.query.filter_by(approval_status='Approved', status='Open').count()
    
    # Graphs Data
    status_counts = db.session.query(Application.status, db.func.count(Application.id)).filter(Application.student_id == student_id).group_by(Application.status).all()
    student_app_status_labels = [row[0] for row in status_counts]
    student_app_status_data = [row[1] for row in status_counts]
    
    applied_drives = db.session.query(PlacementDrive.job_title, PlacementDrive.ctc).join(Application).filter(Application.student_id == student_id).all()
    ctc_labels = [row[0] for row in applied_drives]
    ctc_data = [row[1] if row[1] else 0 for row in applied_drives]
    
    return render_template('student/dashboard.html',
                          student=student,
                          my_applications=my_applications,
                          approved_drives=approved_drives,
                          student_app_status_labels=student_app_status_labels,
                          student_app_status_data=student_app_status_data,
                          ctc_labels=ctc_labels,
                          ctc_data=ctc_data)

@student_bp.route('/available-drives')
@student_required
def available_drives():
    student_id = session.get('user_id')
    
    # Get drives that are approved, open, and deadline not passed
    now = datetime.utcnow()
    drives = PlacementDrive.query.filter(
        PlacementDrive.approval_status == 'Approved',
        PlacementDrive.status == 'Open',
        PlacementDrive.application_deadline > now
    ).all()
    
    # Get already applied drives for this student
    applied_drive_ids = [app.drive_id for app in Application.query.filter_by(student_id=student_id).all()]
    
    return render_template('student/available_drives.html',
                          drives=drives,
                          applied_drive_ids=applied_drive_ids)

@student_bp.route('/apply-drive/<int:drive_id>', methods=['POST'])
@student_required
def apply_drive(drive_id):
    student_id = session.get('user_id')
    
    # Check if already applied
    existing_app = Application.query.filter_by(student_id=student_id, drive_id=drive_id).first()
    if existing_app:
        flash('You have already applied for this drive', 'warning')
        return redirect(url_for('student.available_drives'))
    
    # Check if drive exists and is open
    drive = PlacementDrive.query.get(drive_id)
    if not drive or drive.approval_status != 'Approved' or drive.status != 'Open':
        flash('This drive is not available', 'danger')
        return redirect(url_for('student.available_drives'))
    
    try:
        app = Application(
            student_id=student_id,
            drive_id=drive_id,
            status='Applied'
        )
        db.session.add(app)
        db.session.commit()
        flash(f'Applied successfully for {drive.job_title}', 'success')
    except:
        db.session.rollback()
        flash('Error applying for drive (may have already applied)', 'danger')
    
    return redirect(url_for('student.available_drives'))

@student_bp.route('/my-applications')
@student_required
def my_applications():
    student_id = session.get('user_id')
    applications = Application.query.filter_by(student_id=student_id).all()
    return render_template('student/my_applications.html', applications=applications)

@student_bp.route('/edit-profile', methods=['GET', 'POST'])
@student_required
def edit_profile():
    student_id = session.get('user_id')
    student = Student.query.get(student_id)
    
    if request.method == 'POST':
        student.full_name = request.form.get('full_name')
        student.email = request.form.get('email')
        student.phone = request.form.get('phone')
        student.cgpa = float(request.form.get('cgpa')) if request.form.get('cgpa') else student.cgpa
        student.branch = request.form.get('branch')
        student.semester = int(request.form.get('semester')) if request.form.get('semester') else student.semester
        
        # Handle resume upload
        if 'resume' in request.files:
            file = request.files['resume']
            if file and allowed_file(file.filename):
                import os
                from flask import current_app
                filename = secure_filename(f"{student.roll_number}_{file.filename}")
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                student.resume_path = filename
            elif file:
                flash('Invalid file format. Please upload PDF, DOC, or DOCX', 'warning')
        
        db.session.commit()
        session['name'] = student.full_name
        flash('Profile updated successfully', 'success')
        return redirect(url_for('student.dashboard'))
    
    return render_template('student/edit_profile.html', student=student)

@student_bp.route('/download-resume/<int:student_id>')
@company_required
def download_resume(student_id):
    student = Student.query.get(student_id)
    if not student or not student.resume_path:
        flash('Resume not found', 'danger')
        return redirect(request.referrer)
    
    from flask import send_from_directory, current_app
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], student.resume_path)
