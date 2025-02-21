from datetime import datetime
from hashlib import sha256

from flask import render_template, request, redirect, flash, url_for, session, g, make_response
from sqlalchemy import text, func, extract, create_engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, OperationalError
from sqlalchemy.orm import aliased
from functools import wraps

from package import app, db
from package.Controller.session_manager import SessionManager, logger
from package.Model.administrator_models import BlockedUsers
from package.Model.customer_models import Customer, Address
from package.Model.driver_models import Driver
from package.Model.general_models import RideHistory, RideStatus, Vehicle, PaymentMethod, VehicleClass, \
    VehicleModel

session_manager = SessionManager()


def verify_db_connection(username, password, dbname='TaxiCompany_DB', host='localhost', port=5432):
    """
    Перевіряє, чи можна підключитися до бази даних з введеними обліковими даними.
    Повертає True, якщо підключення вдале, і False, якщо ні.
    """
    try:
        # Формуємо рядок підключення
        connection_string = f'postgresql://{username}:{password}@{host}:{port}/{dbname}'

        # Створюємо двигун і намагаємося підключитися
        engine = create_engine(connection_string)
        connection = engine.connect()
        connection.close()  # Закриваємо з'єднання
        return True
    except OperationalError as e:
        print(f"Помилка підключення: {e}")
        return False


