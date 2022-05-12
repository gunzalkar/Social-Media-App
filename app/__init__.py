from flask import Flask
from config import config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_moment import Moment

app = Flask(__name__)

app.config.from_object(config['default'])
config['default'].init_app(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'users.login'
login.login_message_category = 'info'
mail = Mail(app)
moment = Moment(app)

from app.users import users
from app.main import main

app.register_blueprint(users)
app.register_blueprint(main)