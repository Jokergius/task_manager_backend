from flask import Blueprint, request, jsonify
from app import db
from app.models import Board, Project
from app.utils import auth_required, manager_required

boards_bp = Blueprint('boards', __name__)


@boards_bp.route('/', methods=['GET'])
@auth_required
def get_all_boards():
    """Получение всех досок"""
    boards = Board.query.all()
    boards_list = [{
        'id': board.id,
        'name': board.name,
        'project_id': board.project_id,
        'project_name': board.project.name,
        'created_at': board.created_at.isoformat()
    } for board in boards]

    return jsonify({'boards': boards_list}), 200


@boards_bp.route('/<int:board_id>', methods=['GET'])
@auth_required
def get_board(board_id):
    """Получение конкретной доски по ID"""
    board = Board.query.get(board_id)

    if not board:
        return jsonify({'message': 'Доска не найдена'}), 404

    columns = board.columns.all()
    columns_list = [{
        'id': column.id,
        'name': column.name,
        'order': column.order,
        'task_count': column.tasks.count()
    } for column in columns]

    board_data = {
        'id': board.id,
        'name': board.name,
        'project_id': board.project_id,
        'project_name': board.project.name,
        'created_at': board.created_at.isoformat(),
        'columns': columns_list
    }

    return jsonify(board_data), 200


@boards_bp.route('/', methods=['POST'])
@manager_required
def create_board():
    """Создание новой доски (только менеджеры)"""
    data = request.get_json()

    # Проверка наличия необходимых полей
    if not data or not data.get('name') or not data.get('project_id'):
        return jsonify({'message': 'Название доски и ID проекта обязательны'}), 400

    # Проверка существования проекта
    project = Project.query.get(data['project_id'])
    if not project:
        return jsonify({'message': 'Указанный проект не существует'}), 404

    # Создание доски
    new_board = Board(
        name=data['name'],
        project_id=data['project_id']
    )

    db.session.add(new_board)
    db.session.commit()

    # Создание стандартных колонок
    new_board.create_default_columns()

    return jsonify({
        'message': 'Доска успешно создана',
        'board': {
            'id': new_board.id,
            'name': new_board.name,
            'project_id': new_board.project_id,
            'created_at': new_board.created_at.isoformat()
        }
    }), 201


@boards_bp.route('/<int:board_id>', methods=['PUT'])
@manager_required
def update_board(board_id):
    """Обновление доски (только менеджеры)"""
    board = Board.query.get(board_id)

    if not board:
        return jsonify({'message': 'Доска не найдена'}), 404

    data = request.get_json()

    if data.get('name'):
        board.name = data['name']

    db.session.commit()

    return jsonify({
        'message': 'Доска успешно обновлена',
        'board': {
            'id': board.id,
            'name': board.name,
            'project_id': board.project_id,
            'created_at': board.created_at.isoformat()
        }
    }), 200


@boards_bp.route('/<int:board_id>', methods=['DELETE'])
@manager_required
def delete_board(board_id):
    """Удаление доски (только менеджеры)"""
    board = Board.query.get(board_id)

    if not board:
        return jsonify({'message': 'Доска не найдена'}), 404

    db.session.delete(board)
    db.session.commit()

    return jsonify({'message': 'Доска успешно удалена'}), 200