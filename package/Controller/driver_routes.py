from datetime import datetime
from functools import wraps
from hashlib import sha256

from flask import render_template, request, redirect, flash, url_for, session, g, make_response
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from werkzeug.security import check_password_hash, generate_password_hash

from package import app, db
from package.Controller.session_manager import SessionManager, logger
from package.Model.customer_models import Customer, Address
from package.Model.driver_models import Driver, DriverVehicle
from package.Model.general_models import RideHistory, PaymentMethod, RideStatus

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

def create_driver_and_grant_role(phone_number, password, role):
    username = f"driver_{phone_number}"
    create_user_script = f"""
    CREATE USER {username} WITH PASSWORD '{password}';
    GRANT {role} TO {username};
    """
    sql_script = create_user_script.format(phone_number=phone_number, password=password, role=role)
    execute_sql_script(sql_script)

@app.route('/register/driver', methods=['GET', 'POST'])
def driver_register():
    if 'userid' in session:  # Если пользователь уже авторизован
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
            flash('Будь ласка, заповніть всі поля.')
        elif password != password2:
            flash('Паролі не співпадають.')
        else:
            try:
                date_of_birth = datetime.strptime(date_of_birth_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Некоректний формат дати народження. Використовуйте YYYY-MM-DD.')
            hash_pwd = hash_password(password)
            new_user = Driver(name=name, surname=surname, country_id=country_id, phone_number=phone_number,
                              date_of_birth=date_of_birth, sex=sex, email=email, drivers_license_number=drivers_license_number, passport_id=passport_id, driver_role=role)
            db.session.add(new_user)
            db.session.flush()
            db.session.commit()

            create_driver_and_grant_role(phone_number=phone_number, password=hash_pwd, role='driver')
            session['userrole'] = new_user.driver_role
            session['userid'] = new_user.driver_id

            db_connection = f"postgresql://driver_{phone_number}:{hash_pwd}@localhost:5432/TaxiCompany_DB"
            try:
                session_manager.create_session(new_user.driver_id, db_connection)
                check_db_connection(new_user.driver_id)
                g.driver_id = new_user.driver_id

                # Устанавливаем cookie для отслеживания сессии
                resp = make_response(redirect(url_for('driver_main')))
                resp.set_cookie('driver_logged_in', 'true', max_age=60*60*24*30)  # cookie на 30 дней

                flash('Реєстрація пройшла успішно', 'success')
                return resp
            except Exception as e:
                db.session.rollback()
                flash(f'Помилка при реєстрації: {str(e)}', 'error')
                return redirect(url_for('driver_register'))

    return render_template('driver/Driver_Register.html')


@app.route('/login/driver', methods=['GET', 'POST'])
def driver_login():
    if 'userid' in session:  # Если пользователь уже авторизован
        return redirect(url_for('driver_main'))  # Перенаправление на главную страницу
    if request.method == 'POST':
        phone_number = request.form.get('phone-number')
        password = request.form.get('password')

        if phone_number and password:
            user = Driver.query.filter_by(phone_number=phone_number).first()

            if user:
                session['userrole'] = user.driver_role
                session['userid'] = user.driver_id

                hash_pwd = hash_password(password)
                db_connection = f"postgresql://driver_{phone_number}:{hash_pwd}@localhost:5432/TaxiCompany_DB"

                try:
                    # Получаем или создаем сессию для пользователя
                    existing_session = session_manager.get_session(user.driver_id)
                    if existing_session:
                        logger.info(f"Используется существующая сессия для пользователя {user.driver_id}")
                    else:
                        session_manager.create_session(user.driver_id, db_connection)
                        check_db_connection(user.driver_id)
                        g.driver_id = user.driver_id  # Для передачи customer_id в другие обработчики
                    # Устанавливаем cookie для отслеживания сессии
                    resp = make_response(redirect(url_for('driver_main')))
                    resp.set_cookie('driver_logged_in', 'true', max_age=60*60*24*30)  # cookie на 30 дней

                    flash('Авторизація пройшла успішно', 'success')
                    return resp
                except Exception as e:
                    flash(f'Помилка при ідентифікації користувача: {str(e)}', 'error')
                    return redirect(url_for('driver_login'))

            else:
                flash('Номер телефону або пароль невірний.')
        else:
            flash('Будь ласка, заповніть всі поля.')

    return render_template('driver/Driver_Login.html')


@app.route('/logout/driver', methods=['GET', 'POST'])
@login_required
def driver_logout():
    user_id = session.get('userid')  # Получаем ID пользователя из сессии

    # Закрываем соединение с БД, если оно существует
    if user_id:
        db_session = session_manager.get_session(user_id)
        if db_session:
            db_session.close()  # Закрытие сессии SQLAlchemy
            session_manager.close_session(user_id)  # Удаление сессии из SessionManager

    session.clear()  # Очистка сессии Flask
    response = redirect(url_for('driver_login'))
    response.delete_cookie('driver_logged_in')
    flash('Ви успішно вийшли з акаунту.', 'success')
    return response


@app.route('/driver/main')
@login_required
def driver_main():
    return render_template('driver/Driver_Main.html')


@app.route('/driver/orders', methods=['GET', 'POST'])
@login_required
def driver_orders():
    # Получаем класс автомобиля водителя
    driver_vehicle = DriverVehicle.query.filter_by(driver_id=session.get("userid")).first()

    # Проверка активной поездки водителя
    active_ride = RideHistory.query.filter_by(driver_id=session.get("userid"), status_id=2).first()

    if request.method == 'POST':
        ride_id = request.form.get('ride_id')
        ride = RideHistory.query.get(ride_id)

        if ride and ride.class_id == driver_vehicle.vehicle.class_id:
            # Изменение статуса заказа
            if ride.status_id == 1:  # Замовлено
                ride.status_id = 2  # В дорозі
                ride.driver_id = session.get("userid")
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
                .filter(RideHistory.driver_id == session.get("userid")) \
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
                .filter(RideHistory.class_id == driver_vehicle_class_id) \
                .filter(
                (RideHistory.driver_id == session.get("userid")) |  # Водитель принял поездку
                (RideHistory.driver_id == None)  # Водитель еще не назначен
                ) \
                .filter(RideHistory.status_id != 4) \
                .order_by(RideHistory.driver_id.is_(None).desc()) \
                .order_by(RideHistory.ride_date.desc()) \
                .order_by(RideHistory.ride_id.desc()) \
                .all()
    else:
        rides = []  # Если у водителя нет автомобиля, возвращаем пустой список

    return render_template('driver/Driver_Orders.html', rides=rides)


@app.route('/driver/profile', methods=['GET', 'POST'])
def driver_profile():
    if request.method == 'POST':
        try:
            # Добавление транспортного средства
            if 'model-id' in request.form and 'number' in request.form and 'vin' in request.form and \
                    'color' in request.form and 'seats-quantity' in request.form and \
                    'date-of-manufacture' in request.form and 'maintenance-date' in request.form and \
                    'class-id' in request.form and 'is-company-vehicle' in request.form:

                driver_id = session.get("userid")
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
                flash('Vehicle added successfully!')

            # Удаление транспортного средства
            elif 'vehicle_id' in request.form:
                vehicle_id = request.form.get('vehicle_id')
                db.session.execute(
                    text("CALL delete_vehicle_for_driver(:vehicle_id)"),
                    {'vehicle_id': vehicle_id}
                )
                db.session.commit()
                flash('Vehicle deleted successfully!')
            else:
                flash('No valid action provided!')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}')

    # Получение данных для отображения
    profile_info = Driver.query.filter_by(driver_id=session.get("userid")).first()
    drivers_vehicles = DriverVehicle.query.filter_by(driver_id=session.get("userid")).all()

    return render_template('driver/Driver_Profile.html', profile_info=profile_info, drivers_vehicles=drivers_vehicles)

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
        return redirect(url_for('driver_login') + '?next=' + request.url)
    return response