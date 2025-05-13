from flask import Blueprint, request, jsonify
from app import db
from app.models import Column, Board
from app.utils import auth_required, manager_required

columns_bp = Blueprint('columns', __name__)


@columns_bp.route('/board/<int:board_id>', methods=['GET'])
@auth_required
def get_board_columns(board_id):
    """Получение колонок доски"""
    board = Board.query.get(board_id)

    if not board:
        return jsonify({'message': 'Доска не найдена'}), 404

    columns = board.columns.order_by(Column.order).all()
    columns_list = [{
        'id': column.id,
        'name': column.name,
        'order': column.order,
        'board_id': column.board_id,
        'created_at': column.created_at.isoformat(),
        'tasks': [{
            'id': task.id,
            'code': task.code,
            'title': task.title,
            'priority': task.priority,
            'description': task.description,
            'estimated_time': task.estimated_time,
            'remaining_time': task.remaining_time,
            'spent_time': task.spent_time,
            'author': task.author.username if task.author else None,
            'author_id': task.author_id,
            'assignee': task.assignee.username if task.assignee else None,
            'assignee_id': task.assignee_id,
            'status': task.status,
            'created_at': task.created_at.isoformat(),
            'updated_at': task.updated_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None
        } for task in column.tasks]
    } for column in columns]

    return jsonify({'columns': columns_list}), 200


@columns_bp.route('/', methods=['POST'])
@manager_required
def create_column():
    """Создание новой колонки (только менеджеры)"""
    data = request.get_json()

    # Проверка наличия необходимых полей
    if not data or not data.get('name') or not data.get('board_id'):
        return jsonify({'message': 'Название колонки и ID доски обязательны'}), 400

    # Проверка существования доски
    board = Board.query.get(data['board_id'])
    if not board:
        return jsonify({'message': 'Указанная доска не существует'}), 404

    # Определение порядка колонки
    last_column = Column.query.filter_by(board_id=data['board_id']).order_by(Column.order.desc()).first()
    order = (last_column.order + 1) if last_column else 1

    # Создание колонки
    new_column = Column(
        name=data['name'],
        order=order,
        board_id=data['board_id']
    )

    db.session.add(new_column)
    db.session.commit()

    return jsonify({
        'message': 'Колонка успешно создана',
        'column': {
            'id': new_column.id,
            'name': new_column.name,
            'order': new_column.order,
            'board_id': new_column.board_id,
            'created_at': new_column.created_at.isoformat()
        }
    }), 201


@columns_bp.route('/<int:column_id>', methods=['PUT'])
@manager_required
def update_column(column_id):
    """Обновление колонки (только менеджеры)"""
    column = Column.query.get(column_id)

    if not column:
        return jsonify({'message': 'Колонка не найдена'}), 404

    data = request.get_json()

    if data.get('name'):
        column.name = data['name']

    if data.get('order'):
        column.order = data['order']

    db.session.commit()

    return jsonify({
        'message': 'Колонка успешно обновлена',
        'column': {
            'id': column.id,
            'name': column.name,
            'order': column.order,
            'board_id': column.board_id,
            'created_at': column.created_at.isoformat()
        }
    }), 200


@columns_bp.route('/<int:column_id>', methods=['DELETE'])
@manager_required
def delete_column(column_id):
    """Удаление колонки (только менеджеры)"""
    column = Column.query.get(column_id)

    if not column:
        return jsonify({'message': 'Колонка не найдена'}), 404

    # Проверяем, есть ли задачи в колонке
    if column.tasks.count() > 0:
        return jsonify({
            'message': 'Невозможно удалить колонку, содержащую задачи. Переместите задачи в другие колонки.'
        }), 400

    db.session.delete(column)
    db.session.commit()

    # Обновляем порядок оставшихся колонок
    remaining_columns = Column.query.filter_by(board_id=column.board_id).order_by(Column.order).all()
    for i, col in enumerate(remaining_columns, 1):
        col.order = i

    db.session.commit()

    return jsonify({'message': 'Колонка успешно удалена'}), 200


@columns_bp.route('/reorder', methods=['POST'])
@manager_required
def reorder_columns():
    """Изменение порядка колонок (только менеджеры)"""
    data = request.get_json()

    if not data or 'columns' not in data:
        return jsonify({'message': 'Не предоставлены данные для изменения порядка'}), 400

    column_order = data['columns']  # Формат: [{'id': 1, 'order': 1}, {'id': 2, 'order': 2}, ...]

    # Обновление порядка колонок
    for item in column_order:
        column = Column.query.get(item['id'])
        if column:
            column.order = item['order']

    db.session.commit()

    return jsonify({'message': 'Порядок колонок успешно обновлен'}), 200