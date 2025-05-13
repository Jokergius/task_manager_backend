from flask import Blueprint
from app.routes.auth import auth_bp
from app.routes.users import users_bp
from app.routes.projects import projects_bp
from app.routes.boards import boards_bp
from app.routes.columns import columns_bp
from app.routes.tasks import tasks_bp

# Для прямого импорта
__all__ = ['auth_bp', 'users_bp', 'projects_bp', 'boards_bp', 'columns_bp', 'tasks_bp']