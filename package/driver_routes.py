from datetime import datetime

from flask import render_template, request, redirect, flash, url_for
from flask_login import login_user, login_required, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from package import app, db
from package.models import DriverRegister, DriverAuthentication


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