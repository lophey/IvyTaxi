from flask_login import UserMixin
from sqlalchemy.orm import validates

import re

from package import db


class Admin(db.Model, UserMixin):
    __tablename__ = 'administrator'

    administrator_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    administrator_role = db.Column(db.String(13), nullable=False)

    __table_args__ = (
        db.CheckConstraint("name ~ '^[А-Яа-яЁёІіЇїЄєҐґA-za-z]{3,30}$'", name='customer_name_check'),
        db.CheckConstraint("surname ~ '^[А-Яа-яЁёІіЇїЄєҐґA-za-z]{3,30}$'", name='customer_surname_check'),
        db.CheckConstraint("email ~ '[a-z0-9._%-]+@[a-z0-9._%-]+\.[a-z]{2,4}'", name='customer_email_check'),
    )

    def get_id(self):
        return str(self.administrator_id)

    @validates('name')
    def validate_name(self, key, value):
        if not re.match('^[А-Яа-яЁёІіЇїЄєҐґA-za-z]{3,30}$', value):
            raise ValueError("Невірний формат імені")
        return value

    @validates('surname')
    def validate_surname(self, key, value):
        if not re.match('^[А-Яа-яЁёІіЇїЄєҐґA-za-z]{3,30}$', value):
            raise ValueError("Невірний формат прізвища")
        return value

    @validates('email')
    def validate_phone_number(self, key, value):
        if not re.match('[a-z0-9._%-]+@[a-z0-9._%-]+\.[a-z]{2,4}$', value):
            raise ValueError("Невірний формат електронної пошти")
        return value


class BlockedUsers(db.Model):
    __tablename__ = 'blocked_users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    administrator_id = db.Column(db.Integer, db.ForeignKey('administrator.administrator_id'), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)  # ID пользователя или водителя
    user_type = db.Column(db.String(10), nullable=False)  # Тип пользователя: 'customer' или 'driver'
    block_reason = db.Column(db.String(255), nullable=False)
    blocked_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)

    administrator = db.relationship('Admin', backref=db.backref('blocked_users', lazy=True))