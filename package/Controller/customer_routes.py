from datetime import datetime
import random
from hashlib import sha256

from flask import render_template, request, redirect, flash, url_for, session, g, make_response
# from flask_login import login_user, login_required, logout_user, current_user
from sqlalchemy import text, DDL
from sqlalchemy.exc import InternalError, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import aliased
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

from package import app, db
from package.Controller.session_manager import SessionManager, logger
from package.Model.customer_models import CustomerAuthentication, Customer, Address, CustomerAddress, Payment
from package.Model.driver_models import Driver
from package.Model.general_models import RideHistory, City, RideStatus, Vehicle, PaymentMethod, VehicleClass, \
    VehicleModel

session_manager = SessionManager()

def login_required(f):
    """
    Декоратор для защиты маршрута от неавторизованных пользователей.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'userid' not in session:  # Проверка на наличие сессии
            flash('Для доступа к этой странице необходимо войти', 'warning')
            return redirect(url_for('customer_login'))  # Перенаправление на страницу входа
        return f(*args, **kwargs)
    return decorated_function

def hash_password(password):
    return sha256(password.encode()).hexdigest()


def check_db_connection(user_id):
    db_session = session_manager.get_session(user_id)
    with db_session.connection() as connection:
        try:
            connection.execute(text('SELECT 1'))
            print('Підключення до бази даних успішне')
        except Exception as e:
            print(f'Помилка підключення до бази даних: {str(e)}')

def execute_sql_script(sql_script):
    try:
        db.session.execute(text(sql_script))
        db.session.commit()
        print("SQL script executed successfully!")
    except IntegrityError as e:
        db.session.rollback()
        print(f"Error executing SQL script: {e}")

def create_user_and_grant_role(phone_number, password, role):
    username = f"user_{phone_number}"
    create_user_script = f"""
    CREATE USER {username} WITH PASSWORD '{password}';
    GRANT {role} TO {username};
    """
    sql_script = create_user_script.format(phone_number=phone_number, password=password, role=role)
    execute_sql_script(sql_script)


@app.route('/register/customer', methods=['GET', 'POST'])
def customer_register():
    if 'userid' in session:  # Если пользователь уже авторизован
        return redirect(url_for('customer_main'))  # Перенаправление на главную страницу
    if request.method == 'POST':
        name = request.form.get('name')
        surname = request.form.get('surname')
        phone_number = request.form.get('phone-number')
        email = request.form.get('email')
        password = request.form.get('password')
        password2 = request.form.get('password2')
        role = "customer"
        if not (name or surname or phone_number or email or password or password2):
            flash('Будь ласка, заповніть всі поля.')
        elif password != password2:
            flash('Паролі не співпадають.')
        elif not (name.isalpha() and surname.isalpha()):
            flash('Ім\'я та прізвище повинні містити лише букви.')
        else:
            hash_pwd = hash_password(password)
            new_user = Customer(name=name, surname=surname, phone_number=phone_number, email=email, customer_role=role)
            db.session.add(new_user)
            db.session.flush()
            db.session.commit()

            create_user_and_grant_role(phone_number=phone_number, password=hash_pwd, role='customer')
            session['userrole'] = new_user.customer_role
            session['userid'] = new_user.customer_id

            db_connection = f"postgresql://user_{phone_number}:{hash_pwd}@localhost:5432/TaxiCompany_DB"
            try:
                session_manager.create_session(new_user.customer_id, db_connection)
                check_db_connection(new_user.customer_id)
                g.customer_id = new_user.customer_id

                # Устанавливаем cookie для отслеживания сессии
                resp = make_response(redirect(url_for('driver_main')))
                resp.set_cookie('driver_logged_in', 'true', max_age=60*60*24*30)  # cookie на 30 дней

                flash('Реєстрація пройшла успішно', 'success')
                return resp
            except Exception as e:
                db.session.rollback()
                flash(f'Помилка при реєстрації: {str(e)}', 'error')
                return redirect(url_for('customer_main'))

    return render_template('customer/Customer_Register.html')


@app.route('/login/customer', methods=['GET', 'POST'])
def customer_login():
    if 'userid' in session:  # Если пользователь уже авторизован
        return redirect(url_for('customer_main'))  # Перенаправление на главную страницу
    if request.method == 'POST':
        phone_number = request.form.get('phone-number')
        password = request.form.get('password')

        if phone_number and password:
            user = Customer.query.filter_by(phone_number=phone_number).first()

            if user:
                session['userrole'] = user.customer_role
                session['userid'] = user.customer_id

                hash_pwd = hash_password(password)
                db_connection = f"postgresql://user_{phone_number}:{hash_pwd}@localhost:5432/TaxiCompany_DB"

                try:
                    # Получаем или создаем сессию для пользователя
                    existing_session = session_manager.get_session(user.customer_id)
                    if existing_session:
                        logger.info(f"Используется существующая сессия для пользователя {user.customer_id}")
                    else:
                        session_manager.create_session(user.customer_id, db_connection)
                        check_db_connection(user.customer_id)
                        g.customer_id = user.customer_id  # Для передачи customer_id в другие обработчики
                    # Устанавливаем cookie для отслеживания сессии
                    resp = make_response(redirect(url_for('customer_main')))
                    resp.set_cookie('user_logged_in', 'true', max_age=60*60*24*30)  # cookie на 30 дней

                    flash('Авторизація пройшла успішно', 'success')
                    return resp
                except Exception as e:
                    flash(f'Помилка при ідентифікації користувача: {str(e)}', 'error')
                    return redirect(url_for('customer_login'))
            else:
                flash('Номер телефону або пароль невірний.', 'error')
        else:
            flash('Будь ласка, заповніть всі поля.', 'error')

    return render_template('customer/Customer_Login.html')

@app.route('/logout/customer', methods=['GET', 'POST'])
@login_required
def customer_logout():
    user_id = session.get('userid')  # Получаем ID пользователя из сессии

    # Закрываем соединение с БД, если оно существует
    if user_id:
        db_session = session_manager.get_session(user_id)
        if db_session:
            db_session.close()  # Закрытие сессии SQLAlchemy
            session_manager.close_session(user_id)  # Удаление сессии из SessionManager

    session.clear()  # Очистка сессии Flask
    response = redirect(url_for('customer_login'))
    response.delete_cookie('user_logged_in')
    flash('Ви успішно вийшли з акаунту.', 'success')
    return response


@app.route('/customer/main', methods=['GET', 'POST'])
@login_required
def customer_main():
    # Получение методов оплаты
    payment_methods = db.session.execute(
        text(
            """
            SELECT payment_id, format_card_number(card_number) AS card_number_display 
            FROM Payment 
            WHERE customer_id = :customer_id
            """
        ),
        {'customer_id': session.get('userid')}
    ).fetchall()

    # Получение сохраненных адресов
    saved_addresses = db.session.execute(
        text(
            """
            SELECT a.street, a.house_number, c.city_name
            FROM Address a
            JOIN Customer_Address ca ON a.address_id = ca.address_id
            JOIN City c ON a.city_id = c.city_id
            WHERE ca.customer_id = :customer_id
            """
        ),
        {'customer_id': session.get('userid')}
    ).fetchall()

    if request.method == 'POST':
        try:
            selected_class = request.form.get('class')
            class_map = {'business': 1, 'comfort': 2, 'minivan': 3, 'economy': 4}
            vehicle_class = class_map.get(selected_class)

            if vehicle_class is None:
                return "Invalid vehicle class", 400

            payment_method = request.form.get('payment_type')

            # Получение или вставка адресов через функцию в PostgreSQL
            start_address_id = db.session.execute(text(
                "SELECT get_or_insert_address(:start_city_name, :start_street, :start_house_number)"),
                {'start_city_name': request.form.get('start_city_name'),
                 'start_street': request.form.get('start_street'),
                 'start_house_number': request.form.get('start_house_number')}
            ).scalar()

            final_address_id = db.session.execute(text(
                "SELECT get_or_insert_address(:final_city_name, :final_street, :final_house_number)"),
                {'final_city_name': request.form.get('final_city_name'),
                 'final_street': request.form.get('final_street'),
                 'final_house_number': request.form.get('final_house_number')}
            ).scalar()

            # Вставка записи в RideHistory, расчет цены будет выполнен триггером
            new_ride = RideHistory(
                customer_id=session.get('userid'),
                method_id=payment_method,
                status_id=1,
                ride_date=datetime.today(),
                class_id=vehicle_class,
                ride_start_id=start_address_id,
                ride_final_id=final_address_id
            )
            db.session.add(new_ride)
            db.session.commit()

            return redirect(url_for('customer_rides'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f"Ошибка при сохранении: {str(e)}")

    return render_template('customer/Customer_Main.html', payment_methods=payment_methods,
                           saved_addresses=saved_addresses)


@app.route('/customer/profile', methods=['GET', 'POST'])
@login_required
def customer_profile():
    if request.method == 'POST':

        # Add address
        customer_id = session.get('userid')
        address_id = request.form.get('address_id')

        # Проверяем, что все необходимые данные присутствуют
        city_name = request.form.get('city_name')
        street = request.form.get('street')
        house_number = request.form.get('house_number')

        if city_name and street and house_number:
            db.session.execute(
                text("""
                CALL manage_customer_address(:p_customer_id, :p_city_name, :p_street, :p_house_number, 'ADD', NULL);
                """),
                {
                    'p_customer_id': customer_id,
                    'p_city_name': city_name,
                    'p_street': street,
                    'p_house_number': house_number
                }
            )
            db.session.commit()
            return redirect(url_for('customer_profile'))

        # Удаление адреса
        if address_id:
            try:
                print(f"Attempting to delete address with POST method: {address_id} for customer {customer_id}")
                # Выполняем удаление через вызов процедуры
                db.session.execute(
                    text("""
                    CALL manage_customer_address(:p_customer_id, NULL, NULL, NULL, 'DELETE', :p_address_id);
                    """),
                    {
                        'p_customer_id': customer_id,
                        'p_address_id': int(address_id)
                    }
                )
                db.session.commit()
                flash('Адрес успешно удален!')
                return redirect(url_for('customer_profile'))
            except Exception as e:
                db.session.rollback()
                flash('Ошибка при удалении адреса: ' + str(e))
                return redirect(url_for('customer_profile'))

        # Add payment
        if 'card-number' in request.form:
            customer_id = session.get('userid')
            method_id = 1  # ID метода оплаты
            card_number = request.form.get('card-number')

            try:
                db.session.execute(
                    text("""
                    CALL manage_payment_method(
                        :p_action, :p_customer_id, :p_method_id, :p_card_number, NULL
                    );
                    """), {'p_action': 'ADD', 'p_customer_id': customer_id,
                           'p_method_id': method_id,
                           'p_card_number': card_number
                           }
                )
                db.session.commit()
                return redirect(url_for('customer_profile'))
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при добавлении способа оплаты: {str(e)}')
                return redirect(url_for('customer_profile'))

        # Delete payment
        payment_id = request.form.get('payment_id')
        if payment_id:
            try:
                db.session.execute(
                    text("""
                    CALL manage_payment_method(
                        :p_action, :p_customer_id, NULL, NULL, :p_payment_id
                    );
                    """), {'p_action': 'DELETE', 'p_customer_id': session.get('userid'),
                           'p_payment_id': int(payment_id)
                           }
                )
                db.session.commit()
                flash('Спосіб оплати успішно видалено!')
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при удалении способа оплаты: {str(e)}')
            return redirect(url_for('customer_profile'))

    # Display profile info
    profile_info = Customer.query.filter_by(customer_id=session.get("userid")).first()

    # Получение методов оплаты
    payment_methods = db.session.execute(
        text(
            """
            SELECT payment_id, format_card_number(card_number) AS card_number_display 
            FROM Payment 
            WHERE customer_id = :customer_id
            """
        ),
        {'customer_id': session.get('userid')}
    ).fetchall()

    return render_template('customer/Customer_Profile.html', profile_info=profile_info, payment_methods=payment_methods)


@app.route('/customer/rides', methods=['GET', 'POST'])
@login_required
def customer_rides():
    customer_id = session.get('userid')

    if request.method == 'POST':
        ride_id = request.form.get('ride_id')
        ride = RideHistory.query.get(ride_id)

        if ride and ride.customer_id == session.get('userid'):
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
        Driver.name.label('driver_name'),
        Vehicle.number.label('vehicle_number'),
        VehicleModel.name.label('vehicle_model'),
        StartAddress.street.label('start_street'),
        StartAddress.house_number.label('start_house_number'),
        FinalAddress.street.label('final_street'),
        FinalAddress.house_number.label('final_house_number'),
        PaymentMethod.method_name,
        RideStatus.status_name,
        VehicleClass.class_type
    ).join(Driver, RideHistory.driver_id == Driver.driver_id, isouter=True) \
        .join(Vehicle, RideHistory.vehicle_id == Vehicle.vehicle_id, isouter=True) \
        .join(VehicleModel, VehicleModel.model_id == Vehicle.model_id, isouter=True) \
        .join(StartAddress, RideHistory.ride_start_id == StartAddress.address_id, isouter=True) \
        .join(FinalAddress, RideHistory.ride_final_id == FinalAddress.address_id, isouter=True) \
        .join(PaymentMethod, RideHistory.method_id == PaymentMethod.method_id, isouter=True) \
        .join(RideStatus, RideHistory.status_id == RideStatus.status_id, isouter=True) \
        .join(VehicleClass, RideHistory.class_id == VehicleClass.class_id, isouter=True) \
        .filter(RideHistory.customer_id == customer_id) \
        .order_by(RideHistory.ride_id.desc()) \
        .all()

    return render_template('customer/Customer_Rides.html', rides=rides)

@app.before_request
def load_logged_in_user():
    user_id = session.get('userid')
    if user_id:
        try:
            existing_session = session_manager.get_session(user_id)
            if not existing_session:
                db_uri = session_manager.user_uris.get(user_id)
                if db_uri:
                    session_manager.create_session(user_id, db_uri)
                    logger.info(f"Восстановлена сессия для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка восстановления сессии для пользователя {user_id}: {e}")

@app.after_request
def redirect_to_signin(response):
    if response.status_code == 401:
        return redirect(url_for('customer_login') + '?next=' + request.url)
    return response
