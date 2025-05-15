from flask import Blueprint, request, jsonify
from datetime import datetime
from app import db
from app.models import Task, Column, Project, User, Board, TimeLog
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
            'author': current_user.username,
            'assignee_id': new_task.assignee_id,
            'assignee': User.query.get(assignee_id).username if assignee_id else None,
            'estimated_time': new_task.estimated_time,
            'remaining_time': new_task.remaining_time,
            'spent_time': new_task.spent_time,
            'created_at': new_task.created_at.isoformat(),
            'updated_at': new_task.updated_at.isoformat(),
            'started_at': None,
            'completed_at': None
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
            'column_name': column.name,
            'author_id': new_task.author_id,
            'author': current_user.username,
            'assignee_id': new_task.assignee_id,
            'assignee': User.query.get(assignee_id).username if assignee_id else None,
            'estimated_time': new_task.estimated_time,
            'remaining_time': new_task.remaining_time,
            'spent_time': new_task.spent_time,
            'created_at': new_task.created_at.isoformat(),
            'updated_at': new_task.updated_at.isoformat(),
            'started_at': None,
            'completed_at': None
        }
    }), 201


@tasks_bp.route('/<int:task_id>', methods=['PUT'])
@auth_required
def update_task(task_id):
    """Обновление задачи"""
    task = Task.query.get(task_id)

    if not task:
        return jsonify({'message': 'Задача не найдена'}), 404

    current_user = get_current_user()
    if not current_user:
        return jsonify({'message': 'Пользователь не аутентифицирован'}), 401

    data = request.get_json()

    # Обновляем поля задачи
    if 'title' in data:
        task.title = data['title']

    if 'description' in data:
        task.description = data['description']

    if 'priority' in data:
        task.priority = data['priority']

    if 'column_id' in data:
        if not (current_user.id == task.author_id or 
                current_user.id == task.assignee_id or 
                current_user.is_manager()):
            return jsonify({'message': 'У вас нет прав для перемещения этой задачи'}), 403
            
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


@tasks_bp.route('/<int:task_id>/time', methods=['POST'])
@auth_required
def log_task_time(task_id):
    """Логирование затраченного времени на задачу"""
    task = Task.query.get(task_id)

    if not task:
        return jsonify({'message': 'Задача не найдена'}), 404

    # Получаем текущего пользователя
    current_user = get_current_user()
    if not current_user:
        return jsonify({'message': 'Пользователь не аутентифицирован'}), 401

    data = request.get_json()

    # Проверка необходимых полей
    if not data or 'spent_hours' not in data:
        return jsonify({'message': 'Затраченное время (spent_hours) обязательно для указания'}), 400

    spent_hours = float(data['spent_hours'])
    if spent_hours <= 0:
        return jsonify({'message': 'Затраченное время должно быть положительным числом'}), 400

    # Проверяем, от имени какого пользователя логируется время
    log_user_id = None
    if 'user_id' in data and current_user.is_manager():
        # Менеджер может логировать время от имени любого пользователя
        log_user = User.query.get(data['user_id'])
        if log_user:
            log_user_id = log_user.id
        else:
            return jsonify({'message': 'Указанный пользователь не найден'}), 404
    else:
        # Обычный пользователь может логировать только своё время
        # Проверка прав: только исполнитель или менеджер может логировать время
        if current_user.id != task.assignee_id and not current_user.is_manager():
            return jsonify({'message': 'У вас нет прав для логирования времени для этой задачи'}), 403
        log_user_id = current_user.id

    # Добавляем информацию о том, кто залогировал время
    logged_by = current_user.username

    # Добавляем затраченное время
    task.spent_time += spent_hours

    # Если указано оставшееся время, обновляем его
    if 'remaining_hours' in data:
        task.remaining_time = float(data['remaining_hours'])
    # Иначе автоматически уменьшаем оставшееся время
    else:
        # Не допускаем отрицательных значений
        task.remaining_time = max(0, task.remaining_time - spent_hours)

    # Создаем запись о логировании времени
    time_log = TimeLog(
        task_id=task.id,
        user_id=log_user_id,
        logged_by_id=current_user.id,
        spent_hours=spent_hours,
        remaining_hours=task.remaining_time,
        comment=data.get('comment', '')
    )
    
    db.session.add(time_log)
    db.session.commit()

    # Получаем имя пользователя, от имени которого залогировано время
    log_username = User.query.get(log_user_id).username if log_user_id else None

    return jsonify({
        'message': 'Время успешно залогировано',
        'time_log': {
            'id': time_log.id,
            'spent_hours': spent_hours,
            'remaining_hours': task.remaining_time,
            'logged_by': logged_by,
            'logged_for_user': log_username,
            'comment': time_log.comment,
            'timestamp': time_log.created_at.isoformat()
        },
        'task': {
            'id': task.id,
            'code': task.code,
            'title': task.title,
            'description': task.description,
            'priority': task.priority,
            'status': task.status,
            'column_id': task.column_id,
            'author_id': task.author_id,
            'author': task.author.username if task.author else None,
            'assignee_id': task.assignee_id,
            'assignee': task.assignee.username if task.assignee else None,
            'estimated_time': task.estimated_time,
            'remaining_time': task.remaining_time,
            'spent_time': task.spent_time,
            'updated_at': task.updated_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None
        }
    }), 200


