from datetime import datetime
import random

from flask import render_template, request, redirect, flash, url_for, session
from flask_login import login_user, login_required, logout_user, current_user
from sqlalchemy.exc import InternalError
from sqlalchemy.orm import aliased
from werkzeug.security import check_password_hash, generate_password_hash

from package import app, db
from package.Model.customer_models import CustomerAuthentication, CustomerRegister, Address, CustomerAddress, Payment
from package.Model.driver_models import DriverRegister
from package.Model.general_models import RideHistory, City, RideStatus, Vehicle, PaymentMethod, VehicleClass, \
    VehicleModel


@app.route('/register/customer', methods=['GET', 'POST'])
def customer_register():
    if request.method == 'POST':
        name = request.form.get('name')
        surname = request.form.get('surname')
        phone_number = request.form.get('phone-number')
        email = request.form.get('email')
        password = request.form.get('password')
        password2 = request.form.get('password2')
        if not (name or surname or phone_number or email or password or password2):
            flash('Будь ласка, заповніть всі поля.')
        elif password != password2:
            flash('Паролі не співпадають.')
        elif not (name.isalpha() and surname.isalpha()):
            flash('Ім\'я та прізвище повинні містити лише букви.')
        else:
            try:
                hash_pwd = generate_password_hash(password)
                new_user = CustomerRegister(name=name, surname=surname, phone_number=phone_number, email=email)
                db.session.add(new_user)
                db.session.flush()

                new_user_auth_data = CustomerAuthentication(customer_id=new_user.customer_id, phone_number=phone_number, token=hash_pwd)
                db.session.add(new_user_auth_data)
                db.session.commit()

                return redirect(url_for('customer_login'))
            except Exception as e:
                db.session.rollback()
                flash(f'Помилка при реєстрації: {e}'
                      f' Name: {name}')

    return render_template('customer/Customer_Register.html')


@app.route('/login/customer', methods=['GET', 'POST'])
def customer_login():
    phone_number = request.form.get('phone-number')
    token = request.form.get('password')

    if phone_number and token:
        user_authentication = CustomerAuthentication.query.filter_by(phone_number=phone_number).first()
        if user_authentication and check_password_hash(user_authentication.token, token):
            login_user(user_authentication)
            session['user_type'] = 'customer'
            return redirect(url_for('customer_main'))
        else:
            flash('Номер телефону або пароль невірний.')
    else:
        flash('Будь ласка, заповніть всі поля.')

    return render_template('customer/Customer_Login.html')


@app.route('/logout/customer', methods=['GET', 'POST'])
@login_required
def customer_logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/customer/main', methods=['GET', 'POST'])
@login_required
def customer_main():
    vehicle_class = None
    payment_methods = Payment.query.filter_by(customer_id=current_user.customer_id).all()
    # saved_address = Address.query.filter_by(customer_id=current_user.customer_id).first()

    saved_addresses = (
        db.session.query(Address.street, Address.house_number, City.city_name)
        .join(CustomerAddress, Address.address_id == CustomerAddress.address_id)
        .join(City, Address.city_id == City.city_id)
        .filter(CustomerAddress.customer_id == current_user.customer_id)
        .all()
    )

    # Format card numbers
    for payment in payment_methods:
        if payment.card_number:
            payment.card_number_display = '*' * 12 + payment.card_number[-4:]

    if request.method == 'POST':
        selected_class = request.form.get('class')
        if selected_class == 'business':
            vehicle_class = 1
        elif selected_class == 'comfort':
            vehicle_class = 2
        elif selected_class == 'minivan':
            vehicle_class = 3
        elif selected_class == 'economy':
            vehicle_class = 4

        if vehicle_class is None:
            return "Invalid vehicle class", 400

        # Получаем коэффициент класса из таблицы VehicleClass
        vehicle_class_obj = VehicleClass.query.filter_by(class_id=vehicle_class).first()
        if not vehicle_class_obj:
            return "Vehicle class not found", 400

        start_city_name = request.form.get('start_city_name')
        start_street = request.form.get('start_street')
        start_house_number = request.form.get('start_house_number')

        final_city_name = request.form.get('final_city_name')
        final_street = request.form.get('final_street')
        final_house_number = request.form.get('final_house_number')

        payment_method = request.form.get('payment_type')


        start_city = City.query.filter_by(city_name=start_city_name).first()
        if not start_city:
            return "Ми не обслуговуємо у цьому місті", 400

        final_city = City.query.filter_by(city_name=final_city_name).first()
        if not final_city:
            return "Ми не обслуговуємо у цьому місті", 400

        start_address = Address.query.filter_by(
            city_id=start_city.city_id,
            street=start_street,
            house_number=start_house_number
        ).first()
        if not start_address:
            start_address = Address(city_id=start_city.city_id, street=start_street, house_number=start_house_number)
            db.session.add(start_address)
            db.session.flush()

        final_address = Address.query.filter_by(
            city_id=final_city.city_id,
            street=final_street,
            house_number=final_house_number
        ).first()
        if not final_address:
            final_address = Address(city_id=final_city.city_id, street=final_street, house_number=final_house_number)
            db.session.add(final_address)
            db.session.flush()

        # Генерация случайной базовой цены и умножение на коэффициент
        base_price = random.randint(10, 200)  # Базовая случайная цена между 10 и 200
        final_price = round(base_price * vehicle_class_obj.class_multiplier, 2)  # Округляем до 2 знаков

        new_ride = RideHistory(customer_id=current_user.customer_id,  method_id=payment_method, price=final_price,
                               status_id=1, ride_date=datetime.today(), class_id=vehicle_class,
                               ride_start_id=start_address.address_id, ride_final_id=final_address.address_id)
        db.session.add(new_ride)
        db.session.commit()
        return redirect(url_for('customer_rides'))
    return render_template('customer/Customer_Main.html', payment_methods=payment_methods, saved_addresses=saved_addresses)


