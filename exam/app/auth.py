from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from functools import wraps
from users_policy import UsersPolicy

bp = Blueprint('auth', __name__, url_prefix='/auth')
from app import db

def authentificate_user(login, password):
    our_query = "SELECT * FROM users WHERE login = %s AND password_hash	= SHA2(%s, 256);"
    with db.connection.cursor(named_tuple = True) as cursor:
        cursor.execute(our_query, (login, password))
        print(cursor.statement)
        db_user = cursor.fetchone()
    if db_user is not None:
        user = User(db_user.id, db_user.login, db_user.roles_id, db_user.last_name, db_user.first_name, db_user.middle_name)
        return user
    return None

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for("index"))

def load_user(user_id):
    our_query = "SELECT * FROM users WHERE id = %s;"
    cursor = db.connection.cursor(named_tuple = True)
    cursor.execute(our_query, (user_id,))
    db_user = cursor.fetchone()
    cursor.close()
    if db_user is not None:
        user = User(user_id, db_user.login, db_user.roles_id, db_user.last_name, db_user.first_name, db_user.middle_name)
        return user
    return None

@bp.route('/login', methods = ['POST', 'GET'])
def login():
    if request.method == "POST":
        login = request.form["loginInput"]
        passwd = request.form["passwordInput"]
        remember_me = request.form.get('remember_me') == 'on'
        is_auth = authentificate_user(login, passwd)
        if is_auth:
            login_user(is_auth, remember=remember_me)
            flash("Вы успешно авторизованы", "success")
            next_ = request.args.get('next')
            return redirect(next_ or url_for("index"))
            
        flash("Введены неверные логин и/или пароль", "danger") 


    return render_template('login.html')

def check_rights(action):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = None
            user_id = kwargs.get("user_id")
            if user_id:
                user = load_user(user_id)
            if not current_user.can(action, user):
                flash("У вас недостаточно прав для выполнения данного действия", "warning")
                return redirect(url_for("index"))
            return func(*args, **kwargs)
        return wrapper
    return decorator
        

def init_login_manager(app):
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Для выполнения данного действия необходимо пройти процедуру аутентификации'
    login_manager.login_message_category = 'warning'
    login_manager.user_loader(load_user)

class User(UserMixin):
    def __init__(self, id, login, roles_id, last_name, first_name, middle_name):
        self.id = id
        self.login = login
        self.roles_id = roles_id
        self.last_name = last_name
        self.first_name = first_name
        self.middle_name = middle_name

    def is_administrator(self):
        return self.roles_id <= current_app.config["ADMINISTRATOR_ROLE_ID"]

    def is_moderator(self):
        return self.roles_id <= current_app.config["MODERATOR_ROLE_ID"]

    def getFullName(self):
        return self.last_name+" "+self.first_name+" "+self.middle_name

    def can(self, action, record=None):
        users_policy = UsersPolicy(record)
        method = getattr(users_policy, action, None)
        if method:
            return method()
        return False
