from contextlib import nullcontext
from datetime import datetime
from functools import wraps
from hashlib import sha256
from types import NoneType

from flask import render_template, request, redirect, flash, url_for, session, g, make_response
from sqlalchemy import text, func, extract, create_engine
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import aliased

from package import app, db
from package.Controller.session_manager import SessionManager, logger
from package.Model.administrator_models import BlockedUsers
from package.Model.customer_models import Customer, Address
from package.Model.driver_models import Driver, DriverVehicle
from package.Model.general_models import RideHistory, PaymentMethod, RideStatus

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
        if 'driverid' not in session:  # Проверка на наличие сессии
            flash('Для доступу до цієї сторінки необхідно увійти', 'warning')
            return redirect(url_for('driver_login'))  # Перенаправление на страницу входа
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


def create_driver_and_grant_role(phone_number, password, role):
    username = f"driver_{phone_number}"
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


@app.route('/register/driver', methods=['GET', 'POST'])
def driver_register():
    if 'driverid' in session:  # Если пользователь уже авторизован
        return redirect(url_for('driver_main'))  # Перенаправление на главную страницу
    if request.method == 'POST':
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
        role = "driver"
        if not (name or surname or country_id or phone_number or date_of_birth_str or sex or email
                or drivers_license_number or passport_id or password or password2):
            flash('Будь ласка, заповніть всі поля.', 'error-driver-register')
        elif password != password2:
            flash('Паролі не співпадають.', 'error-driver-register')
        else:
            try:
                date_of_birth = datetime.strptime(date_of_birth_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Некоректний формат дати народження. Використовуйте YYYY-MM-DD.', 'error-driver-register')
            hash_pwd = hash_password(password)
            new_user = Driver(name=name, surname=surname, country_id=country_id, phone_number=phone_number,
                              date_of_birth=date_of_birth, sex=sex, email=email, drivers_license_number=drivers_license_number, passport_id=passport_id, driver_role=role)
            db.session.add(new_user)
            db.session.flush()
            db.session.commit()

            create_driver_and_grant_role(phone_number=phone_number, password=hash_pwd, role='driver')
            session['driverrole'] = new_user.driver_role
            session['driverid'] = new_user.driver_id

            try:
                db_connection = f"postgresql://driver_{phone_number}:{hash_pwd}@localhost:5432/TaxiCompany_DB"
                session_manager.create_session(new_user.driver_id, db_connection)
                check_db_connection(new_user.driver_id)
                g.driver_id = new_user.driver_id

                # Устанавливаем cookie для отслеживания сессии
                resp = make_response(redirect(url_for('driver_profile')))
                resp.set_cookie('driver_logged_in', 'true', max_age=60*60*24*30)  # cookie на 30 дней

                flash('Реєстрація пройшла успішно', 'success-driver-register')
                return resp
            except Exception as e:
                db.session.rollback()
                flash(f'Помилка при реєстрації.', 'error-driver-register')
                return redirect(url_for('driver_register'))

    return render_template('driver/Driver_Register.html')


@app.route('/login/driver', methods=['GET', 'POST'])
def driver_login():
    if 'driverid' in session:  # Если пользователь уже авторизован
        return redirect(url_for('driver_main'))  # Перенаправление на главную страницу

    if request.method == 'POST':
        phone_number = request.form.get('phone-number')
        password = request.form.get('password')
        hash_pwd = hash_password(password)

        if phone_number and password:
            # Формуємо ім'я користувача для підключення до бази даних
            db_username = f"driver_{phone_number}"

            if verify_db_connection(db_username, hash_pwd):
                user = Driver.query.filter_by(phone_number=phone_number).first()

                if user:
                    if is_user_blocked(user.driver_id, user.driver_role):
                        flash('Ваш акаунт заблоковано. Причина: ' + get_block_reason(user.driver_id, user.driver_role), 'error-driver-login')
                        return redirect(url_for('driver_login'))
                    session['driverrole'] = user.driver_role
                    session['driverid'] = user.driver_id

                    try:
                        # Получаем или создаем сессию для пользователя
                        existing_session = session_manager.get_session(user.driver_id)
                        if existing_session:
                            logger.info(f"Используется существующая сессия для пользователя {user.driver_id}")
                        else:
                            db_connection = f"postgresql://driver_{phone_number}:{hash_pwd}@localhost:5432/TaxiCompany_DB"
                            session_manager.create_session(user.driver_id, db_connection)
                            check_db_connection(user.driver_id)
                            g.driver_id = user.driver_id  # Для передачи customer_id в другие обработчики
                        # Устанавливаем cookie для отслеживания сессии
                        resp = make_response(redirect(url_for('driver_orders')))
                        resp.set_cookie('driver_logged_in', 'true', max_age=60*60*24*30)  # cookie на 30 дней

                        flash('Авторизація пройшла успішно', 'success-driver-login')
                        return resp
                    except Exception as e:
                        print(f'Помилка при ідентифікації користувача: {str(e)}')
                        flash(f'Помилка при ідентифікації користувача.', 'error')
                        return redirect(url_for('driver_login'))
                else:
                    flash('Користувача не знайдено.', 'error-driver-login')
                    return redirect(url_for('driver_login'))
            else:
                flash('Номер телефону або пароль невірний.', 'error-driver-login')
                return redirect(url_for('driver_login'))
        else:
            flash('Будь ласка, заповніть всі поля.', 'error-driver-login')
            return redirect(url_for('driver_login'))

    return render_template('driver/Driver_Login.html')


@app.route('/logout/driver', methods=['GET', 'POST'])
@login_required
def driver_logout():
    user_id = session.get('driverid')  # Получаем ID пользователя из сессии

    # Закрываем соединение с БД, если оно существует
    if user_id:
        db_session = session_manager.get_session(user_id)
        if db_session:
            db_session.close()  # Закрытие сессии SQLAlchemy
            session_manager.close_session(user_id)  # Удаление сессии из SessionManager

    session.clear()  # Очистка сессии Flask
    response = redirect(url_for('driver_login'))
    response.delete_cookie('driver_logged_in')
    flash('Ви успішно вийшли з акаунту.', 'success-driver-logout')
    return response


@app.route('/driver/main')
@login_required
def driver_main():
    return render_template('driver/Driver_Main.html')


@app.route('/driver/orders', methods=['GET', 'POST'])
@login_required
def driver_orders():
    # Получаем класс автомобиля водителя
    driver_vehicle = DriverVehicle.query.filter_by(driver_id=session.get("driverid")).first()

    # Проверка активной поездки водителя
    active_ride = RideHistory.query.filter_by(driver_id=session.get("driverid"), status_id=2).first()

    if request.method == 'POST':
        ride_id = request.form.get('ride_id')
        ride = RideHistory.query.get(ride_id)

        if ride and ride.class_id == driver_vehicle.vehicle.class_id:
            # Изменение статуса заказа
            if ride.status_id == 1:  # Замовлено
                ride.status_id = 2  # В дорозі
                ride.driver_id = session.get("driverid")
                ride.vehicle_id = driver_vehicle.vehicle.vehicle_id
                db.session.commit()
                flash('Поїздка успішно підтверджена.', 'success-driver-orders')
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
                Customer.name.label('customer_name'),
                StartAddress.street.label('start_street'),
                StartAddress.house_number.label('start_house_number'),
                FinalAddress.street.label('final_street'),
                FinalAddress.house_number.label('final_house_number'),
                PaymentMethod.method_name,
                RideStatus.status_name
            ).join(Customer, RideHistory.customer_id == Customer.customer_id, isouter=True) \
                .join(StartAddress, RideHistory.ride_start_id == StartAddress.address_id, isouter=True) \
                .join(FinalAddress, RideHistory.ride_final_id == FinalAddress.address_id, isouter=True) \
                .join(PaymentMethod, RideHistory.method_id == PaymentMethod.method_id, isouter=True) \
                .join(RideStatus, RideHistory.status_id == RideStatus.status_id, isouter=True) \
                .filter(RideHistory.class_id == driver_vehicle_class_id) \
                .filter(RideHistory.driver_id == session.get("driverid")) \
                .filter(RideHistory.status_id != 4) \
                .filter(RideHistory.status_id != 3) \
                .order_by(RideHistory.ride_date.desc()) \
                .all()
        else:
            # Фильтруем поездки по классу автомобиля
            rides = db.session.query(
                RideHistory,
                Customer.name.label('customer_name'),
                StartAddress.street.label('start_street'),
                StartAddress.house_number.label('start_house_number'),
                FinalAddress.street.label('final_street'),
                FinalAddress.house_number.label('final_house_number'),
                PaymentMethod.method_name,
                RideStatus.status_name
            ).join(Customer, RideHistory.customer_id == Customer.customer_id, isouter=True) \
                .join(StartAddress, RideHistory.ride_start_id == StartAddress.address_id, isouter=True) \
                .join(FinalAddress, RideHistory.ride_final_id == FinalAddress.address_id, isouter=True) \
                .join(PaymentMethod, RideHistory.method_id == PaymentMethod.method_id, isouter=True) \
                .join(RideStatus, RideHistory.status_id == RideStatus.status_id, isouter=True) \
                .filter(
                (RideHistory.driver_id == session.get("driverid"))  | # Водитель принял поездку
                (RideHistory.driver_id == None) & (RideHistory.class_id == driver_vehicle_class_id) # Водитель еще не назначен
                ) \
                .filter(RideHistory.status_id != 4) \
                .order_by(RideHistory.driver_id.is_(None).desc()) \
                .order_by(RideHistory.ride_date.desc()) \
                .order_by(RideHistory.ride_id.desc()) \
                .all()

    elif driver_vehicle is None :
        # Фильтруем поездки по классу автомобиля
        rides = db.session.query(
            RideHistory,
            Customer.name.label('customer_name'),
            StartAddress.street.label('start_street'),
            StartAddress.house_number.label('start_house_number'),
            FinalAddress.street.label('final_street'),
            FinalAddress.house_number.label('final_house_number'),
            PaymentMethod.method_name,
            RideStatus.status_name
        ).join(Customer, RideHistory.customer_id == Customer.customer_id, isouter=True) \
            .join(StartAddress, RideHistory.ride_start_id == StartAddress.address_id, isouter=True) \
            .join(FinalAddress, RideHistory.ride_final_id == FinalAddress.address_id, isouter=True) \
            .join(PaymentMethod, RideHistory.method_id == PaymentMethod.method_id, isouter=True) \
            .join(RideStatus, RideHistory.status_id == RideStatus.status_id, isouter=True) \
            .filter(
            (RideHistory.driver_id == session.get("driverid")) # Водитель принял поездку
            ) \
            .filter(RideHistory.status_id == 3) \
            .order_by(RideHistory.driver_id.is_(None).desc()) \
            .order_by(RideHistory.ride_date.desc()) \
            .order_by(RideHistory.ride_id.desc()) \
            .all()

    return render_template('driver/Driver_Orders.html', rides=rides)


