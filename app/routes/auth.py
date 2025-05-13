from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity
from app import db
from app.models import User, Role
from app.utils import auth_required

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """Регистрация нового пользователя"""
    data = request.get_json()

    # Проверка наличия необходимых полей
    required_fields = ['username', 'email', 'password', 'role']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Не все поля заполнены'}), 400

    # Проверка существования пользователя
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'Пользователь с таким именем уже существует'}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Пользователь с такой почтой уже существует'}), 400

    # Проверка наличия роли
    role_name = data['role']
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        return jsonify({'message': 'Указанная роль не существует'}), 400

    # Создание пользователя
    new_user = User(
        username=data['username'],
        email=data['email'],
        role_id=role.id
    )
    new_user.password = data['password']

    db.session.add(new_user)
    db.session.commit()

    # Создание токена - преобразуем ID в строку
    access_token = create_access_token(identity=str(new_user.id))

    return jsonify({
        'message': 'Пользователь успешно зарегистрирован',
        'access_token': access_token,
        'user': {
            'id': new_user.id,
            'username': new_user.username,
            'email': new_user.email,
            'role': role.name
        }
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Авторизация пользователя"""
    data = request.get_json()

    # Проверка наличия необходимых полей
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Не все поля заполнены'}), 400

    # Поиск пользователя
    user = User.query.filter_by(username=data['username']).first()
    if not user or not user.verify_password(data['password']):
        return jsonify({'message': 'Неверное имя пользователя или пароль'}), 401

    # Создание токена - преобразуем ID в строку
    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        'message': 'Авторизация успешна',
        'access_token': access_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role.name
        }
    }), 200


@auth_bp.route('/me', methods=['GET'])
@auth_required
def get_me():
    """Получение информации о текущем пользователе"""
    user_id = get_jwt_identity()
    # Преобразуем обратно в число, так как теперь получаем строку
    user = User.query.get(int(user_id))

    if not user:
        return jsonify({'message': 'Пользователь не найден'}), 404

    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role.name
    }), 200