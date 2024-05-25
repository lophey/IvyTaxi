from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

app = Flask(__name__)
app.secret_key = 'some secret salt'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost/TaxiCompany_DB'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.init_app(app)

from package import models, index, customer_routes, driver_routes

app.app_context().push()
db.create_all()