@app.route('/driver/profile', methods=['GET', 'POST'])
@login_required
def driver_profile():
    if request.method == 'POST':
        try:
            # Добавление транспортного средства
            if 'model-id' in request.form and 'number' in request.form and 'vin' in request.form and \
                    'color' in request.form and 'seats-quantity' in request.form and \
                    'date-of-manufacture' in request.form and 'maintenance-date' in request.form and \
                    'class-id' in request.form and 'is-company-vehicle' in request.form:

                driver_id = session.get("driverid")
                model_id = request.form.get('model-id')
                number = request.form.get('number')
                vin = request.form.get('vin')
                color = request.form.get('color')
                seats_quantity = request.form.get('seats-quantity')
                date_of_manufacture = request.form.get('date-of-manufacture')
                maintenance_date = request.form.get('maintenance-date')
                class_id = request.form.get('class-id')
                is_company_vehicle = request.form.get('is-company-vehicle') == 'Yes'

                db.session.execute(
                    text("""
                        CALL add_vehicle_for_driver(
                            :driver_id, :model_id, :number, :vin, :color, 
                            :seats_quantity, :date_of_manufacture, :maintenance_date, 
                            :class_id, :is_company_vehicle, NULL
                        )
                    """),
                    {
                        'driver_id': driver_id,
                        'model_id': model_id,
                        'number': number,
                        'vin': vin,
                        'color': color,
                        'seats_quantity': seats_quantity,
                        'date_of_manufacture': date_of_manufacture,
                        'maintenance_date': maintenance_date,
                        'class_id': class_id,
                        'is_company_vehicle': is_company_vehicle,
                    }
                )
                db.session.commit()
                flash('Транспорт успішно доданий!', 'success-driver-profile')

            # Удаление транспортного средства
            elif 'vehicle_id' in request.form:
                vehicle_id = request.form.get('vehicle_id')
                db.session.execute(
                    text("CALL delete_vehicle_for_driver(:vehicle_id)"),
                    {'vehicle_id': vehicle_id}
                )
                db.session.commit()
                flash('Транспортний засіб успішно видалено!', 'success-driver-profile')
            else:
                flash('Не вказано дійсну дію!', 'error-driver-profile')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}')

    # Получение данных для отображения
    profile_info = Driver.query.filter_by(driver_id=session.get("driverid")).first()
    drivers_vehicles = DriverVehicle.query.filter_by(driver_id=session.get("driverid")).all()

    return render_template('driver/Driver_Profile.html', profile_info=profile_info, drivers_vehicles=drivers_vehicles)