def login_required(f):
    """
    Декоратор для защиты маршрута от неавторизованных пользователей.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
            if 'userid' not in session:  # Проверка на наличие сессии
                flash('Для доступу до цієї сторінки необхідно увійти', 'warning')
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


def is_user_blocked(user_id, user_type):
    return BlockedUsers.query.filter_by(user_id=user_id, user_type=user_type).first() is not None


def get_block_reason(user_id, user_type):
    blocked_user = BlockedUsers.query.filter_by(user_id=user_id, user_type=user_type).first()
    return blocked_user.block_reason if blocked_user else None


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
            flash('Будь ласка, заповніть всі поля.', 'error-customer-register')
        elif password != password2:
            flash('Паролі не співпадають.', 'error-customer-register')
            return redirect(url_for('customer_register'))
        elif not (name.isalpha() and surname.isalpha()):
            flash('Ім\'я та прізвище повинні містити лише букви.', 'error-customer-register')
            return redirect(url_for('customer_register'))
        else:
            hash_pwd = hash_password(password)
            new_user = Customer(name=name, surname=surname, phone_number=phone_number, email=email, customer_role=role)
            db.session.add(new_user)
            db.session.flush()
            db.session.commit()

            create_user_and_grant_role(phone_number=phone_number, password=hash_pwd, role='customer')
            session['userrole'] = new_user.customer_role
            session['userid'] = new_user.customer_id

            try:
                db_connection = f"postgresql://user_{phone_number}:{hash_pwd}@localhost:5432/TaxiCompany_DB"
                session_manager.create_session(new_user.customer_id, db_connection)
                check_db_connection(new_user.customer_id)
                g.customer_id = new_user.customer_id

                # Устанавливаем cookie для отслеживания сессии
                resp = make_response(redirect(url_for('customer_main')))
                resp.set_cookie('customer_logged_in', 'true', max_age=60*60*24*30)  # cookie на 30 дней

                flash('Реєстрація пройшла успішно.', 'success-customer-register')
                return resp
            except Exception as e:
                db.session.rollback()
                flash(f'Помилка при реєстрації.', 'error-customer-register')
                return redirect(url_for('customer_register'))

    return render_template('customer/Customer_Register.html')


@app.route('/login/customer', methods=['GET', 'POST'])
def customer_login():
    if 'userid' in session:  # Если пользователь уже авторизован
        return redirect(url_for('customer_main'))  # Перенаправление на главную страницу

    if request.method == 'POST':
        phone_number = request.form.get('phone-number')
        password = request.form.get('password')

        hash_pwd = hash_password(password)

        try:
            if phone_number and password:
                # Формуємо ім'я користувача для підключення до бази даних
                db_username = f"user_{phone_number}"

                if verify_db_connection(db_username, hash_pwd):
                    user = Customer.query.filter_by(phone_number=phone_number).first()

                    if user:
                        if is_user_blocked(user.customer_id, user.customer_role):
                            flash('Ваш акаунт заблоковано. Причина: ' + get_block_reason(user.customer_id, user.customer_role), 'error-customer-login')
                            return redirect(url_for('customer_login'))

                        session['userrole'] = user.customer_role
                        session['userid'] = user.customer_id


                        # Получаем или создаем сессию для пользователя
                        existing_session = session_manager.get_session(user.customer_id)
                        if existing_session:
                            logger.info(f"Використовується існуюча сесія для користувача {user.customer_id}")
                        else:
                            db_connection = f"postgresql://user_{phone_number}:{hash_pwd}@localhost:5432/TaxiCompany_DB"
                            session_manager.create_session(user.customer_id, db_connection)
                            check_db_connection(user.customer_id)
                            g.customer_id = user.customer_id  # Для передачи customer_id в другие обработчики
                        # Устанавливаем cookie для отслеживания сессии
                        resp = make_response(redirect(url_for('customer_main')))
                        resp.set_cookie('user_logged_in', 'true', max_age=60*60*24*30)  # cookie на 30 дней

                        flash('Авторизація пройшла успішно', 'success-customer-login')
                        return resp
                    else:
                        flash('Користувача не знайдено.', 'error-customer-login')
                else:
                    flash('Номер телефону або пароль невірний.', 'error-customer-login')
            else:
                flash('Будь ласка, заповніть всі поля.', 'error-customer-login')
        except Exception as e:
            print(f'Помилка при ідентифікації користувача: {str(e)}')
            flash(f'Помилка при ідентифікації користувача.', 'error-customer-login')
            return redirect(url_for('customer_login'))


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
    flash('Ви успішно вийшли з акаунту.', 'success-customer-logout')
    return response


@app.route('/customer/main', methods=['GET', 'POST'])
@login_required
def customer_main():
    # Получение методов оплаты
    payment_methods = db.session.execute(
        text("SELECT * FROM get_customer_payment_methods(:customer_id)"),
        {'customer_id': session.get('userid')}
    ).fetchall()

    # Получение сохраненных адресов
    saved_addresses = db.session.execute(
        text("SELECT * FROM get_customer_saved_addresses(:customer_id)"),
        {'customer_id': session.get('userid')}
    ).fetchall()

    if request.method == 'POST':
        try:
            selected_class = request.form.get('class')
            class_map = {'business': 1, 'comfort': 2, 'minivan': 3, 'economy': 4}
            vehicle_class = class_map.get(selected_class)

            if vehicle_class is None:
                flash(f"Невірний клас транспорту.", 'error-customer-main')

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
            flash(f"Помилка при збереженні.", 'error-customer-main')
            return redirect(url_for('customer_main'))

    return render_template('customer/Customer_Main.html', payment_methods=payment_methods,
                           saved_addresses=saved_addresses)


@app.route('/customer/profile', methods=['GET', 'POST'])
@login_required
def customer_profile():
    if request.method == 'POST':
        payment_id = request.form.get('payment_id')
        # Add address
        customer_id = session.get('userid')
        address_id = request.form.get('address_id')

        # Проверяем, что все необходимые данные присутствуют
        city_name = request.form.get('city_name')
        street = request.form.get('street')
        house_number = request.form.get('house_number')

        if city_name and street and house_number:
            try:
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
                flash('Адресу успішно додано!', 'success-customer-profile')
                return redirect(url_for('customer_profile'))
            except Exception as e:
                db.session.rollback()
                flash('Помилка при додаванні адреси.', 'error-customer-profile')
                return redirect(url_for('customer_profile'))


        # Удаление адреса
        elif address_id:
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
                flash('Адресу успішно видалено!', 'success-customer-profile')
                return redirect(url_for('customer_profile'))
            except Exception as e:
                db.session.rollback()
                flash('Помилка при видаленні адреси.', 'error-customer-profile')
                return redirect(url_for('customer_profile'))



                # Add payment
        elif 'card-number' in request.form:
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
                flash('Спосіб оплати успішно додано!', 'success-customer-profile')
                return redirect(url_for('customer_profile'))
            except Exception as e:
                db.session.rollback()
                flash(f'Помилка при додаванні способу оплати.', 'error-customer-profile')
                return redirect(url_for('customer_profile'))

        elif payment_id:
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
                flash('Спосіб оплати успішно видалено!', 'success-customer-profile')
            except Exception as e:
                db.session.rollback()
                flash(f'Помилка при видаленні способу оплати.', 'error-customer-profile')
            return redirect(url_for('customer_profile'))
        else:
            flash('Невірно введені дані.', 'error-customer-profile')
            return redirect(url_for('customer_profile'))

    # Display profile info
    profile_info = Customer.query.filter_by(customer_id=session.get("userid")).first()

    payment_methods = db.session.execute(
        text("SELECT * FROM get_customer_payment_methods(:customer_id)"),
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
                flash('Поїздка успішно скасована.', 'success-customer-rides')
                return redirect(url_for('customer_rides'))
            else:
                flash('Не вдалось відмінити поїздку.', 'error-customer-rides')

            if ride.status_id == 2:
                ride.status_id = 3
                db.session.commit()
                flash('Поїздка успішно завершена.', 'success-customer-rides')
                return redirect(url_for('customer_rides'))
            else:
                flash('Не вдалось завершити поїздку.', 'error-customer-rides')

    StartAddress = aliased(Address)
    FinalAddress = aliased(Address)

    rides = db.session.execute(
        text("""
        SELECT * 
        FROM customer_ride_history 
        WHERE customer_id = :customer_id 
        ORDER BY ride_id DESC
    """),
        {'customer_id': customer_id}
    ).fetchall()

    return render_template('customer/Customer_Rides.html', rides=rides)


@app.route('/customer/statistics', methods=['GET', 'POST'])
@login_required
def customer_statistics():
    customer_id = session.get("userid")  # Получаем ID пользователя из сессии

    # Класс транспорта, на котором пользователь чаще всего ездил
    most_used_class = db.session.execute(
        text("SELECT * FROM get_most_used_vehicle_class(:customer_id)"),
        {'customer_id': session.get("userid")}
    ).fetchone()

    # Данные для графиков
    current_year = datetime.now().year  # Текущий год

    # Количество поездок по месяцам
    rides_by_month = db.session.execute(
        text("SELECT * FROM get_rides_by_month(:customer_id)"),
        {'customer_id': session.get("userid")}
    ).fetchall()

    # Количество поездок по классам транспорта
    rides_by_class = db.session.execute(
        text("SELECT * FROM get_rides_by_vehicle_class(:customer_id)"),
        {'customer_id': session.get("userid")}
    ).fetchall()

    # Преобразуем данные в удобный формат для Chart.js
    months = list(range(1, 13))  # Все месяцы года
    rides_data = [0] * 12  # Количество поездок по месяцам
    for ride in rides_by_month:
        rides_data[int(ride.month) - 1] = ride.total_rides

    # Названия месяцев на украинском языке
    month_names = [
        "Січень", "Лютий", "Березень", "Квітень", "Травень", "Червень",
        "Липень", "Серпень", "Вересень", "Жовтень", "Листопад", "Грудень"
    ]

    # Данные для графика по классам транспорта
    class_labels = [row.class_type for row in rides_by_class]
    class_data = [row.total_rides for row in rides_by_class]

    return render_template('customer/Customer_Statistics.html',
                           most_used_class=most_used_class[0] if most_used_class else None,
                           rides_data=rides_data,
                           class_labels=class_labels,
                           class_data=class_data,
                           months=month_names,
                           current_year=current_year)


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
                    logger.info(f"Відновлено сесію для користувача {user_id}")
        except Exception as e:
            logger.error(f"Помилка відновлення сесії для користувача {user_id}: {e}")


@app.after_request
def redirect_to_signin(response):
    if response.status_code == 401:
        return redirect(url_for('customer_login') + '?next=' + request.url)
    return response
