from flask import Blueprint, request, jsonify
from datetime import datetime
from app import db
from app.models import Task, Column, Project, User, Board
from app.utils import auth_required, get_current_user, generate_task_code

tasks_bp = Blueprint('tasks', __name__)


@tasks_bp.route('/', methods=['GET'])
@auth_required
def get_tasks():
    """Получение списка задач с фильтрацией"""
    # Получаем параметры фильтрации
    args = request.args

    # Базовый запрос
    query = Task.query

    # Фильтр по приоритету
    if 'priority' in args:
        query = query.filter(Task.priority == args['priority'])

    # Фильтр по автору
    if 'author_id' in args:
        query = query.filter(Task.author_id == args['author_id'])

    # Фильтр по исполнителю
    if 'assignee_id' in args:
        query = query.filter(Task.assignee_id == args['assignee_id'])

    # Фильтр "мои задачи"
    if 'my_tasks' in args and args['my_tasks'].lower() == 'true':
        user = get_current_user()
        if user:
            query = query.filter(Task.assignee_id == user.id)

    # Фильтр по дате создания (с)
    if 'created_from' in args:
        try:
            created_from = datetime.fromisoformat(args['created_from'])
            query = query.filter(Task.created_at >= created_from)
        except ValueError:
            pass

    # Фильтр по дате создания (по)
    if 'created_to' in args:
        try:
            created_to = datetime.fromisoformat(args['created_to'])
            query = query.filter(Task.created_at <= created_to)
        except ValueError:
            pass

    # Выполнение запроса
    tasks = query.all()

    tasks_list = [{
        'id': task.id,
        'code': task.code,
        'title': task.title,
        'description': task.description,
        'priority': task.priority,
        'status': task.status,
        'estimated_time': task.estimated_time,
        'remaining_time': task.remaining_time,
        'spent_time': task.spent_time,
        'author': task.author.username if task.author else None,
        'assignee': task.assignee.username if task.assignee else None,
        'created_at': task.created_at.isoformat(),
        'updated_at': task.updated_at.isoformat(),
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None
    } for task in tasks]

    return jsonify({'tasks': tasks_list}), 200


@tasks_bp.route('/<int:task_id>', methods=['GET'])
@auth_required
def get_task(task_id):
    """Получение задачи по ID"""
    task = Task.query.get(task_id)

    if not task:
        return jsonify({'message': 'Задача не найдена'}), 404

    task_data = {
        'id': task.id,
        'code': task.code,
        'title': task.title,
        'description': task.description,
        'priority': task.priority,
        'status': task.status,
        'column_id': task.column_id,
        'estimated_time': task.estimated_time,
        'remaining_time': task.remaining_time,
        'spent_time': task.spent_time,
        'author_id': task.author_id,
        'author': task.author.username if task.author else None,
        'assignee_id': task.assignee_id,
        'assignee': task.assignee.username if task.assignee else None,
        'created_at': task.created_at.isoformat(),
        'updated_at': task.updated_at.isoformat(),
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None
    }

    return jsonify(task_data), 200


@tasks_bp.route('/', methods=['POST'])
@auth_required
def create_task():
    """Создание новой задачи с автоматическим помещением в беклог"""
    # Получаем текущего пользователя
    current_user = get_current_user()
    if not current_user:
        return jsonify({'message': 'Пользователь не аутентифицирован'}), 401

    data = request.get_json()

    # Проверка обязательных полей
    if not data or not data.get('title') or not data.get('board_id'):
        return jsonify({'message': 'Название задачи и ID доски обязательны'}), 400

    # Получаем доску
    board = Board.query.get(data['board_id'])
    if not board:
        return jsonify({'message': 'Доска не найдена'}), 404

    # Получаем проект для генерации кода задачи
    project = board.project

    # Находим колонку "Беклог" на доске
    backlog_column = Column.query.filter_by(board_id=board.id, name='Беклог').first()

    if not backlog_column:
        # Если колонка "Беклог" не найдена, берем первую колонку
        backlog_column = Column.query.filter_by(board_id=board.id).order_by(Column.order).first()

    if not backlog_column:
        return jsonify({'message': 'На доске нет колонок'}), 400

    # Генерируем код задачи
    task_code = generate_task_code(project.code)
    if not task_code:
        return jsonify({'message': 'Ошибка при генерации кода задачи'}), 500

    # Определяем исполнителя (если указан)
    assignee_id = None
    if data.get('assignee_id'):
        assignee = User.query.get(data['assignee_id'])
        if assignee:
            assignee_id = assignee.id

    # Создаем задачу
    new_task = Task(
        code=task_code,
        title=data['title'],
        description=data.get('description', ''),
        priority=data.get('priority', 'medium'),
        column_id=backlog_column.id,
        author_id=current_user.id,
        assignee_id=assignee_id,
        estimated_time=data.get('estimated_time', 0),
        remaining_time=data.get('estimated_time', 0)  # По умолчанию равно оценке
    )

    db.session.add(new_task)
    db.session.commit()

    return jsonify({
        'message': 'Задача успешно создана',
        'task': {
            'id': new_task.id,
            'code': new_task.code,
            'title': new_task.title,
            'description': new_task.description,
            'priority': new_task.priority,
            'status': new_task.status,
            'column_id': new_task.column_id,
            'column_name': backlog_column.name,
            'author_id': new_task.author_id,
            'assignee_id': new_task.assignee_id,
            'created_at': new_task.created_at.isoformat()
        }
    }), 201


