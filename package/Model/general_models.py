from flask_login import UserMixin
from sqlalchemy.orm import validates

import re

from package import db


class Country(db.Model, UserMixin):
    __tablename__ = 'country'
    country_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False, unique=True)

    __table_args__ = (
        db.CheckConstraint("name ~ '^[A-za-zА-Яа-яЁёІіЇїЄєҐґ ]{2,60}$'", name='country_name_check'),
    )

    @validates('name')
    def validate_surname(self, key, value):
        if not re.match('^[A-za-zА-Яа-яЁёІіЇїЄєҐґ ]{2,60}$', value):
            raise ValueError("Невірний формат назви країни")
        return value


class City(db.Model, UserMixin):
    __tablename__ = 'city'

    city_id = db.Column(db.Integer, primary_key=True)
    country_id = db.Column(db.Integer, nullable=False)
    city_name = db.Column(db.String(168), nullable=False)

    __table_args__ = (
        db.CheckConstraint("city_name ~ '[A-za-zА-Яа-яЁёІіЇїЄєҐґ ]{3,168}'", name='city_city_name_check'),
    )

    @validates('city_name')
    def validate_surname(self, key, value):
        if not re.match('[A-za-zА-Яа-яЁёІіЇїЄєҐґ ]{3,168}', value):
            raise ValueError("Невірний формат назви міста")
        return value


class PaymentMethod(db.Model):
    __tablename__ = 'payment_method'

    method_id = db.Column(db.Integer, primary_key=True, nullable=False)
    method_name = db.Column(db.String(6), nullable=False, unique=True)
    cash = db.Column(db.Boolean, nullable=False)
    card = db.Column(db.Boolean, nullable=False)

    __table_args__ = (
        db.CheckConstraint('method_id >= 1 AND method_id <= 2', name='method_id_check'),
        db.CheckConstraint("method_name IN ('Готівка', 'Карта')", name='method_name_check'),
        db.CheckConstraint(
            "(method_id = 1 AND cash = false AND card = true) OR "
            "(method_id = 2 AND cash = true AND card = false)",
            name='payment_method_check'
        ),
    )


class VehicleClass(db.Model):
    __tablename__ = 'vehicle_class'

    class_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    class_type = db.Column(db.String(8), nullable=False)
    class_multiplier = db.Column(db.Float, nullable=False)

    __table_args__ = (
        db.CheckConstraint("class_type IN ('Бізнес', 'Комфорт', 'Мінівен', 'Економ')", name='vehicle_class_class_type_check'),
    )

    @validates('class_type')
    def validate_surname(self, key, value):
        if not re.match("class_type IN ('Бізнес', 'Комфорт', 'Мінівен', 'Економ')", value):
            raise ValueError("Невірний формат класу транспортного засобу")
        return value


class VehicleBrand(db.Model):
    __tablename__ = 'vehicle_brand'

    brand_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(15), nullable=False, unique=True)

    __table_args__ = (
        db.CheckConstraint("name ~ '^[A-Za-z]{3,15}$'", name='vehicle_brand_name_check'),
    )

    @validates('name')
    def validate_surname(self, key, value):
        if not re.match('^[A-Za-z]{3,15}$', value):
            raise ValueError("Невірний формат назви бренду транспортного засобу")
        return value


class VehicleModel(db.Model):
    __tablename__ = 'vehicle_model'

    model_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    brand_id = db.Column(db.Integer, db.ForeignKey('vehicle_brand.brand_id', ondelete='SET NULL'), nullable=False)
    name = db.Column(db.String(15), nullable=False, unique=True)

    vehicle_brand = db.relationship('VehicleBrand', backref=db.backref('models', lazy=True))

    __table_args__ = (
        db.CheckConstraint("name ~ '^[A-Za-z0-9 -]{1,15}$'", name='vehicle_model_name_check'),
    )

    @validates('name')
    def validate_surname(self, key, value):
        if not re.match('^[A-Za-z0-9 -]{1,15}$', value):
            raise ValueError("Невірний формат назви моделі транспортного засобу")
        return value


class Vehicle(db.Model):
    __tablename__ = 'vehicle'

    vehicle_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    number = db.Column(db.String(10), nullable=False, unique=True)
    vin = db.Column(db.String(17), nullable=False, unique=True)
    color = db.Column(db.String(100), nullable=False)
    date_of_manufacture = db.Column(db.Date, nullable=False)
    is_company_vehicle = db.Column(db.Boolean, nullable=False)
    maintenance_date = db.Column(db.Date, nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('vehicle_class.class_id', ondelete='SET NULL'), nullable=False)
    seats_quantity = db.Column(db.Integer, nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey('vehicle_model.model_id', ondelete='SET NULL'), nullable=False)

    # Relationships
    vehicle_class = db.relationship('VehicleClass', backref=db.backref('vehicles', lazy=True))
    vehicle_model = db.relationship('VehicleModel', backref=db.backref('vehicles', lazy=True))

    __table_args__ = (
        db.CheckConstraint("number ~ '[A-ZА-ЯІ0-9]{3,10}'", name='vehicle_number_check'),
        db.CheckConstraint("vin ~ '^[A-Z0-9]{17}'", name='vehicle_vin_check'),
    )

    @validates('number')
    def validate_surname(self, key, value):
        if not re.match('[A-ZА-ЯІ0-9]{3,10}', value):
            raise ValueError("Невірний формат номерного знаку транспортного засобу")
        return value

    @validates('vin')
    def validate_surname(self, key, value):
        if not re.match('^[A-Z0-9]{17}', value):
            raise ValueError("Невірний формат VIN-номера транспортного засобу")
        return value


class RideStatus(db.Model):
    __tablename__ = 'ride_status'

    status_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    status_name = db.Column(db.String(100), nullable=False)

    __table_args__ = (
        db.CheckConstraint(
            "status_name IN ('Замовлено', 'В дорозі', 'Завершена', 'Скасована', 'Очікування')",
            name='ride_status_status_name_check'
        ),
    )

    @validates('status_name')
    def validate_surname(self, key, value):
        if not re.match("status_name IN ('Замовлено', 'В дорозі', 'Завершена', 'Скасована', 'Очікування')", value):
            raise ValueError("Невірний формат назви статусу поїздки")
        return value


class RideHistory(db.Model):
    __tablename__ = 'ride_history'

    ride_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.driver_id', ondelete='SET NULL'), nullable=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('driver_vehicle.vehicle_id', ondelete='SET NULL'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.customer_id', ondelete='SET NULL'), nullable=False)
    ride_start_id = db.Column(db.Integer, db.ForeignKey('address.address_id', ondelete='SET NULL'), nullable=True)
    ride_final_id = db.Column(db.Integer, db.ForeignKey('address.address_id', ondelete='SET NULL'), nullable=True)
    method_id = db.Column(db.Integer, db.ForeignKey('payment_method.method_id', ondelete='SET NULL'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('ride_status.status_id', ondelete='SET NULL'), nullable=False)
    ride_date = db.Column(db.Date, nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("vehicle_class.class_id", ondelete='SET NULL'), nullable=False)

    __table_args__ = (
        db.CheckConstraint(
            "price ~ '^[0-9]{1,6}$'",
            name='ride_history_price_check'
        ),
    )

    @validates('price')
    def validate_surname(self, key, value):
        if not re.match('^[0-9]{1,6}$', value):
            raise ValueError("Невірний формат ціни")
        return value