@tasks_bp.route('/board/<int:board_id>/task/<int:task_id>', methods=['GET'])
@auth_required
def get_task_in_board_context(board_id, task_id):
    """Получение детальной информации о задаче в контексте доски"""
    # Проверяем существование доски
    board = Board.query.get(board_id)
    if not board:
        return jsonify({'message': 'Доска не найдена'}), 404

    # Получаем задачу
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'message': 'Задача не найдена'}), 404

    # Проверяем, что задача относится к доске
    column = Column.query.get(task.column_id)
    if not column or column.board_id != board_id:
        return jsonify({'message': 'Задача не принадлежит указанной доске'}), 400

    # Формируем детальную информацию о задаче
    task_data = {
        'id': task.id,
        'code': task.code,
        'title': task.title,
        'description': task.description,
        'priority': task.priority,
        'status': task.status,
        'column_id': task.column_id,
        'column_name': column.name,
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
        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
        'board_id': board_id,
        'project_id': board.project_id,
        'project_name': board.project.name if board.project else None
    }

    return jsonify(task_data), 200


@tasks_bp.route('/<int:task_id>/estimate', methods=['POST'])
@auth_required
def update_task_estimate(task_id):
    """Обновление оценки времени задачи"""
    task = Task.query.get(task_id)

    if not task:
        return jsonify({'message': 'Задача не найдена'}), 404

    # Проверяем права: только менеджер или автор задачи может обновлять оценку
    current_user = get_current_user()
    if not current_user or (current_user.id != task.author_id and not current_user.is_manager()):
        return jsonify({'message': 'У вас нет прав для обновления оценки этой задачи'}), 403

    data = request.get_json()

    # Проверка необходимых полей
    if not data or 'estimated_hours' not in data:
        return jsonify({'message': 'Оценка времени (estimated_hours) обязательна для указания'}), 400

    estimated_hours = float(data['estimated_hours'])
    if estimated_hours < 0:
        return jsonify({'message': 'Оценка времени не может быть отрицательной'}), 400

    # Обновляем оценку времени
    task.estimated_time = estimated_hours

    # Если не указано оставшееся время, обновляем его на основе оценки и затраченного времени
    if 'remaining_hours' not in data:
        # Вычисляем оставшееся время как разницу между оценкой и затраченным временем,
        # но не меньше нуля
        task.remaining_time = max(0, estimated_hours - task.spent_time)
    else:
        # Если оставшееся время указано явно, используем его
        task.remaining_time = float(data['remaining_hours'])

    db.session.commit()

    return jsonify({
        'message': 'Оценка времени успешно обновлена',
        'task': {
            'id': task.id,
            'code': task.code,
            'title': task.title,
            'priority': task.priority,
            'status': task.status,
            'estimated_time': task.estimated_time,
            'remaining_time': task.remaining_time,
            'spent_time': task.spent_time,
            'updated_at': task.updated_at.isoformat()
        }
    }), 200


