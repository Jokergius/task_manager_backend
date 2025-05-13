from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return f'<Role {self.name}>'


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Отношения
    created_tasks = db.relationship('Task', foreign_keys='Task.author_id', backref='author', lazy='dynamic')
    assigned_tasks = db.relationship('Task', foreign_keys='Task.assignee_id', backref='assignee', lazy='dynamic')

    @property
    def password(self):
        raise AttributeError('Пароль не является читаемым атрибутом')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_manager(self):
        return self.role.name == 'manager'

    def is_executor(self):
        return self.role.name == 'executor'

    def __repr__(self):
        return f'<User {self.username}>'


class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Отношения
    boards = db.relationship('Board', backref='project', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Project {self.name}>'


class Board(db.Model):
    __tablename__ = 'boards'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Отношения
    columns = db.relationship('Column', backref='board', lazy='dynamic', order_by='Column.order',
                              cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Board {self.name}>'

    def create_default_columns(self):
        """Создает стандартные колонки для доски"""
        default_columns = [
            {'name': 'Беклог', 'order': 1},
            {'name': 'Переоткрыто', 'order': 2},
            {'name': 'В работе', 'order': 3},
            {'name': 'Деплой/Ревью', 'order': 4},
            {'name': 'Тест', 'order': 5},
            {'name': 'Проверено', 'order': 6},
            {'name': 'В продакшен', 'order': 7}
        ]

        for col_data in default_columns:
            column = Column(
                name=col_data['name'],
                order=col_data['order'],
                board_id=self.id
            )
            db.session.add(column)

        db.session.commit()


class Column(db.Model):
    __tablename__ = 'columns'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    board_id = db.Column(db.Integer, db.ForeignKey('boards.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Отношения
    tasks = db.relationship('Task', backref='column', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Column {self.name}>'


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(20), default='medium')  # low, medium, high

    # Поля для времени
    estimated_time = db.Column(db.Float, default=0)  # Оценка времени в часах
    remaining_time = db.Column(db.Float, default=0)  # Оставшееся время в часах
    spent_time = db.Column(db.Float, default=0)  # Затраченное время в часах

    # Связи с пользователями
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Связь с колонкой
    column_id = db.Column(db.Integer, db.ForeignKey('columns.id'), nullable=False)

    # Даты
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<Task {self.code}: {self.title}>'

    @property
    def status(self):
        """Возвращает статус задачи на основе колонки"""
        return self.column.name if self.column else "Не определен"