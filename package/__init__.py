import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__, template_folder=os.path.join('View', 'templates'), static_folder=os.path.join('View', 'static'))
app.secret_key = 'some secret salt'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost:5432/TaxiCompany_DB'
app.config['SESSION_COOKIE_NAME'] = 'taxi_session'  # Имя cookie для сессии
app.config['SESSION_PERMANENT'] = False  # Временная сессия
db = SQLAlchemy(app)
from package.Controller import driver_routes, customer_routes, administrator_routes, index
from package.Model import customer_models,  driver_models, administrator_models, general_models


app.app_context().push()
db.create_all()