@app.route('/driver/ratings')
@login_required
def driver_ratings():
    driver_id = session.get("driverid")  # Получаем ID водителя из сессии

    # Общая сумма заработка
    total_earned = db.session.execute(
        text("SELECT get_driver_total_earned(:driver_id)"),
        {'driver_id': driver_id}
    ).scalar()

    # ТОП-3 водителей
    top_earners = db.session.execute(
        text("SELECT * FROM get_top_earners()")
    ).fetchall()

    # Проверка в ТОП-3
    current_driver_in_top_earners = db.session.execute(
        text("SELECT is_driver_in_top(:driver_id)"),
        {'driver_id': driver_id}
    ).scalar()

    # Текущий ранг водителя
    current_driver_earned_rank = db.session.execute(
        text("SELECT get_driver_rank(:driver_id)"),
        {'driver_id': driver_id}
    ).scalar()

        # ТОП-3 водителей по поездкам
    top_rides = db.session.execute(
        text("SELECT * FROM get_top_rides()")
    ).fetchall()

    # Проверка в ТОП-3
    current_driver_in_top_rides = db.session.execute(
        text("SELECT is_driver_in_top_rides(:driver_id)"),
        {'driver_id': driver_id}
    ).scalar()

    # Текущий ранг по поездкам
    current_driver_rides_rank = db.session.execute(
        text("SELECT get_driver_rides_rank(:driver_id)"),
        {'driver_id': driver_id}
    ).scalar() or 0

    driver_rides_rank = db.session.query(
        Driver.driver_id,
        func.count(RideHistory.ride_id).label('total_rides')
    ).join(RideHistory, RideHistory.driver_id == Driver.driver_id).filter(
        RideHistory.status_id == 3
    ).group_by(Driver.driver_id).order_by(func.count(RideHistory.ride_id).desc()).all()

    # ТОП-3 водителей по стоимости поездок
    top_expensive_rides = db.session.execute(
        text("SELECT * FROM get_top_expensive_rides()")
    ).fetchall()

    # Проверка в ТОП-3
    current_driver_in_top_expensive_rides = db.session.execute(
        text("SELECT is_driver_in_top_expensive(:driver_id)"),
        {'driver_id': driver_id}
    ).scalar()

    # Текущий ранг по стоимости
    current_driver_expensive_rides_rank = db.session.execute(
        text("SELECT get_driver_expensive_rank(:driver_id)"),
        {'driver_id': driver_id}
    ).scalar() or 0

    driver_expensive_rides_rank = db.session.query(
        Driver.driver_id,
        func.max(RideHistory.price).label('max_price')
    ).join(RideHistory, RideHistory.driver_id == Driver.driver_id).filter(
        RideHistory.status_id == 3
    ).group_by(Driver.driver_id).order_by(func.max(RideHistory.price).desc()).all()

    # Данные для графиков
    current_year = datetime.now().year  # Текущий год
    rides_by_month = db.session.query(
        extract('month', RideHistory.ride_date).label('month'),
        func.count(RideHistory.ride_id).label('total_rides')
    ).filter(
        RideHistory.driver_id == driver_id,
        RideHistory.status_id == 3,
        extract('year', RideHistory.ride_date) == current_year
    ).group_by('month').order_by('month').all()

    earnings_by_month = db.session.query(
        extract('month', RideHistory.ride_date).label('month'),
        func.sum(RideHistory.price).label('total_earned')
    ).filter(
        RideHistory.driver_id == driver_id,
        RideHistory.status_id == 3,
        extract('year', RideHistory.ride_date) == current_year
    ).group_by('month').order_by('month').all()

    # Преобразуем данные в удобный формат для Chart.js
    months = list(range(1, 13))  # Все месяцы года
    rides_data = [0] * 12  # Количество поездок по месяцам
    earnings_data = [0] * 12  # Сумма заработка по месяцам

    for ride in rides_by_month:
        rides_data[int(ride.month) - 1] = ride.total_rides

    for earning in earnings_by_month:
        earnings_data[int(earning.month) - 1] = float(earning.total_earned or 0)

    # Названия месяцев на украинском языке
    month_names = [
        "Січень", "Лютий", "Березень", "Квітень", "Травень", "Червень",
        "Липень", "Серпень", "Вересень", "Жовтень", "Листопад", "Грудень"
    ]
    # Получаем имя текущего водителя
    current_driver_name = db.session.query(Driver.name).filter(Driver.driver_id == driver_id).scalar()

    return render_template('driver/Driver_Ratings.html',
                           total_earned=total_earned,
                           top_earners=top_earners,
                           top_rides=top_rides,
                           top_expensive_rides=top_expensive_rides,
                           current_driver_earned_rank=current_driver_earned_rank,
                           current_driver_rides_rank=current_driver_rides_rank,
                           current_driver_expensive_rides_rank=current_driver_expensive_rides_rank,

                           current_driver_id=driver_id,
                           current_driver_name=current_driver_name,
                           driver_expensive_rides_rank=driver_expensive_rides_rank,
                           driver_rides_rank=driver_rides_rank,
                           current_driver_in_top_earners=current_driver_in_top_earners,
                           current_driver_in_top_rides=current_driver_in_top_rides,
                           current_driver_in_top_expensive_rides=current_driver_in_top_expensive_rides,

                           rides_data=rides_data,
                           earnings_data=earnings_data,
                           months=month_names,
                           current_year=current_year,
                           enumerate=enumerate)


@app.before_request
def load_logged_in_user():
    user_id = session.get('driverid')
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
        return redirect(url_for('driver_login') + '?next=' + request.url)
    return response