@tasks_bp.route('/<int:task_id>/time-logs', methods=['GET'])
@auth_required
def get_task_time_logs(task_id):
    """Получение истории логирования времени для задачи"""
    task = Task.query.get(task_id)

    if not task:
        return jsonify({'message': 'Задача не найдена'}), 404
    
    # Получение параметров фильтрации
    args = request.args
    
    # Базовый запрос
    query = TimeLog.query.filter_by(task_id=task_id)
    
    # Фильтр по пользователю (для кого залогировано время)
    if 'user_id' in args:
        query = query.filter(TimeLog.user_id == args['user_id'])
    
    # Фильтр по логировщику (кто залогировал время)
    if 'logged_by_id' in args:
        query = query.filter(TimeLog.logged_by_id == args['logged_by_id'])
    
    # Фильтр по дате (с)
    if 'from_date' in args:
        try:
            from_date = datetime.fromisoformat(args['from_date'])
            query = query.filter(TimeLog.created_at >= from_date)
        except ValueError:
            pass
    
    # Фильтр по дате (по)
    if 'to_date' in args:
        try:
            to_date = datetime.fromisoformat(args['to_date'])
            query = query.filter(TimeLog.created_at <= to_date)
        except ValueError:
            pass
    
    # Сортировка по дате (по умолчанию - от новых к старым)
    sort_order = args.get('sort', 'desc').lower()
    if sort_order == 'asc':
        query = query.order_by(TimeLog.created_at.asc())
    else:
        query = query.order_by(TimeLog.created_at.desc())
    
    # Пагинация
    page = int(args.get('page', 1))
    per_page = int(args.get('per_page', 10))
    time_logs_paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    time_logs = []
    for log in time_logs_paginated.items:
        time_logs.append({
            'id': log.id,
            'task_id': log.task_id,
            'user': {
                'id': log.user_id,
                'username': log.user.username if log.user else None
            },
            'logged_by': {
                'id': log.logged_by_id,
                'username': log.logger.username if log.logger else None
            },
            'spent_hours': log.spent_hours,
            'remaining_hours': log.remaining_hours,
            'comment': log.comment,
            'created_at': log.created_at.isoformat()
        })
    
    response = {
        'time_logs': time_logs,
        'pagination': {
            'total_items': time_logs_paginated.total,
            'per_page': per_page,
            'current_page': page,
            'total_pages': time_logs_paginated.pages
        },
        'task': {
            'id': task.id,
            'code': task.code,
            'title': task.title,
            'total_spent_time': task.spent_time
        }
    }
    
    return jsonify(response), 200


@tasks_bp.route('/time-summary', methods=['GET'])
@auth_required
def get_time_summary():
    """
    Получение сводной информации о затраченном времени по задачам.
    Только для менеджеров.
    """
    # Проверка прав доступа
    current_user = get_current_user()
    if not current_user or not current_user.is_manager():
        return jsonify({'message': 'Доступ запрещен. Требуются права менеджера.'}), 403
    
    # Получение параметров фильтрации
    args = request.args
    
    # Определение фильтров
    filters = []
    
    # Фильтр по проекту
    if 'project_id' in args:
        project_id = args['project_id']
        # Получаем все доски проекта
        boards = Board.query.filter_by(project_id=project_id).all()
        board_ids = [board.id for board in boards]
        
        # Получаем все колонки для досок проекта
        columns = Column.query.filter(Column.board_id.in_(board_ids)).all() if board_ids else []
        column_ids = [column.id for column in columns]
        
        # Добавляем фильтр по колонкам
        if column_ids:
            filters.append(Task.column_id.in_(column_ids))
    
    # Фильтр по доске
    if 'board_id' in args:
        board_id = args['board_id']
        # Получаем все колонки доски
        columns = Column.query.filter_by(board_id=board_id).all()
        column_ids = [column.id for column in columns]
        
        # Добавляем фильтр по колонкам
        if column_ids:
            filters.append(Task.column_id.in_(column_ids))
    
    # Фильтр по пользователю
    if 'user_id' in args:
        user_id = args['user_id']
        filters.append(TimeLog.user_id == user_id)
    
    # Фильтр по периоду времени
    if 'from_date' in args:
        try:
            from_date = datetime.fromisoformat(args['from_date'])
            filters.append(TimeLog.created_at >= from_date)
        except ValueError:
            pass
    
    if 'to_date' in args:
        try:
            to_date = datetime.fromisoformat(args['to_date'])
            filters.append(TimeLog.created_at <= to_date)
        except ValueError:
            pass
    
    # Запрос для получения сводной информации
    time_logs = db.session.query(
        TimeLog.user_id,
        User.username,
        db.func.sum(TimeLog.spent_hours).label('total_spent_hours'),
        db.func.count(TimeLog.id).label('log_count')
    ).join(
        User, TimeLog.user_id == User.id
    ).join(
        Task, TimeLog.task_id == Task.id
    )
    
    # Применяем фильтры
    for f in filters:
        time_logs = time_logs.filter(f)
    
    # Группировка по пользователю
    time_logs = time_logs.group_by(TimeLog.user_id, User.username)
    
    # Сортировка по общему затраченному времени (по убыванию)
    time_logs = time_logs.order_by(db.func.sum(TimeLog.spent_hours).desc())
    
    # Выполнение запроса
    summary = time_logs.all()
    
    # Формирование результата
    result = []
    for user_id, username, total_spent_hours, log_count in summary:
        result.append({
            'user_id': user_id,
            'username': username,
            'total_spent_hours': float(total_spent_hours) if total_spent_hours else 0,
            'log_count': log_count
        })
    
    return jsonify({
        'time_summary': result,
        'filters_applied': {
            'project_id': args.get('project_id'),
            'board_id': args.get('board_id'),
            'user_id': args.get('user_id'),
            'from_date': args.get('from_date'),
            'to_date': args.get('to_date')
        }
    }), 200