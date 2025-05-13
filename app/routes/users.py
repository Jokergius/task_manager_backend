from flask import Blueprint, jsonify
from app.models import User
from app.utils import auth_required, manager_required

users_bp = Blueprint('users', __name__)


@users_bp.route('/', methods=['GET'])
@auth_required
def get_users():
    """Получение списка всех пользователей"""
    users = User.query.all()
    users_list = [{
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role.name
    } for user in users]

    return jsonify({'users': users_list}), 200


@users_bp.route('/<int:user_id>', methods=['GET'])
@auth_required
def get_user(user_id):
    """Получение конкретного пользователя по ID"""
    user = User.query.get(user_id)

    if not user:
        return jsonify({'message': 'Пользователь не найден'}), 404

    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role.name,
        'created_at': user.created_at.isoformat()
    }

    return jsonify(user_data), 200