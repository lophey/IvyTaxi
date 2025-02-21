from sqlalchemy.orm import validates

import re

from package import db


class Customer(db.Model):
    __tablename__ = 'customer'

    customer_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    customer_role = db.Column(db.String(8), nullable=False)

    customer_addresses = db.relationship('CustomerAddress', back_populates='customer')

    __table_args__ = (
        db.CheckConstraint("name ~ '^[А-Яа-яЁёІіЇїЄєҐґA-za-z]{3,30}$'", name='customer_name_check'),
        db.CheckConstraint("surname ~ '^[А-Яа-яЁёІіЇїЄєҐґA-za-z]{3,30}$'", name='customer_surname_check'),
        db.CheckConstraint("phone_number ~ '^[0-9]{10,20}$'", name='customer_phone_number_check'),
        db.CheckConstraint("email ~ '[a-z0-9._%-]+@[a-z0-9._%-]+\.[a-z]{2,4}'", name='customer_email_check'),
    )

    def get_id(self):
        return str(self.customer_id)

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

    @validates('phone_number')
    def validate_phone_number(self, key, value):
        if not re.match('^[0-9]{10,20}$', value):
            raise ValueError("Невірний формат номеру телефону")
        return value

    @validates('email')
    def validate_phone_number(self, key, value):
        if not re.match('[a-z0-9._%-]+@[a-z0-9._%-]+\.[a-z]{2,4}$', value):
            raise ValueError("Невірний формат електронної пошти")
        return value


class Address(db.Model):
    __tablename__ = 'address'

    address_id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    city_id = db.Column(db.Integer, db.ForeignKey('city.city_id', onupdate="NO ACTION",
                                                  ondelete="SET NULL"), nullable=False)
    street = db.Column(db.String(100), nullable=False)
    house_number = db.Column(db.String(10), nullable=False)

    city = db.relationship('City', backref=db.backref('address', lazy=True))
    customers = db.relationship('CustomerAddress', back_populates='address')

    __table_args__ = (
        db.CheckConstraint("street ~ '^[А-Яа-яЁёІіЇїЄєҐґ ]{3,100}$'", name='customer_name_check'),
        db.CheckConstraint("house_number ~ '^[А-Яа-яЁёІіЇїЄєҐґ0-9/-]{1,10}$'", name='customer_surname_check'),
    )

    def get_id(self):
        return str(self.customer_id)

    @validates('street')
    def validate_name(self, key, value):
        if not re.match('^[А-Яа-яЁёІіЇїЄєҐґ ]{3,100}$', value):
            raise ValueError("Некоректний формат вулиці")
        return value

    @validates('house_number')
    def validate_name(self, key, value):
        if not re.match('^[А-Яа-яЁёІіЇїЄєҐґ0-9/-]{1,10}$', value):
            raise ValueError("Некоректний формат номера дому")
        return value


class CustomerAddress(db.Model):
    __tablename__ = 'customer_address'
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.customer_id', ondelete='SET NULL'), primary_key=True)
    address_id = db.Column(db.Integer, db.ForeignKey('address.address_id', ondelete='SET NULL'), primary_key=True)

    customer = db.relationship(Customer, back_populates='customer_addresses')
    address = db.relationship(Address, back_populates='customers')


class Payment(db.Model):
    __tablename__ = 'payment'

    payment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    method_id = db.Column(db.Integer, db.ForeignKey('payment_method.method_id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.customer_id'), nullable=False)
    card_number = db.Column(db.String(19), unique=True, nullable=True)

    __table_args__ = (
        db.CheckConstraint("card_number ~ '^[0-9]{12,19}$'", name='card_number_check'),
    )

    @validates('card_number')
    def validate_name(self, key, value):
        if not re.match('^[0-9]{12,19}$', value):
            raise ValueError("Некоректний формат банківської картки")
        return value
