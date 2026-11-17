from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Course, Examination, Rubric, Slot, Booking, RubricScore
from datetime import date, datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'emp_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        hashed_password = generate_password_hash('adminpassword', method='pbkdf2:sha256')
        admin_user = User(email='admin@emp.com', password=hashed_password, role='admin', name='Super Admin', status='approved')
        db.session.add(admin_user)
        db.session.commit()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            if user.role == 'examiner' and user.status != 'approved':
                flash('Your account is pending admin approval.', 'warning')
                return redirect(url_for('login'))
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'examiner':
                return redirect(url_for('examiner_dashboard'))
            elif user.role == 'student':
                return redirect(url_for('student_dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = generate_password_hash(request.form.get('password'), method='pbkdf2:sha256')
        role = request.form.get('role')
        department = request.form.get('department')
        contact = request.form.get('contact')
        
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
            
        status = 'pending' if role == 'examiner' else 'approved'
        user = User(name=name, email=email, password=password, role=role, department=department, contact=contact, status=status)
        db.session.add(user)
        db.session.commit()
        
        if role == 'examiner':
            flash('Registration successful! Waiting for admin approval.', 'success')
        else:
            flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    update_exam_status() 
    courses_count = Course.query.count()
    exams_count = Examination.query.count()
    examiners_count = User.query.filter_by(role='examiner').count()
    students_count = User.query.filter_by(role='student').count()
    slots_count = Slot.query.count()
    bookings_count = Booking.query.count()
    search_query = request.args.get('q', '')
    students, examiners, examinations, bookings = [], [], [], []
    if search_query:
        students = User.query.filter(User.role == 'student', User.name.ilike(f'%{search_query}%')).all()
        examiners = User.query.filter(User.role == 'examiner', User.name.ilike(f'%{search_query}%')).all()
        examinations = Examination.query.filter(Examination.name.ilike(f'%{search_query}%')).all()
    else:
        students = User.query.filter_by(role='student').all()
        examiners = User.query.filter_by(role='examiner').all()
        examinations = Examination.query.all()
        bookings = Booking.query.all()
        
    return render_template('admin/dashboard.html', 
                           courses_count=courses_count, exams_count=exams_count,
                           examiners_count=examiners_count, students_count=students_count,
                           slots_count=slots_count, bookings_count=bookings_count,
                           students=students, examiners=examiners, examinations=examinations, bookings=bookings)

@app.route('/admin/courses', methods=['GET', 'POST'])
@login_required
def manage_courses():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    if request.method == 'POST':
        code = request.form.get('course_code')
        name = request.form.get('course_name')
        desc = request.form.get('description')
        course = Course(course_code=code, course_name=name, description=desc)
        db.session.add(course)
        db.session.commit()
        flash('Course added successfully.', 'success')
        return redirect(url_for('manage_courses'))
    courses = Course.query.all()
    return render_template('admin/manage_courses.html', courses=courses)

@app.route('/admin/courses/delete/<int:id>')
@login_required
def delete_course(id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    course = Course.query.get_or_404(id)
    db.session.delete(course)
    db.session.commit()
    flash('Course deleted.', 'success')
    return redirect(url_for('manage_courses'))

@app.route('/admin/examinations', methods=['GET', 'POST'])
@login_required
def manage_exams():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        name = request.form.get('name')
        exam_type = request.form.get('exam_type')
        duration = request.form.get('duration')
        max_marks = request.form.get('max_marks')
        s_start = request.form.get('slot_creation_start')
        s_end = request.form.get('slot_creation_end')
        b_start = request.form.get('booking_start')
        b_end = request.form.get('booking_end')
                
        exam = Examination(course_id=course_id, name=name, exam_type=exam_type, duration=duration, max_marks=max_marks,
                           slot_creation_start=s_start, slot_creation_end=s_end, booking_start=b_start, booking_end=b_end, status='Draft')
        db.session.add(exam)
        db.session.commit()

        criterion_names = request.form.getlist('criterion_name[]')
        criterion_max_marks = request.form.getlist('criterion_max_marks[]')
        criterion_descs = request.form.getlist('criterion_desc[]')

        for i in range(len(criterion_names)):
            if criterion_names[i].strip():
                rubric = Rubric(
                    examination_id=exam.id,
                    criterion_name=criterion_names[i],
                    max_marks=float(criterion_max_marks[i]),
                    description=criterion_descs[i] if i < len(criterion_descs) else ''
                )
                db.session.add(rubric)
        db.session.commit()

        flash('Examination and rubrics created successfully.', 'success')
        update_exam_status()
        return redirect(url_for('manage_exams'))

    update_exam_status()
    examinations = Examination.query.all()
    courses = Course.query.all()
    return render_template('admin/manage_exams.html', examinations=examinations, courses=courses)

@app.route('/admin/examinations/status/<int:id>/<status>')
@login_required
def update_exam_status(id, status):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    exam = Examination.query.get_or_404(id)
    exam.status = status
    db.session.commit()
    flash(f'Examination status updated to {status}', 'success')
    return redirect(url_for('manage_exams'))

@app.route('/admin/examiners')
@login_required
def manage_examiners():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    examiners = User.query.filter_by(role='examiner').all()
    return render_template('admin/manage_examiners.html', examiners=examiners)

@app.route('/admin/examinations/update_times/<int:id>', methods=['POST'])
@login_required
def update_exam_times(id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    exam = Examination.query.get_or_404(id)
    exam.slot_creation_start = request.form.get('slot_creation_start')
    exam.slot_creation_end = request.form.get('slot_creation_end')
    exam.booking_start = request.form.get('booking_start')
    exam.booking_end = request.form.get('booking_end')
    
    db.session.commit()
    update_exam_status()
    flash('Examination dates and times updated successfully.', 'success')
    return redirect(url_for('manage_exams'))

def update_exam_status():
    current_date = date.today()
    examinations = Examination.query.all()

    for exam in examinations:
        if exam.slot_creation_start and exam.slot_creation_end:
            a = datetime.strptime(exam.slot_creation_start, "%Y-%m-%d").date()
            b = datetime.strptime(exam.slot_creation_end, "%Y-%m-%d").date()
        else:
            a, b = None, None
        if exam.booking_start and exam.booking_end:
            c = datetime.strptime(exam.booking_start, "%Y-%m-%d").date()
            d = datetime.strptime(exam.booking_end, "%Y-%m-%d").date()
        else:
            c, d = None, None
        if a and b and (a <= current_date <= b):
            exam.status = "Slot Creation"
        elif c and d and (c <= current_date <= d):
            exam.status = "Booking Open"
        else:
            exam.status = "Draft"

    db.session.commit()

@app.route('/admin/examiners/approve/<int:id>')
@login_required
def approve_examiner(id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    examiner = User.query.get_or_404(id)
    examiner.status = 'approved'
    db.session.commit()
    flash('Examiner approved.', 'success')
    return redirect(url_for('manage_examiners'))

@app.route('/admin/examiners/deactivate/<int:id>')
@login_required
def deactivate_examiner(id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    examiner = User.query.get_or_404(id)
    examiner.status = 'deactivated'
    db.session.commit()
    flash('Examiner deactivated.', 'warning')
    return redirect(url_for('manage_examiners'))

@app.route('/admin/dashboard/approve/<int:id>')
@login_required
def approve_student(id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    student = User.query.get_or_404(id)
    student.status = 'approved'
    db.session.commit()
    flash('Student approved.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/dashboard/deactivate/<int:id>')
@login_required
def deactivate_student(id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    student = User.query.get_or_404(id)
    student.status = 'deactivated'
    db.session.commit()
    flash('Student deactivated.', 'warning')
    return redirect(url_for('admin_dashboard'))

@app.route('/examiner/dashboard')
@login_required
def examiner_dashboard():
  if current_user.role != 'examiner':
    return redirect(url_for('login'))

  update_exam_status()

  slots = Slot.query.filter_by(examiner_id=current_user.id).all()
  current_dt = datetime.now()
  for s in slots:
    if s.status != 'Full':
      try:
        slot_end_dt = datetime.strptime(f'{s.date} {s.end_time}', '%Y-%m-%d %H:%M')
        if current_dt > slot_end_dt:
          s.status = 'Not Available'
        else:
          s.status = 'Available'
      except ValueError:
        slot_date = datetime.strptime(s.date, '%Y-%m-%d').date()
        if date.today() > slot_date:
          s.status = 'Not Available'
        else:
          s.status = 'Available'
  db.session.commit()

  examinations = Examination.query.filter(
      Examination.status.in_(
          ['Slot Creation', 'Booking Open', 'Closed', 'Completed']
      )
  ).all()
  return render_template(
      'examiner/dashboard.html', examinations=examinations, slots=slots
  )

@app.route('/examiner/slot/create', methods=['GET', 'POST'])
@login_required
def create_slot():
    if current_user.role != 'examiner':
        return redirect(url_for('login'))
    if request.method == 'POST':
        exam_id = request.form.get('examination_id')
        date = request.form.get('date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        capacity = int(request.form.get('capacity'))
        exam = Examination.query.get_or_404(exam_id)
        if exam.status != 'Slot Creation':
            flash('Slot creation is not active for this examination.', 'danger')
            return redirect(url_for('create_slot'))
            
        slot = Slot(examination_id=exam_id, examiner_id=current_user.id, date=date, start_time=start_time, end_time=end_time, capacity=capacity, available_seats=capacity)
        db.session.add(slot)
        db.session.commit()
        flash('Slot created successfully.', 'success')
        return redirect(url_for('examiner_dashboard'))
    examinations = Examination.query.filter_by(status='Slot Creation').all()
    return render_template('examiner/create_slot.html', examinations=examinations)

@app.route('/examiner/evaluate', methods=['GET', 'POST'])
@login_required
def evaluate_student():
  if current_user.role != 'examiner':
    return redirect(url_for('login'))

  examiner_exams = (
      Examination.query.join(Slot)
      .filter(Slot.examiner_id == current_user.id)
      .distinct()
      .all()
  )

  booking = None
  rubrics = []
  existing_scores = {}
  student_id = request.form.get('student_id') or request.args.get('student_id')
  exam_id = request.form.get('examination_id') or request.args.get(
      'examination_id'
  )

  if request.method == 'POST' and 'load_student' in request.form:
    if student_id and exam_id:
      booking = (
          Booking.query.join(Slot)
          .filter(
              Booking.student_id == int(student_id),
              Slot.examination_id == int(exam_id),
              Slot.examiner_id == current_user.id,
          )
          .first()
      )

      if not booking or booking.status == 'Cancelled':
        flash('Student does not write exam', 'danger')
        booking = None
      else:
        try:
          slot_end_dt = datetime.strptime(
              f'{booking.slot.date} {booking.slot.end_time}', '%Y-%m-%d %H:%M'
          )
          if datetime.now() < slot_end_dt:
            flash(
                'Examination is not completed yet. You cannot evaluate before'
                ' the exam finishes.',
                'warning',
            )
            booking = None
          else:
            rubrics = booking.slot.examination.rubrics
            existing_scores = {
                score.rubric_id: score.marks_awarded
                for score in booking.rubric_scores
            }
        except ValueError:
          slot_date = datetime.strptime(booking.slot.date, '%Y-%m-%d').date()
          if date.today() < slot_date:
            flash(
                'Examination is not completed yet. You cannot evaluate before'
                ' the exam finishes.',
                'warning',
            )
            booking = None
          else:
            rubrics = booking.slot.examination.rubrics
            existing_scores = {
                score.rubric_id: score.marks_awarded
                for score in booking.rubric_scores
            }

  if request.method == 'POST' and 'submit_evaluation' in request.form:
    booking_id = request.form.get('booking_id')
    booking = Booking.query.get_or_404(booking_id)
    rubrics = booking.slot.examination.rubrics

    total_marks = 0.0
    for rubric in rubrics:
      marks_val = float(request.form.get(f'rubric_{rubric.id}', 0))
      total_marks += marks_val

      existing_score = RubricScore.query.filter_by(
          booking_id=booking.id, rubric_id=rubric.id
      ).first()
      if existing_score:
        existing_score.marks_awarded = marks_val
      else:
        score = RubricScore(
            booking_id=booking.id, rubric_id=rubric.id, marks_awarded=marks_val
        )
        db.session.add(score)

    booking.marks = total_marks
    booking.remarks = request.form.get('remarks')
    booking.status = 'Completed'
    db.session.commit()
    flash('Evaluation submitted successfully.', 'success')
    return redirect(url_for('examiner_dashboard'))

  return render_template(
      'examiner/evaluate.html',
      examiner_exams=examiner_exams,
      booking=booking,
      rubrics=rubrics,
      existing_scores=existing_scores,
      student_id=student_id,
      exam_id=exam_id,
    )

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('login'))

    update_exam_status() 

    search = request.args.get('search', '')
    exam_type = request.args.get('exam_type', '')
    
    query = Examination.query.filter_by(status='Booking Open')
    if search:
        query = query.filter(Examination.name.ilike(f'%{search}%'))
    if exam_type:
        query = query.filter_by(exam_type=exam_type)
        
    available_exams = query.all()
    my_bookings = Booking.query.filter_by(student_id=current_user.id).all()
    return render_template('student/dashboard.html', available_exams=available_exams, my_bookings=my_bookings)

@app.route('/student/book/<int:exam_id>')
@login_required
def book_slot_page(exam_id):
    if current_user.role != 'student':
        return redirect(url_for('login'))
    exam = Examination.query.get_or_404(exam_id)
    slots = Slot.query.filter_by(examination_id=exam_id, status='Available').all()
    return render_template('student/book_slot.html', exam=exam, slots=slots)

@app.route('/student/book/confirm/<int:slot_id>')
@login_required
def confirm_booking(slot_id):
    if current_user.role != 'student':
        return redirect(url_for('login'))
    slot = Slot.query.get_or_404(slot_id)
    
    existing = Booking.query.join(Slot).filter(Booking.student_id == current_user.id, Slot.examination_id == slot.examination_id, Booking.status == 'Booked').first()
    if existing:
        flash('You already have an active booking for this examination.', 'danger')
        return redirect(url_for('student_dashboard'))
        
    if slot.available_seats > 0:
        booking = Booking(student_id=current_user.id, slot_id=slot.id, status='Booked')
        slot.available_seats -= 1
        if slot.available_seats == 0:
            slot.status = 'Full'
        db.session.add(booking)
        db.session.commit()
        flash('Slot booked successfully!', 'success')
    else:
        flash('Slot is full.', 'danger')
    return redirect(url_for('student_dashboard'))

@app.route('/student/cancel/<int:booking_id>')
@login_required
def cancel_booking(booking_id):
    if current_user.role != 'student':
        return redirect(url_for('login'))
    booking = Booking.query.get_or_404(booking_id)
    if booking.student_id == current_user.id and booking.status == 'Booked':
        booking.status = 'Cancelled'
        slot = booking.slot
        slot.available_seats += 1
        if slot.status == 'Full':
            slot.status = 'Available'
        db.session.commit()
        flash('Booking cancelled.', 'success')
    return redirect(url_for('student_dashboard'))

@app.route('/student/results')
@login_required
def student_results():
    if current_user.role != 'student':
        return redirect(url_for('login'))
    completed_bookings = Booking.query.filter_by(student_id=current_user.id, status='Completed').all()
    return render_template('student/results.html', completed_bookings=completed_bookings)

if __name__ == '__main__':
    app.run(debug=True)