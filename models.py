from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100))
    contact = db.Column(db.String(20))
    status = db.Column(db.String(20), default='pending')

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='Active')

class Examination(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    exam_type = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    max_marks = db.Column(db.Integer, nullable=False)
    slot_creation_start = db.Column(db.String(20))
    slot_creation_end = db.Column(db.String(20))
    booking_start = db.Column(db.String(20))
    booking_end = db.Column(db.String(20))
    status = db.Column(db.String(30), default='Draft')
    course = db.relationship('Course', backref=db.backref('examinations', lazy=True))

class Rubric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    examination_id = db.Column(db.Integer, db.ForeignKey('examination.id'), nullable=False)
    criterion_name = db.Column(db.String(100), nullable=False)
    max_marks = db.Column(db.Integer, nullable=False)
    weightage = db.Column(db.Float, nullable=False, default=1.0)
    description = db.Column(db.Text)
    examination = db.relationship('Examination', backref=db.backref('rubrics', lazy=True, cascade='all, delete-orphan'))

class Slot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    examination_id = db.Column(db.Integer, db.ForeignKey('examination.id'), nullable=False)
    examiner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.String(20), nullable=False)
    end_time = db.Column(db.String(20), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    available_seats = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Available')
    examination = db.relationship('Examination', backref=db.backref('slots', lazy=True))
    examiner = db.relationship('User', backref=db.backref('slots', lazy=True))

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('slot.id'), nullable=False)
    booking_date = db.Column(db.String(30), default=datetime.utcnow)
    status = db.Column(db.String(20), default='Booked')
    marks = db.Column(db.Float, nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    student = db.relationship('User', backref=db.backref('bookings', lazy=True))
    slot = db.relationship('Slot', backref=db.backref('bookings', lazy=True))

class RubricScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    rubric_id = db.Column(db.Integer, db.ForeignKey('rubric.id'), nullable=False)
    marks_awarded = db.Column(db.Float, nullable=False, default=0.0)
    booking = db.relationship('Booking', backref=db.backref('rubric_scores', lazy=True, cascade='all, delete-orphan'))
    rubric = db.relationship('Rubric', backref=db.backref('scores', lazy=True))