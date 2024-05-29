import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager


app = Flask(__name__, template_folder=os.path.join('View', 'templates'), static_folder=os.path.join('View', 'static'))
app.secret_key = 'some secret salt'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost/TaxiCompany_DB'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.init_app(app)

from package.Controller import driver_routes, customer_routes, index
from package.Model import customer_models,  driver_models, general_models

app.app_context().push()
db.create_all()
