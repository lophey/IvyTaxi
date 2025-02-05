from flask_login import UserMixin
from sqlalchemy.orm import validates

import re
from datetime import date

from package import db


class Driver(db.Model, UserMixin):
    __tablename__ = 'driver'

    driver_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    country_id = db.Column(db.Integer, db.ForeignKey('country.country_id'), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False, unique=True)
    date_of_birth = db.Column(db.Date, nullable=False)
    sex = db.Column(db.Boolean, nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    registration_date = db.Column(db.Date, nullable=False, default=date.today)
    drivers_license_number = db.Column(db.String(12), nullable=False, unique=True)
    passport_id = db.Column(db.String(12), nullable=False, unique=True)
    driver_role = db.Column(db.String(6), nullable=False)

    # __table_args__ = (
    #     db.CheckConstraint("name ~ '^[A-Za-z]{3,30}$'", name='driver_name_check'),
    #     db.CheckConstraint("surname ~ '^[A-Za-z]{3,30}$'", name='driver_surname_check'),
    #     db.CheckConstraint("phone_number ~ '^[0-9]{10,20}$'", name='driver_phone_number_check'),
    #     db.CheckConstraint("EXTRACT(year FROM age(CURRENT_DATE, date_of_birth)) >= 18", name='driver_date_of_birth_check'),
    #     db.CheckConstraint("email ~ '[a-z0-9._%-]+@[a-z0-9._%-]+\.[a-z]{2,4}'", name='driver_email_check'),
    #     db.CheckConstraint("drivers_license_number ~ '[A-Za-z0-9]{4,12}'", name='driver_drivers_license_number_check'),
    #     db.CheckConstraint("passport_id ~ '[A-Za-z0-9]{4,12}'", name='driver_passport_id_check'),
    # )

    def get_id(self):
        return str(self.driver_id)

    @validates('name')
    def validate_name(self, key, value):
        if not re.match('^[A-Za-z]{3,30}$', value):
            raise ValueError("Invalid name format")
        return value

    @validates('surname')
    def validate_surname(self, key, value):
        if not re.match('^[A-Za-z]{3,30}$', value):
            raise ValueError("Invalid surname format")
        return value

    @validates('phone_number')
    def validate_phone_number(self, key, value):
        if not re.match('^[0-9]{10,20}$', value):
            raise ValueError("Invalid phone number format")
        return value

    @validates('date_of_birth')
    def validate_date_of_birth(self, key, value):
        if (date.today().year - value.year) < 18:
            raise ValueError("Driver must be at least 18 years old")
        return value

    @validates('email')
    def validate_email(self, key, value):
        if not re.match('[a-z0-9._%-]+@[a-z0-9._%-]+\.[a-z]{2,4}', value):
            raise ValueError("Invalid email format")
        return value

    @validates('drivers_license_number')
    def validate_drivers_license_number(self, key, value):
        if not re.match('[A-Za-z0-9]{4,12}', value):
            raise ValueError("Invalid drivers license number format")
        return value

    @validates('passport_id')
    def validate_passport_id(self, key, value):
        if not re.match('[A-Za-z0-9]{4,12}', value):
            raise ValueError("Invalid passport ID format")
        return value


class DriverAuthentication(db.Model, UserMixin):
    __tablename__ = 'driverauthentication'

    driver_id = db.Column(db.Integer, db.ForeignKey('driver.driver_id', onupdate="NO ACTION",
                                                    ondelete="SET NULL"), primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False, unique=True)
    token = db.Column(db.String(165), nullable=False, unique=True)

    def get_id(self):
        return str(self.driver_id)

    # __table_args__ = (
    #     db.CheckConstraint("phone_number ~ '^[0-9]{10,20}$'", name='authentication_phone_number_check'),
    # )

    driver = db.relationship('Driver', backref=db.backref('authentications', lazy=True))

    @validates('phone_number')
    def validate_phone_number(self, key, value):
        if not re.match('^[0-9]{10,20}$', value):
            raise ValueError("Invalid phone number format")
        return value

    @validates('token')
    def validate_token(self, key, value):
        if not value:
            raise ValueError("Token cannot be empty")
        return value


class DriverVehicle(db.Model):
    __tablename__ = 'driver_vehicle'

    driver_id = db.Column(db.Integer, db.ForeignKey('driver.driver_id', ondelete='SET NULL'), primary_key=True, nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.vehicle_id', ondelete='SET NULL'), primary_key=True, nullable=False, unique=True)

    driver = db.relationship('Driver', backref=db.backref('vehicles', lazy=True))
    vehicle = db.relationship('Vehicle',   backref=db.backref('driver', cascade='all, delete-orphan', lazy=True), single_parent=True)
