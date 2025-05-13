import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Инициализация расширений
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


def create_app():
    app = Flask(__name__)

    # Конфигурация приложения
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')

    # Инициализация расширений с приложением
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app)

    # Регистрация маршрутов
    from app.routes import auth_bp, users_bp, projects_bp, boards_bp, columns_bp, tasks_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(projects_bp, url_prefix='/api/projects')
    app.register_blueprint(boards_bp, url_prefix='/api/boards')
    app.register_blueprint(columns_bp, url_prefix='/api/columns')
    app.register_blueprint(tasks_bp, url_prefix='/api/tasks')

    # Создание таблиц в БД
    with app.app_context():
        db.create_all()
        from app.models import User, Role

        # Создание ролей, если их нет
        if not Role.query.first():
            manager_role = Role(name='manager')
            executor_role = Role(name='executor')
            db.session.add(manager_role)
            db.session.add(executor_role)
            db.session.commit()

    return app