from flask import Blueprint, request, jsonify
from app import db
from app.models import Project, Board
from app.utils import auth_required, manager_required

projects_bp = Blueprint('projects', __name__)


@projects_bp.route('/', methods=['GET'])
@auth_required
def get_projects():
    """Получение списка всех проектов"""
    projects = Project.query.all()
    projects_list = [{
        'id': project.id,
        'name': project.name,
        'code': project.code,
        'description': project.description,
        'created_at': project.created_at.isoformat()
    } for project in projects]

    return jsonify({'projects': projects_list}), 200


@projects_bp.route('/', methods=['POST'])
@manager_required
def create_project():
    """Создание нового проекта (только менеджеры)"""
    data = request.get_json()

    # Проверка наличия необходимых полей
    if not data or not data.get('name') or not data.get('code'):
        return jsonify({'message': 'Имя и код проекта обязательны'}), 400

    # Проверка уникальности кода проекта
    if Project.query.filter_by(code=data['code']).first():
        return jsonify({'message': 'Проект с таким кодом уже существует'}), 400

    # Создание проекта
    new_project = Project(
        name=data['name'],
        code=data['code'].upper(),
        description=data.get('description', '')
    )

    db.session.add(new_project)
    db.session.commit()

    # Создание доски по умолчанию для проекта
    default_board = Board(
        name=f"{new_project.name} Board",
        project_id=new_project.id
    )

    db.session.add(default_board)
    db.session.commit()

    # Создание стандартных колонок для доски
    default_board.create_default_columns()

    return jsonify({
        'message': 'Проект успешно создан',
        'project': {
            'id': new_project.id,
            'name': new_project.name,
            'code': new_project.code,
            'description': new_project.description,
            'created_at': new_project.created_at.isoformat()
        }
    }), 201


@projects_bp.route('/<int:project_id>', methods=['GET'])
@auth_required
def get_project(project_id):
    """Получение деталей проекта по ID"""
    project = Project.query.get(project_id)

    if not project:
        return jsonify({'message': 'Проект не найден'}), 404

    project_data = {
        'id': project.id,
        'name': project.name,
        'code': project.code,
        'description': project.description,
        'created_at': project.created_at.isoformat(),
        'boards': [{
            'id': board.id,
            'name': board.name
        } for board in project.boards]
    }

    return jsonify(project_data), 200


@projects_bp.route('/<int:project_id>', methods=['PUT'])
@manager_required
def update_project(project_id):
    """Обновление проекта (только менеджеры)"""
    project = Project.query.get(project_id)

    if not project:
        return jsonify({'message': 'Проект не найден'}), 404

    data = request.get_json()

    if data.get('name'):
        project.name = data['name']

    if data.get('description'):
        project.description = data['description']

    db.session.commit()

    return jsonify({
        'message': 'Проект успешно обновлен',
        'project': {
            'id': project.id,
            'name': project.name,
            'code': project.code,
            'description': project.description,
            'created_at': project.created_at.isoformat()
        }
    }), 200


@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@manager_required
def delete_project(project_id):
    """Удаление проекта (только менеджеры)"""
    project = Project.query.get(project_id)

    if not project:
        return jsonify({'message': 'Проект не найден'}), 404

    db.session.delete(project)
    db.session.commit()

    return jsonify({'message': 'Проект успешно удален'}), 200


@projects_bp.route('/<int:project_id>/boards', methods=['GET'])
@auth_required
def get_project_boards(project_id):
    """Получение досок проекта"""
    project = Project.query.get(project_id)

    if not project:
        return jsonify({'message': 'Проект не найден'}), 404

    boards = project.boards.all()
    boards_list = [{
        'id': board.id,
        'name': board.name,
        'created_at': board.created_at.isoformat()
    } for board in boards]

    return jsonify({'boards': boards_list}), 200