@app.route('/customer/profile', methods=['GET', 'POST'])
@login_required
def customer_profile():
    if request.method == 'POST':

        # Add address
        if 'city_name' in request.form and 'street' in request.form and 'house_number' in request.form:
            customer_id = current_user.customer_id
            city_name = request.form.get('city_name')
            street = request.form.get('street')
            house_number = request.form.get('house_number')

            city = City.query.filter_by(city_name=city_name).first()
            if not city:
                return "Ми не обслуговуємо у цьому місті", 400

            existing_address = Address.query.filter_by(city_id=city.city_id, street=street, house_number=house_number).first()

            try:
                if existing_address:
                    address_id = existing_address.address_id
                    customer_address = CustomerAddress(customer_id=customer_id, address_id=address_id, order=1)
                    db.session.add(customer_address)
                    db.session.commit()
                    return redirect(url_for('customer_profile'))
                else:
                    address = Address(city_id=city.city_id, street=street, house_number=house_number)
                    db.session.add(address)
                    db.session.flush()

                    customer_address = CustomerAddress(customer_id=customer_id, address_id=address.address_id, order=1)
                    db.session.add(customer_address)
                    db.session.commit()
                    return redirect(url_for('customer_profile'))
            except InternalError:
                db.session.rollback()
                flash('Ви вже додали цей адрес!')
                return redirect(url_for('customer_profile'))

        # Delete address
        address_id = request.form.get('address_id')
        if address_id:
            customer_id = current_user.customer_id
            customer_address = CustomerAddress.query.filter_by(customer_id=customer_id, address_id=address_id).first()
            if customer_address:
                db.session.delete(customer_address)
                db.session.commit()
                flash('Адресу успішно видалено!')
            # else:
            #     flash('Address not found!')
            return redirect(url_for('customer_profile'))
        # else:
        #     flash('Address ID not provided!')

        # Add payment
        if 'card-number' in request.form:
            customer_id = current_user.customer_id
            method_id = 1
            card_number = request.form.get('card-number')

            payment = Payment(method_id=method_id, customer_id=customer_id,
                              card_number=card_number)
            db.session.add(payment)
            db.session.commit()
            return redirect(url_for('customer_profile'))

        # Delete payment
        payment_id = request.form.get('payment_id')
        if payment_id:
            payment = Payment.query.get(payment_id)
            if payment:
                db.session.delete(payment)
                db.session.commit()
                flash('Спосіб оплати успішно видалено!')
            else:
                flash('Спосіб оплати не знайдено!')
            return redirect(url_for('customer_profile'))
        # else:
        #     flash('Payment ID not provided!')

    # Display profile info
    profile_info = CustomerRegister.query.filter_by(phone_number=current_user.phone_number).first()
    payment_methods = Payment.query.filter_by(customer_id=current_user.customer_id).all()

    # Format card numbers
    for payment in payment_methods:
        if payment.card_number:
            payment.card_number_display = '*' * 12 + payment.card_number[-4:]

    return render_template('customer/Customer_Profile.html', profile_info=profile_info, payment_methods=payment_methods)


@app.route('/customer/rides', methods=['GET', 'POST'])
@login_required
def customer_rides():
    customer_id = current_user.customer_id

    if request.method == 'POST':
        ride_id = request.form.get('ride_id')
        ride = RideHistory.query.get(ride_id)

        if ride and ride.customer_id == current_user.customer_id:
            if ride.status_id == 1 or ride.status_id == 5:
                ride.status_id = 4
                db.session.commit()
                flash('Поїздка успішно скасована.', 'success')
                return redirect(url_for('customer_rides'))
            else:
                flash('Не вдалось відмінити поїздку.', 'error')

            if ride.status_id == 2:
                ride.status_id = 3
                db.session.commit()
                flash('Поїздка успішно завершена.', 'success')
                return redirect(url_for('customer_rides'))
            else:
                flash('Не вдалось завершити поїздку.', 'error')

    StartAddress = aliased(Address)
    FinalAddress = aliased(Address)

    rides = db.session.query(
        RideHistory,
        DriverRegister.name.label('driver_name'),
        Vehicle.number.label('vehicle_number'),
        VehicleModel.name.label('vehicle_model'),
        StartAddress.street.label('start_street'),
        StartAddress.house_number.label('start_house_number'),
        FinalAddress.street.label('final_street'),
        FinalAddress.house_number.label('final_house_number'),
        PaymentMethod.method_name,
        RideStatus.status_name,
        VehicleClass.class_type
    ).join(DriverRegister, RideHistory.driver_id == DriverRegister.driver_id, isouter=True) \
        .join(Vehicle, RideHistory.vehicle_id == Vehicle.vehicle_id, isouter=True) \
        .join(VehicleModel, VehicleModel.model_id == Vehicle.model_id, isouter=True) \
        .join(StartAddress, RideHistory.ride_start_id == StartAddress.address_id, isouter=True) \
        .join(FinalAddress, RideHistory.ride_final_id == FinalAddress.address_id, isouter=True) \
        .join(PaymentMethod, RideHistory.method_id == PaymentMethod.method_id, isouter=True) \
        .join(RideStatus, RideHistory.status_id == RideStatus.status_id, isouter=True) \
        .join(VehicleClass, RideHistory.class_id == VehicleClass.class_id, isouter=True) \
        .filter(RideHistory.customer_id == customer_id).all()

    return render_template('customer/Customer_Rides.html', rides=rides)


@app.after_request
def redirect_to_signin(response):
    if response.status_code == 401:
        return redirect(url_for('customer_login') + '?next=' + request.url)
    return response