# Оставляем старый метод для обратной совместимости
@tasks_bp.route('/column/<int:column_id>', methods=['POST'])
@auth_required
def create_task_in_column(column_id):
    """Создание новой задачи в колонке (устаревший метод)"""
    # Проверяем существование колонки
    column = Column.query.get(column_id)
    if not column:
        return jsonify({'message': 'Колонка не найдена'}), 404

    # Получаем текущего пользователя
    current_user = get_current_user()
    if not current_user:
        return jsonify({'message': 'Пользователь не аутентифицирован'}), 401

    data = request.get_json()

    # Проверка обязательных полей
    if not data or not data.get('title'):
        return jsonify({'message': 'Название задачи обязательно'}), 400

    # Получаем проект для генерации кода задачи
    board = column.board
    project = board.project

    # Генерируем код задачи
    task_code = generate_task_code(project.code)
    if not task_code:
        return jsonify({'message': 'Ошибка при генерации кода задачи'}), 500

    # Определяем исполнителя (если указан)
    assignee_id = None
    if data.get('assignee_id'):
        assignee = User.query.get(data['assignee_id'])
        if assignee:
            assignee_id = assignee.id

    # Создаем задачу
    new_task = Task(
        code=task_code,
        title=data['title'],
        description=data.get('description', ''),
        priority=data.get('priority', 'medium'),
        column_id=column_id,
        author_id=current_user.id,
        assignee_id=assignee_id,
        estimated_time=data.get('estimated_time', 0),
        remaining_time=data.get('estimated_time', 0)  # По умолчанию равно оценке
    )

    db.session.add(new_task)
    db.session.commit()

    return jsonify({
        'message': 'Задача успешно создана',
        'task': {
            'id': new_task.id,
            'code': new_task.code,
            'title': new_task.title,
            'description': new_task.description,
            'priority': new_task.priority,
            'status': new_task.status,
            'column_id': new_task.column_id,
            'author_id': new_task.author_id,
            'assignee_id': new_task.assignee_id,
            'created_at': new_task.created_at.isoformat()
        }
    }), 201


@tasks_bp.route('/<int:task_id>', methods=['PUT'])
@auth_required
def update_task(task_id):
    """Обновление задачи"""
    task = Task.query.get(task_id)

    if not task:
        return jsonify({'message': 'Задача не найдена'}), 404

    data = request.get_json()

    # Обновляем поля задачи
    if 'title' in data:
        task.title = data['title']

    if 'description' in data:
        task.description = data['description']

    if 'priority' in data:
        task.priority = data['priority']

    if 'column_id' in data:
        # Проверяем существование колонки
        column = Column.query.get(data['column_id'])
        if column:
            task.column_id = data['column_id']

            # Если задача перемещается в колонку "В работе", устанавливаем дату начала
            if column.name == 'В работе' and not task.started_at:
                task.started_at = datetime.utcnow()

            # Если задача перемещается в колонку "В продакшен", устанавливаем дату завершения
            if column.name == 'В продакшен' and not task.completed_at:
                task.completed_at = datetime.utcnow()

    if 'assignee_id' in data:
        # Проверяем существование пользователя
        assignee = None if data['assignee_id'] is None else User.query.get(data['assignee_id'])
        task.assignee_id = assignee.id if assignee else None

    if 'estimated_time' in data:
        task.estimated_time = data['estimated_time']

    if 'remaining_time' in data:
        task.remaining_time = data['remaining_time']

    if 'spent_time' in data:
        task.spent_time = data['spent_time']

    db.session.commit()

    return jsonify({
        'message': 'Задача успешно обновлена',
        'task': {
            'id': task.id,
            'code': task.code,
            'title': task.title,
            'description': task.description,
            'priority': task.priority,
            'status': task.status,
            'column_id': task.column_id,
            'author_id': task.author_id,
            'assignee_id': task.assignee_id,
            'estimated_time': task.estimated_time,
            'remaining_time': task.remaining_time,
            'spent_time': task.spent_time,
            'updated_at': task.updated_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None
        }
    }), 200


@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
@auth_required
def delete_task(task_id):
    """Удаление задачи"""
    task = Task.query.get(task_id)

    if not task:
        return jsonify({'message': 'Задача не найдена'}), 404

    # Проверяем права: только автор или менеджер может удалять задачу
    current_user = get_current_user()
    if not current_user or (current_user.id != task.author_id and not current_user.is_manager()):
        return jsonify({'message': 'У вас нет прав для удаления этой задачи'}), 403

    db.session.delete(task)
    db.session.commit()

    return jsonify({'message': 'Задача успешно удалена'}), 200