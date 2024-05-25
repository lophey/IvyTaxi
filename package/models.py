from flask_login import UserMixin
from sqlalchemy.orm import validates
from werkzeug.security import generate_password_hash, check_password_hash

import re
from datetime import date

from package import db, login_manager


class CustomerRegister(db.Model, UserMixin):
    __tablename__ = 'customer'

    customer_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    customer_addresses = db.relationship('CustomerAddress', back_populates='customer')

    __table_args__ = (
        db.CheckConstraint("name ~ '^[A-Za-z]{3,30}$'", name='customer_name_check'),
        db.CheckConstraint("surname ~ '^[A-Za-z]{3,30}$'", name='customer_surname_check'),
        db.CheckConstraint("phone_number ~ '^[0-9]{10,20}$'", name='customer_phone_number_check'),
        db.CheckConstraint("email ~ '[a-z0-9._%-]+@[a-z0-9._%-]+\.[a-z]{2,4}'", name='customer_email_check'),
    )

    def get_id(self):
        return str(self.customer_id)

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


class Country(db.Model, UserMixin):
    __tablename__ = 'country'
    country_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False, unique=True)

    __table_args__ = (
        db.CheckConstraint("name ~ '^[A-Za-z ]{2,60}$'", name='country_name_check'),
    )

    @validates('name')
    def validate_surname(self, key, value):
        if not re.match('^[A-Za-z ]{2,60}$', value):
            raise ValueError("Invalid surname format")
        return value


class DriverRegister(db.Model, UserMixin):
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

    __table_args__ = (
        db.CheckConstraint("name ~ '^[A-Za-z]{3,30}$'", name='driver_name_check'),
        db.CheckConstraint("surname ~ '^[A-Za-z]{3,30}$'", name='driver_surname_check'),
        db.CheckConstraint("phone_number ~ '^[0-9]{10,20}$'", name='driver_phone_number_check'),
        db.CheckConstraint("EXTRACT(year FROM age(CURRENT_DATE, date_of_birth)) >= 18", name='driver_date_of_birth_check'),
        db.CheckConstraint("email ~ '[a-z0-9._%-]+@[a-z0-9._%-]+\.[a-z]{2,4}'", name='driver_email_check'),
        db.CheckConstraint("drivers_license_number ~ '[A-Za-z0-9]{4,12}'", name='driver_drivers_license_number_check'),
        db.CheckConstraint("passport_id ~ '[A-Za-z0-9]{4,12}'", name='driver_passport_id_check'),
    )

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


class CustomerAuthentication(db.Model, UserMixin):
    __tablename__ = 'customerauthentication'

    customer_id = db.Column(db.Integer, db.ForeignKey('customer.customer_id', onupdate="NO ACTION",
                                                      ondelete="SET NULL"), primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False, unique=True)
    token = db.Column(db.String(165), nullable=False, unique=True)

    def get_id(self):
        return str(self.customer_id)

    def set_password(self, password):
        self.token = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.token, password)

    __table_args__ = (
        db.CheckConstraint("phone_number ~ '^[0-9]{10,20}$'", name='authentication_phone_number_check'),
    )

    customer = db.relationship('CustomerRegister', backref=db.backref('authentications', lazy=True))

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


class DriverAuthentication(db.Model, UserMixin):
    __tablename__ = 'driverauthentication'

    driver_id = db.Column(db.Integer, db.ForeignKey('driver.driver_id', onupdate="NO ACTION",
                                                      ondelete="SET NULL"), primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False, unique=True)
    token = db.Column(db.String(165), nullable=False, unique=True)

    def get_id(self):
        return str(self.driver_id)

    def set_password(self, password):
        self.token = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.token, password)

    __table_args__ = (
        db.CheckConstraint("phone_number ~ '^[0-9]{10,20}$'", name='authentication_phone_number_check'),
    )

    driver = db.relationship('DriverRegister', backref=db.backref('authentications', lazy=True))

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


class Address(db.Model, UserMixin):
    __tablename__ = 'address'

    address_id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    city_id = db.Column(db.Integer, db.ForeignKey('city.city_id', onupdate="NO ACTION",
                                                  ondelete="SET NULL"), nullable=False )
    street = db.Column(db.String(100), nullable=False)
    house_number = db.Column(db.String(10), nullable=False)

    city = db.relationship('City', backref=db.backref('address', lazy=True))
    customers = db.relationship('CustomerAddress', cascade='all, delete-orphan', back_populates='address')


class CustomerAddress(db.Model, UserMixin):
    __tablename__ = 'customer_address'
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.customer_id', ondelete='SET NULL'), primary_key=True)
    address_id = db.Column(db.Integer, db.ForeignKey('address.address_id', ondelete='SET NULL'), primary_key=True)
    order = db.Column(db.Integer, nullable=False)

    customer = db.relationship(CustomerRegister, back_populates='customer_addresses')
    address = db.relationship(Address, back_populates='customers')


class City(db.Model, UserMixin):
    __tablename__ = 'city'

    city_id = db.Column(db.Integer, primary_key=True)
    country_id = db.Column(db.Integer, nullable=False)
    city_name = db.Column(db.String(168), nullable=False)

    __table_args__ = (
        db.CheckConstraint("city_name ~ '[A-Za-z]{3,168}'", name='city_city_name_check'),
    )




@login_manager.user_loader
def load_customer(customer_id):
    return CustomerAuthentication.query.get(customer_id)


def load_driver(driver_id):
    return DriverAuthentication.query.get(driver_id)

