from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
import random
import string
from app.models import User, Project


def generate_task_code(project_code):
    """Генерирует код задачи на основе кода проекта"""
    # Получаем все задачи проекта, чтобы найти последний номер
    from app.models import Task, Column, Board, Project

    project = Project.query.filter_by(code=project_code).first()
    if not project:
        return None

    # Получаем все доски проекта
    boards = project.boards.all()
    board_ids = [board.id for board in boards]

    # Получаем все колонки для досок проекта
    from app import db
    columns = db.session.query(Column).filter(Column.board_id.in_(board_ids)).all() if board_ids else []
    column_ids = [column.id for column in columns]

    # Получаем все задачи для колонок
    tasks = db.session.query(Task).filter(Task.column_id.in_(column_ids)).all() if column_ids else []

    # Ищем коды задач, которые начинаются с кода проекта
    task_numbers = []
    for task in tasks:
        if task.code.startswith(project_code):
            # Извлекаем номер задачи из кода
            try:
                # Формат: PROJECT_CODE-NUMBER
                number_part = task.code.split('-')[1]
                task_numbers.append(int(number_part))
            except (IndexError, ValueError):
                continue

    # Определяем новый номер задачи
    next_task_number = max(task_numbers) + 1 if task_numbers else 1

    # Форматируем номер с ведущими нулями (например, 001, 002, ...)
    formatted_number = f"{next_task_number:03d}"

    # Возвращаем новый код задачи
    return f"{project_code}-{formatted_number}"


def manager_required(fn):
    """Декоратор для проверки роли менеджера"""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user or not user.is_manager():
            return jsonify({"message": "Требуются права менеджера"}), 403

        return fn(*args, **kwargs)

    return wrapper


def auth_required(fn):
    """Декоратор для проверки аутентификации"""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({"message": "Требуется аутентификация"}), 401

        return fn(*args, **kwargs)

    return wrapper


def get_current_user():
    """Получает текущего пользователя из JWT"""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        return User.query.get(user_id)
    except:
        return None