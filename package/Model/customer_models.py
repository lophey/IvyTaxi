from flask_login import UserMixin
from sqlalchemy.orm import validates

import re

from package import db


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


class CustomerAuthentication(db.Model, UserMixin):
    __tablename__ = 'customerauthentication'

    customer_id = db.Column(db.Integer, db.ForeignKey('customer.customer_id', onupdate="NO ACTION",
                                                      ondelete="SET NULL"), primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False, unique=True)
    token = db.Column(db.String(165), nullable=False, unique=True)

    def get_id(self):
        return str(self.customer_id)

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


class Payment(db.Model):
    __tablename__ = 'payment'

    payment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    method_id = db.Column(db.Integer, db.ForeignKey('payment_method.method_id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.customer_id'), nullable=False)
    card_number = db.Column(db.String(19), unique=True, nullable=True)
    date_of_expiry = db.Column(db.Date, nullable=True)
    cvv = db.Column(db.String(3), nullable=True)

    __table_args__ = (
        db.CheckConstraint("card_number ~ '^[0-9]{12,19}$'", name='card_number_check'),
        db.CheckConstraint("cvv ~ '^[0-9]{3}$'", name='cvv_check'),
        db.CheckConstraint(
            "(method_id = 2 AND card_number IS NULL AND date_of_expiry IS NULL AND cvv IS NULL) OR "
            "(method_id = 1 AND card_number IS NOT NULL AND date_of_expiry IS NOT NULL AND cvv IS NOT NULL)",
            name='method_id_check'
        ),
    )

