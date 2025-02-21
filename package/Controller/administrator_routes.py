from datetime import datetime
from hashlib import sha256

from flask import render_template, request, redirect, flash, url_for, session, g, make_response
from sqlalchemy import text, func, extract, create_engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, OperationalError
from sqlalchemy.orm import aliased
from functools import wraps

from package import app, db
from package.Controller.session_manager import SessionManager, logger
from package.Model.administrator_models import Admin, BlockedUsers
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
        if 'adminid' not in session:  # Проверка на наличие сессии
            flash('Для доступу до цієї сторінки необхідно увійти', 'warning')
            return redirect(url_for('admin_login'))  # Перенаправление на страницу входа
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


def create_user_and_grant_role(email, password, role):
    username = f"admin_{email}"
    create_user_script = f"""
    CREATE USER {username} WITH PASSWORD '{password}';
    GRANT {role} TO {username};
    """
    sql_script = create_user_script.format(phone_number=email, password=password, role=role)
    execute_sql_script(sql_script)


@app.context_processor
def utility_processor():
    def is_user_blocked(user_id, user_type):
        return BlockedUsers.query.filter_by(user_id=user_id, user_type=user_type).first() is not None

    return dict(is_user_blocked=is_user_blocked)


def get_block_reason(user_id, user_type):
    blocked_user = BlockedUsers.query.filter_by(user_id=user_id, user_type=user_type).first()
    return blocked_user.block_reason if blocked_user else None


@app.route('/login/administrator', methods=['GET', 'POST'])
def admin_login():
    if 'adminid' in session:  # Если пользователь уже авторизован
        return redirect(url_for('admin_main'))  # Перенаправление на главную страницу

    if request.method == 'POST':
        email = request.form.get('email')
        email_without_domain = email.split('@')[0]
        password = request.form.get('password')

        hash_pwd = hash_password(password)

        try:
            if email and password:
                # Формуємо ім'я користувача для підключення до бази даних
                db_username = f"admin_{email_without_domain}"

                if verify_db_connection(db_username, hash_pwd):
                    user = Admin.query.filter_by(email=email).first()

                    if user:
                        session['adminrole'] = user.administrator_role
                        session['adminid'] = user.administrator_id

                        # Получаем или создаем сессию для пользователя
                        existing_session = session_manager.get_session(user.administrator_id)
                        if existing_session:
                            logger.info(f"Використовується існуюча сесія для користувача {user.administrator_id}")
                        else:
                            db_connection = f"postgresql://admin_{email_without_domain}:{hash_pwd}@localhost:5432/TaxiCompany_DB"
                            session_manager.create_session(user.administrator_id, db_connection)
                            check_db_connection(user.administrator_id)
                            g.administrator_id = user.administrator_id  # Для передачи customer_id в другие обработчики
                        # Устанавливаем cookie для отслеживания сессии
                        resp = make_response(redirect(url_for('admin_main')))
                        resp.set_cookie('admin_logged_in', 'true', max_age=60*60*24*30)  # cookie на 30 дней

                        flash('Авторизація пройшла успішно', 'success-admin-login')
                        return resp
                    else:
                        flash('Користувача не знайдено.', 'error-admin-login')
                else:
                    flash('Email або пароль невірний.', 'error-admin-login')
            else:
                flash('Будь ласка, заповніть всі поля.', 'error-admin-login')
        except Exception as e:
            print(f'Помилка при ідентифікації користувача: {str(e)}')
            flash(f'Помилка при ідентифікації користувача.', 'error-admin-login')
            return redirect(url_for('admin_login'))

    return render_template('administrator/Administrator_Login.html')


# @app.route('/register/administrator', methods=['GET', 'POST'])
# def admin_register():
#     if 'adminid' in session:  # Если пользователь уже авторизован
#         return redirect(url_for('admin_main'))  # Перенаправление на главную страницу
#     if request.method == 'POST':
#         name = request.form.get('name')
#         surname = request.form.get('surname')
#         email = request.form.get('email')
#         email_without_domain = email.split('@')[0]
#         password = request.form.get('password')
#         password2 = request.form.get('password2')
#         role = "admin"
#
#         hash_pwd = hash_password(password)
#         new_user = Admin(name=name, surname=surname, email=email, administrator_role=role)
#         db.session.add(new_user)
#         db.session.flush()
#         db.session.commit()
#
#         create_user_and_grant_role(email=email_without_domain, password=hash_pwd, role='admin')
#         session['adminrole'] = new_user.administrator_role
#         session['adminid'] = new_user.administrator_id
#
#         try:
#             db_connection = f"postgresql://admin_{email_without_domain}:{hash_pwd}@localhost:5432/TaxiCompany_DB"
#             session_manager.create_session(new_user.administrator_id, db_connection)
#             check_db_connection(new_user.administrator_id)
#             g.administrator_id = new_user.administrator_id
#
#             # Устанавливаем cookie для отслеживания сессии
#             resp = make_response(redirect(url_for('admin_main')))
#             resp.set_cookie('admin_logged_in', 'true', max_age=60*60*24*30)  # cookie на 30 дней
#
#             flash('Реєстрація пройшла успішно.', 'success-admin-register')
#             return resp
#         except Exception as e:
#             db.session.rollback()
#             flash(f'Помилка при реєстрації.', 'error-admin-register')
#             return redirect(url_for('admin_register'))
#
#     return render_template('administrator/Administrator_Register.html')


