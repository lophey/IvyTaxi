from datetime import datetime

from flask import render_template, request, redirect, flash, url_for, session
from flask_login import login_user, login_required, logout_user, current_user
from sqlalchemy.exc import InternalError
from werkzeug.security import check_password_hash, generate_password_hash

from package import app, db
from package.Model.customer_models import CustomerAuthentication, CustomerRegister, Address, CustomerAddress, Payment


@app.route('/register/customer', methods=['GET', 'POST'])
def customer_register():
    name = request.form.get('name')
    surname = request.form.get('surname')
    phone_number = request.form.get('phone-number')
    email = request.form.get('email')
    password = request.form.get('password')
    password2 = request.form.get('password2')

    if request.method == 'POST':
        if not (name or surname or phone_number or email or password or password2):
            flash('Будь ласка, заповніть всі поля.')
        elif password != password2:
            flash('Паролі не співпадають.')
        else:
            hash_pwd = generate_password_hash(password)
            new_user = CustomerRegister(name=name, surname=surname, phone_number=phone_number, email=email)
            db.session.add(new_user)
            db.session.flush()

            new_user_auth_data = CustomerAuthentication(customer_id=new_user.customer_id, phone_number=phone_number, token=hash_pwd)
            db.session.add(new_user_auth_data)
            db.session.commit()

            return redirect(url_for('customer_login'))

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


@app.route('/customer/main')
@login_required
def customer_main():
    return render_template('customer/Customer_Main.html')


@app.route('/customer/profile', methods=['GET', 'POST'])
@login_required
def customer_profile():
    if request.method == 'POST':

        # Add address
        if 'city_name' in request.form and 'street' in request.form and 'house_number' in request.form:
            customer_id = current_user.customer_id
            city_id = request.form.get('city_name')
            street = request.form.get('street')
            house_number = request.form.get('house_number')

            existing_address = Address.query.filter_by(city_id=city_id, street=street, house_number=house_number).first()

            try:
                if existing_address:
                    address_id = existing_address.address_id
                    customer_address = CustomerAddress(customer_id=customer_id, address_id=address_id, order=1)
                    db.session.add(customer_address)
                    db.session.commit()
                    return redirect(url_for('customer_profile'))
                else:
                    address = Address(city_id=city_id, street=street, house_number=house_number)
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
        if 'card-number' in request.form and 'date-of-expiry' in request.form and 'cvv' in request.form:
            customer_id = current_user.customer_id
            method_id = 1
            card_number = request.form.get('card-number')
            date_of_expiry_str = request.form.get('date-of-expiry')
            date_of_expiry = datetime.strptime(date_of_expiry_str, '%Y-%m-%d').date()
            cvv = request.form.get('cvv')

            payment = Payment(method_id=method_id, customer_id=customer_id,
                              card_number=card_number, date_of_expiry=date_of_expiry, cvv=cvv)
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


@app.route('/customer/rides')
@login_required
def customer_rides():
    return render_template('customer/Customer_Rides.html')


@app.after_request
def redirect_to_signin(response):
    if response.status_code == 401:
        return redirect(url_for('customer_login') + '?next=' + request.url)
    return response


