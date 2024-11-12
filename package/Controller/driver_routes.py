from datetime import datetime

from flask import render_template, request, redirect, flash, url_for, session
from flask_login import login_user, login_required, logout_user, current_user
from sqlalchemy.orm import aliased
from werkzeug.security import check_password_hash, generate_password_hash

from package import app, db
from package.Model.customer_models import CustomerRegister, Address
from package.Model.driver_models import DriverRegister, DriverAuthentication, DriverVehicle
from package.Model.general_models import Vehicle, RideHistory, PaymentMethod, RideStatus, VehicleClass


@app.route('/register/driver', methods=['GET', 'POST'])
def driver_register():
    name = request.form.get('name')
    surname = request.form.get('surname')
    country_id = request.form.get('country')
    phone_number = request.form.get('phone-number')
    date_of_birth_str = request.form.get('date-of-birth')
    sex_str = request.form.get('sex')
    if sex_str == 'Male':
        sex = True
    else:
        sex = False
    email = request.form.get('email')
    drivers_license_number = request.form.get('drivers-license-number')
    passport_id = request.form.get('passport-id')
    password = request.form.get('password')
    password2 = request.form.get('password2')

    if request.method == 'POST':
        if not (name or surname or country_id or phone_number or date_of_birth_str or sex or email
                or drivers_license_number or passport_id or password or password2):
            flash('Будь ласка, заповніть всі поля.')
        elif password != password2:
            flash('Паролі не співпадають.')
        else:
            try:
                date_of_birth = datetime.strptime(date_of_birth_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Некоректний формат дати народження. Використовуйте YYYY-MM-DD.')
            hash_pwd = generate_password_hash(password)
            new_user = DriverRegister(name=name, surname=surname, country_id=country_id, phone_number=phone_number,
                                      date_of_birth=date_of_birth, sex=sex, email=email, drivers_license_number=drivers_license_number, passport_id=passport_id)
            db.session.add(new_user)
            db.session.flush()

            new_user_auth_data = DriverAuthentication(driver_id=new_user.driver_id, phone_number=phone_number, token=hash_pwd)
            db.session.add(new_user_auth_data)
            db.session.commit()

            return redirect(url_for('driver_login'))

    return render_template('driver/Driver_Register.html')


@app.route('/login/driver', methods=['GET', 'POST'])
def driver_login():
    phone_number = request.form.get('phone-number')
    token = request.form.get('password')

    if phone_number and token:
        driver_authentication = DriverAuthentication.query.filter_by(phone_number=phone_number).first()
        if driver_authentication and check_password_hash(driver_authentication.token, token):
            login_user(driver_authentication)
            session['user_type'] = 'driver'
            return redirect(url_for('driver_main'))
        else:
            flash('Номер телефону або пароль невірний.')
    else:
        flash('Будь ласка, заповніть всі поля.')

    return render_template('driver/Driver_Login.html')


@app.route('/logout/driver', methods=['GET', 'POST'])
@login_required
def driver_logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/driver/main')
@login_required
def driver_main():
    return render_template('driver/Driver_Main.html')


@app.route('/driver/orders', methods=['GET', 'POST'])
@login_required
def driver_orders():
    driver_id = current_user.driver_id

    # Получаем класс автомобиля водителя
    driver_vehicle = DriverVehicle.query.filter_by(driver_id=driver_id).first()

    # Проверка активной поездки водителя
    active_ride = RideHistory.query.filter_by(driver_id=driver_id, status_id=2).first()

    if request.method == 'POST':
        ride_id = request.form.get('ride_id')
        ride = RideHistory.query.get(ride_id)

        if ride and ride.class_id == driver_vehicle.vehicle.class_id:
            # Изменение статуса заказа
            if ride.status_id == 1:  # Замовлено
                ride.status_id = 2  # В дорозі
                ride.driver_id = driver_id
                ride.vehicle_id = driver_vehicle.vehicle.vehicle_id
                db.session.commit()
                flash('Поїздка успішно підтверджена.', 'success')
                return redirect(url_for('driver_orders'))
        return redirect(url_for('driver_orders'))

    StartAddress = aliased(Address)
    FinalAddress = aliased(Address)

    if driver_vehicle:
        driver_vehicle_class_id = driver_vehicle.vehicle.class_id

        if active_ride:
            # Показываем только текущие поездки водителя
            rides = db.session.query(
                RideHistory,
                CustomerRegister.name.label('customer_name'),
                StartAddress.street.label('start_street'),
                StartAddress.house_number.label('start_house_number'),
                FinalAddress.street.label('final_street'),
                FinalAddress.house_number.label('final_house_number'),
                PaymentMethod.method_name,
                RideStatus.status_name
            ).join(CustomerRegister, RideHistory.customer_id == CustomerRegister.customer_id, isouter=True) \
                .join(StartAddress, RideHistory.ride_start_id == StartAddress.address_id, isouter=True) \
                .join(FinalAddress, RideHistory.ride_final_id == FinalAddress.address_id, isouter=True) \
                .join(PaymentMethod, RideHistory.method_id == PaymentMethod.method_id, isouter=True) \
                .join(RideStatus, RideHistory.status_id == RideStatus.status_id, isouter=True) \
                .filter(RideHistory.driver_id == driver_id) \
                .filter(RideHistory.status_id != 4) \
                .order_by(RideHistory.ride_date.desc()) \
                .all()
        else:
            # Фильтруем поездки по классу автомобиля
            rides = db.session.query(
                RideHistory,
                CustomerRegister.name.label('customer_name'),
                StartAddress.street.label('start_street'),
                StartAddress.house_number.label('start_house_number'),
                FinalAddress.street.label('final_street'),
                FinalAddress.house_number.label('final_house_number'),
                PaymentMethod.method_name,
                RideStatus.status_name
            ).join(CustomerRegister, RideHistory.customer_id == CustomerRegister.customer_id, isouter=True) \
                .join(StartAddress, RideHistory.ride_start_id == StartAddress.address_id, isouter=True) \
                .join(FinalAddress, RideHistory.ride_final_id == FinalAddress.address_id, isouter=True) \
                .join(PaymentMethod, RideHistory.method_id == PaymentMethod.method_id, isouter=True) \
                .join(RideStatus, RideHistory.status_id == RideStatus.status_id, isouter=True) \
                .filter(RideHistory.class_id == driver_vehicle_class_id) \
                .filter(
                (RideHistory.driver_id == driver_id) |  # Водитель принял поездку
                (RideHistory.driver_id == None)  # Водитель еще не назначен
                ) \
                .filter(RideHistory.status_id != 4) \
                .order_by(RideHistory.driver_id.is_(None).desc()) \
                .order_by(RideHistory.ride_date.desc()) \
                .all()
    else:
        rides = []  # Если у водителя нет автомобиля, возвращаем пустой список

    return render_template('driver/Driver_Orders.html', rides=rides)


@app.route('/driver/profile', methods=['GET', 'POST'])
@login_required
def driver_profile():
    if request.method == 'POST':

        # Add vehicle
        if 'model-id' in request.form and 'number' in request.form and 'vin' in request.form and 'color' in request.form \
                and 'seats-quantity' in request.form and 'date-of-manufacture' in request.form and 'maintenance-date' in request.form \
                and 'class-id' in request.form and 'is-company-vehicle' in request.form:
            driver_id = current_user.driver_id
            model_id = request.form.get('model-id')
            number = request.form.get('number')
            vin = request.form.get('vin')
            color = request.form.get('color')
            seats_quantity = request.form.get('seats-quantity')
            date_of_manufacture_str = request.form.get('date-of-manufacture')
            maintenance_date_str = request.form.get('maintenance-date')
            class_id = request.form.get('class-id')
            is_company_vehicle_str = request.form.get('is-company-vehicle-id')
            if is_company_vehicle_str == 'Yes':
                is_company_vehicle = True
            else:
                is_company_vehicle = False
            try:
                date_of_manufacture = datetime.strptime(date_of_manufacture_str, '%Y-%m-%d').date()
                maintenance_date = datetime.strptime(maintenance_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Некоректний формат дати народження. Використовуйте YYYY-MM-DD.')

            vehicle = Vehicle(model_id=model_id, number=number, vin=vin, color=color,
                              seats_quantity=seats_quantity, date_of_manufacture=date_of_manufacture, maintenance_date=maintenance_date,
                              class_id=class_id, is_company_vehicle=is_company_vehicle)
            db.session.add(vehicle)
            db.session.flush()

            driver_vehicle = DriverVehicle(driver_id=driver_id, vehicle_id=vehicle.vehicle_id)
            db.session.add(driver_vehicle)
            db.session.commit()
            return redirect(url_for('driver_profile'))

        # Delete vehicle
        vehicle_id = request.form.get('vehicle_id')
        if vehicle_id:
            vehicle = Vehicle.query.get(vehicle_id)
            if vehicle:
                db.session.delete(vehicle)
                db.session.commit()
                flash('Vehicle deleted successfully!')
            else:
                flash('Vehicle not found!')
            return redirect(url_for('driver_profile'))
        else:
            flash('Vehicle ID not provided!')

    # Display profile info
    profile_info = DriverRegister.query.filter_by(phone_number=current_user.phone_number).first()
    drivers_vehicles = DriverVehicle.query.filter_by(driver_id=current_user.driver_id).all()
    if not drivers_vehicles:
        drivers_vehicles = []

    return render_template('driver/Driver_Profile.html', profile_info=profile_info, drivers_vehicles=drivers_vehicles)