@app.route('/logout/administrator', methods=['GET', 'POST'])
@login_required
def admin_logout():
    user_id = session.get('adminid')  # Получаем ID пользователя из сессии

    # Закрываем соединение с БД, если оно существует
    if user_id:
        db_session = session_manager.get_session(user_id)
        if db_session:
            db_session.close()  # Закрытие сессии SQLAlchemy
            session_manager.close_session(user_id)  # Удаление сессии из SessionManager

    session.clear()  # Очистка сессии Flask
    response = redirect(url_for('admin_login'))
    response.delete_cookie('admin_logged_in')
    flash('Ви успішно вийшли з акаунту.', 'success-customer-logout')
    return response


@app.route('/administrator/main', methods=['GET', 'POST'])
@login_required
def admin_main():
    return render_template('administrator/Administrator_Main.html')


@app.route('/administrator/profile', methods=['GET', 'POST'])
@login_required
def admin_profile():
    if request.method == 'GET':

        # Display profile info
        profile_info = Admin.query.filter_by(administrator_id=session.get("adminid")).first()

        return render_template('administrator/Administrator_Profile.html', profile_info=profile_info)


@app.route('/administrator/history', methods=['GET', 'POST'])
@login_required
def admin_history():
    # Получаем все записи о блокировках
    blocked_users = BlockedUsers.query.join(Admin).add_columns(
        Admin.name.label('admin_name'),
        Admin.surname.label('admin_surname'),
        BlockedUsers.user_id,
        BlockedUsers.user_type,
        BlockedUsers.block_reason,
        BlockedUsers.blocked_at
    ).order_by(BlockedUsers.blocked_at.desc()).all()

    return render_template('administrator/Administrator_History.html', blocked_users=blocked_users)


@app.route('/administrator/users', methods=['GET', 'POST'])
@login_required
def admin_users():
    if request.method == 'POST':
        phone_number = request.form.get('phone_number')
        customers = Customer.query.filter_by(phone_number=phone_number).all()
        drivers = Driver.query.filter_by(phone_number=phone_number).all()
        return render_template('administrator/Administrator_Users.html', customers=customers, drivers=drivers)

    customers = Customer.query.all()
    drivers = Driver.query.all()
    return render_template('administrator/Administrator_Users.html', customers=customers, drivers=drivers, get_block_reason=get_block_reason)


@app.route('/administrator/block_user/<int:user_id>', methods=['POST'])
@login_required
def block_user(user_id):
    administrator_id = session.get('adminid')
    block_reason = request.form.get('block_reason')
    user_type = 'customer'  # или 'driver', в зависимости от контекста

    # Добавляем запись о блокировке
    blocked_user = BlockedUsers(
        administrator_id=administrator_id,
        user_id=user_id,
        user_type=user_type,
        block_reason=block_reason
    )
    db.session.add(blocked_user)
    db.session.commit()

    return redirect(url_for('admin_users'))


@app.route('/administrator/unblock_user/<int:user_id>', methods=['POST'])
@login_required
def unblock_user(user_id):
    user_type = 'customer'

    # Удаляем запись о блокировке
    blocked_user = BlockedUsers.query.filter_by(user_id=user_id, user_type=user_type).first()
    if blocked_user:
        db.session.delete(blocked_user)
        db.session.commit()

    return redirect(url_for('admin_users'))


@app.route('/administrator/block_driver/<int:driver_id>', methods=['POST'])
@login_required
def block_driver(driver_id):
    administrator_id = session.get('adminid')
    block_reason = request.form.get('block_reason')
    user_type = 'driver'  # или 'driver', в зависимости от контекста

    # Добавляем запись о блокировке
    blocked_user = BlockedUsers(
        administrator_id=administrator_id,
        user_id=driver_id,
        user_type=user_type,
        block_reason=block_reason
    )
    db.session.add(blocked_user)
    db.session.commit()

    return redirect(url_for('admin_users'))


@app.route('/administrator/unblock_driver/<int:driver_id>', methods=['POST'])
@login_required
def unblock_driver(driver_id):
    user_type = 'driver'

    # Удаляем запись о блокировке
    blocked_user = BlockedUsers.query.filter_by(user_id=driver_id, user_type=user_type).first()
    if blocked_user:
        db.session.delete(blocked_user)
        db.session.commit()

    return redirect(url_for('admin_users'))