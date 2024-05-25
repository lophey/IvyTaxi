from flask import render_template, request, redirect, flash, url_for
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash

from package import app, db
from package.models import CustomerAuthentication, CustomerRegister, Address, CustomerAddress


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

            address = Address(city_id=city_id, street=street, house_number=house_number)
            db.session.add(address)
            db.session.flush()

            customer_address = CustomerAddress(customer_id=customer_id, address_id=address.address_id, order=1)
            db.session.add(customer_address)
            db.session.commit()
            return redirect(url_for('customer_profile'))

        # Delete address
        address_id = request.form.get('address_id')
        if address_id:
            address = Address.query.get(address_id)
            if address:
                db.session.delete(address)
                db.session.commit()
                flash('Address deleted successfully!')
            else:
                flash('Address not found!')
            return redirect(url_for('customer_profile'))
        else:
            flash('Address ID not provided!')


    # Display profile info
    profile_info = CustomerRegister.query.filter_by(phone_number=current_user.phone_number).first()
    return render_template('customer/Customer_Profile.html', profile_info=profile_info)


@app.route('/customer/rides')
@login_required
def customer_rides():
    return render_template('customer/Customer_Rides.html')


@app.after_request
def redirect_to_signin(response):
    if response.status_code == 401:
        return redirect(url_for('customer_login') + '?next=' + request.url)
    return response


