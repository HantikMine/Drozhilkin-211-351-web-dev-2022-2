from flask import Flask, render_template, session, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from mysql_db import MySQL
from config import TYPES_ERRORS
import mysql.connector

app = Flask(__name__)
application = app

# Список разрешенных параметров для запросов
PERMITTED_PARAMS = ["login", "password", "last_name", "first_name", "middle_name", "role_id"]

# Загрузка настроек приложения из файла конфигурации
app.config.from_pyfile('config.py')

# Подключение к базе данных MySQL
db = MySQL(app)

# Настройка модуля управления сеансом
login_manager = LoginManager()
login_manager.init_app(app)

# Установка страницы для входа в систему
login_manager.login_view = 'login'

# Установка сообщения об ошибке при необходимости аутентификации
login_manager.login_message = 'Для доступа к этой странице необходимо пройти процедуру аутентификации.'

# Установка типа сообщения для уведомления об ошибке при необходимости аутентификации
login_manager.login_message_category = 'warning'

# Объявление класса User и его наследование от класса UserMixin
class User(UserMixin):
    
    # Объявление метода __init__, который вызывается при создании нового объекта класса
    # Метод принимает аргументы id и login
    def __init__(self, id, login):
        # Присвоение атрибуту id значения аргумента id
        self.id = id
        # Присвоение атрибуту login значения аргумента login
        

@app.route('/')
def index():
    return render_template('index.html')

# Функция проверки аутентификации пользователя по логину и паролю в базе данных
def authentificate_user(login, password):
    # Запрос на выборку всех данных пользователя по логину и хэшу пароля с использованием функции SHA2 для безопасности
    query = "SELECT * FROM users WHERE login = %s AND password_hash = SHA2(%s, 256);"
    # Использование модуля базы данных для установления соединения и работы с курсором
    with db.connection.cursor(named_tuple=True) as cursor:
        # Выполнение запроса на выборку с передачей параметров логина и хэша пароля
        cursor.execute(query, (login, password))
        # Вывод SQL-запроса, который выполнился на экран
        print(cursor.statement)
        # Получение одной строки данных из результата запроса
        db_user = cursor.fetchone()
    # Если пользователь найден в базе данных - создание объекта пользователя и возврат его
    if db_user is not None:
        user = User(db_user.id, db_user.login)
        return user
    # Если пользователь не найден - возврат пустого значения
    return None

# Функция, вызываемая при загрузке пользователя в приложении
@login_manager.user_loader
def load_user(user_id):
    # Запрос на выборку всех данных пользователя по его id
    query = "SELECT * FROM users WHERE id = %s;"
    # Использование модуля базы данных для установления соединения и работы с курсором
    cursor = db.connection.cursor(named_tuple=True)
    # Выполнение запроса на выборку с передачей id пользователя в качестве параметра
    cursor.execute(query, (user_id,))
    # Получение одной строки данных из результата запроса
    db_user = cursor.fetchone()
    # Закрытие курсора
    cursor.close()
    # Если пользователь найден в базе данных - создание объекта пользователя и возврат его
    if db_user is not None:
        user = User(user_id, db_user.login)
        return user
    # Если пользователь не найден - возврат пустого значения
    return None

# Это декоратор, который определяет маршрут, который будет обслуживаться нашим приложением
@app.route('/login', methods = ['POST', 'GET'])

# Это функция, которая будет обрабатывать вход пользователя
def login():
    # Если запрос был POST-запросом
    if request.method == "POST": 
        # Получаем логин пользователя из формы
        user_login = request.form["loginInput"]
        # Получаем пароль пользователя из формы
        user_password = request.form["passwordInput"]
        # Получаем значение флага "запомнить меня" из формы
        remember_me = request.form.get('remember_me') == 'on'
        # Проверяем аутентификацию пользователя
        auth_user = authentificate_user(user_login, user_password)
        # Если пользователь был успешно аутентифицирован
        if auth_user:
            # Авторизуем пользователя
            login_user(auth_user, remember=remember_me)
            # Выводим сообщение об успешной авторизации
            flash("Вы успешно авторизованы", "success")           
            # Получаем параметр next из запроса (если параметр отсутствует, то значение будет None)
            next_ = request.args.get('next')          
            # Перенаправляем пользователя на следующую страницу (если параметр next отсутствует, то перенаправляем пользователя на главную страницу)
            return redirect(next_ or url_for("index"))          
        # Если пользователь не был успешно аутентифицирован
        flash("Введены неверные логин и/или пароль", "danger") 
    # Если запрос был GET-запросом
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for("index"))

# определяем маршрут для запросов к /users
@app.route('/users')
# определяем обработчик для данного маршрута
def users():
    # формируем запрос для получения данных о пользователях и их ролях
    query = "SELECT users.*, roles.name as role_name FROM users LEFT JOIN roles on users.role_id=roles.id;"    
    # создаем курсор для работы в контексте подключения к БД
    with db.connection.cursor(named_tuple = True) as cursor:
        # выполняем запрос
        cursor.execute(query)
        # выводим запрос, который был выполнен
        print(cursor.statement)
        # получаем все данные из запроса
        db_users = cursor.fetchall()        
    # возвращаем шаблон страницы для отображения списка пользователей из БД
    # и передаем в контекст полученные данные
    return render_template('users/index.html', users = db_users)

def load_roles():
    query = "SELECT * FROM roles;"
    with db.connection.cursor(named_tuple = True) as cursor:
        cursor.execute(query)
        db_roles = cursor.fetchall()
    return db_roles

@app.route('/users/new')
@login_required
def new_user():
    return render_template('users/new.html', roles = load_roles(), user={}, errors={})

def insert_to_db(params):
    query = """
        INSERT INTO users (login, password_hash, last_name, first_name, middle_name, role_id) 
        VALUES (%(login)s, SHA2(%(password)s, 256), %(last_name)s, %(first_name)s, %(middle_name)s, %(role_id)s);
    """
    try:
        with db.connection.cursor(named_tuple = True) as cursor:
            cursor.execute(query, params)
            db.connection.commit()
    except mysql.connector.errors.DatabaseError:
        db.connection.rollback()
        return False

    return True

def validation_edit(params):
    PERMITTED_LOGIN = "abcdefghijklmnopqrstuvwxyz1234567890"
    errors_res = {
        "login": None,
        "last_name": None,
        "first_name": None,
        "isvalidate": 1,
    }
    login = params.get("login")
    if login is None:
        errors_res["login"] = TYPES_ERRORS["empty_login"]
        errors_res["isvalidate"] = 0
    elif len(login) < 5:
        errors_res["login"] = TYPES_ERRORS["login_incorrect_size"]
        errors_res["isvalidate"] = 0
    else:
        for char in login:
             if PERMITTED_LOGIN.find(char.lower()) == -1:
                 errors_res["login"] = TYPES_ERRORS["login_incorrect_chars"]
                 errors_res["isvalidate"] = 0
                 break
             
    if params.get("last_name") is None:
        errors_res["last_name"] = TYPES_ERRORS["empty_last_name"]
        errors_res["isvalidate"] = 0

    if params.get("first_name") is None:
        errors_res["first_name"] = TYPES_ERRORS["empty_first_name"]
        errors_res["isvalidate"] = 0

    return errors_res

def check_password(params, PERMITTED_PASSWORD):
    errors_res = {
        "password": None,
    }
    count_upper_letters = 0
    count_lower_letters = 0
    count_digits = 0
    password = params.get("password")
    if password is None:
        errors_res["password"] = TYPES_ERRORS["empty_passwd"]
    elif len(password) < 8:
        errors_res["password"] = TYPES_ERRORS["password_small_length"]
    elif len(password) > 128:
        errors_res["password"] = TYPES_ERRORS["password_big_length"]
    elif password.find(" ") > -1:
        errors_res["password"] = TYPES_ERRORS["password_has_spaces"]
    else:
        for char in password:
            if PERMITTED_PASSWORD.find(char.lower()) == -1:
                errors_res["password"] = TYPES_ERRORS["password_incorrect_chars"]
                break
            elif char.isalpha():
                if char.isupper():
                    count_upper_letters += 1
                else:
                    count_lower_letters += 1
            elif char.isdigit():
                count_digits += 1
        if count_upper_letters < 1:
            errors_res["password"] = TYPES_ERRORS["password_hasnt_big_alpha"]
        elif count_lower_letters < 1:
            errors_res["password"] = TYPES_ERRORS["password_hasnt_small_alpha"]
        elif count_digits < 1:
            errors_res["password"] = TYPES_ERRORS["password_hasnt_digit"]
    return errors_res

def validation_create(params):
    PERMITTED_LOGIN = "abcdefghijklmnopqrstuvwxyz1234567890"
    PERMITTED_PASSWORD = '''abcdefghijklmnopqrstuvwxyzабвгдеёжзийклмнопрстуфхцчшщъыьэюя1234567890~!?@#$%^&*_-+()[]{}></\|"'.,:;'''
    errors_res = {
        "login": None,
        "password": None,
        "last_name": None,
        "first_name": None,
        "isvalidate": 1,
    }
    login = params.get("login")
    if login is None:
        errors_res["login"] = TYPES_ERRORS["empty_login"]
        errors_res["isvalidate"] = 0
    elif len(login) < 5:
        errors_res["login"] = TYPES_ERRORS["login_incorrect_size"]
        errors_res["isvalidate"] = 0
    else:
        for char in login:
             if PERMITTED_LOGIN.find(char.lower()) == -1:
                 errors_res["login"] = TYPES_ERRORS["login_incorrect_chars"]
                 errors_res["isvalidate"] = 0
                 break
             
    if params.get("last_name") is None:
        errors_res["last_name"] = TYPES_ERRORS["empty_last_name"]
        errors_res["isvalidate"] = 0

    if params.get("first_name") is None:
        errors_res["first_name"] = TYPES_ERRORS["empty_first_name"]
        errors_res["isvalidate"] = 0

    checked_password = check_password(params, PERMITTED_PASSWORD)
    if not checked_password.get("password") is None:
        errors_res["password"] = checked_password["password"]
        errors_res["isvalidate"] = 0

    return errors_res
            
def params(names_list):
    result = {}
    for name in names_list:
        result[name] = request.form.get(name) or None
    return result

@app.route('/users/create', methods=['POST'])
@login_required
def create_user():
    cur_params = params(PERMITTED_PARAMS)
    errors = validation_create(cur_params)
    if errors["isvalidate"] == 0:
        flash("Проверьте правильность введённых данных", "danger")
        return render_template("users/new.html", roles = load_roles(), user=cur_params, errors=errors)
    
    inserted = insert_to_db(cur_params)
    if inserted:
        flash("Пользователь успешно добавлен", "success")
        return redirect(url_for("users"))
    else:
        flash("При сохранении возникла ошибка", "danger")
        return render_template("users/new.html", roles = load_roles(), user=cur_params, errors=errors)

@app.route('/users/<int:user_id>/edit', methods=['GET'])
@login_required
def edit_user(user_id):
    edit_select = "SELECT * FROM users WHERE id = %s;"
    errors = {}
    with db.connection.cursor(named_tuple = True) as cursor:
        cursor.execute(edit_select, (user_id,))
        user = cursor.fetchone()
        if user is None:
            flash("Пользователь не найден", "warning")
            return redirect(url_for("users"))
        
    return render_template("users/edit.html", user=user, roles=load_roles(), errors=errors)

@app.route('/users/<int:user_id>/update', methods=['POST'])
@login_required
def update_user(user_id):
    cur_params = params(PERMITTED_PARAMS)
    errors = validation_edit(cur_params)
    cur_params["id"] = user_id
    update_query = """
    UPDATE users SET login = %(login)s, last_name = %(last_name)s, 
    first_name = %(first_name)s, middle_name = %(middle_name)s,
    role_id = %(role_id)s WHERE id = %(id)s;
    """
    if errors["isvalidate"] == 0:
        flash("Проверьте правильность введённых данных", "danger")
        return render_template('users/edit.html', user=cur_params, roles=load_roles(), errors=errors)
    try:
        with db.connection.cursor(named_tuple = True) as cursor:
            cursor.execute(update_query, cur_params)
            db.connection.commit()
            flash("Пользователь успешно обновлен", "success")
    except mysql.connector.errors.DatabaseError:
        flash("При изменении возникла ошибка", "danger")
        db.connection.rollback()
        return render_template('users/edit.html', user=cur_params, roles=load_roles(), errors=errors)
        
    return redirect(url_for("users"))
    
    
@app.route("/users/<int:user_id>")
def show_user(user_id):
    with db.connection.cursor(named_tuple = True) as cursor:
        query="SELECT * FROM users WHERE id = %s"
        cursor.execute(query, (user_id,))
        db_user = cursor.fetchone()
    if db_user is None:
        flash("Пользователь не найден", "danger")
        return redirect(url_for("users"))
    
    return render_template('users/show.html', user=db_user)

@app.route("/users/<int:user_id>/delete", methods=['POST'])  # Define a route for deleting a user with a given user ID
@login_required  # Require the user to be logged in to access this route
def delete_user(user_id):  # Define a function to handle the delete user request
    delete_query="DELETE FROM users WHERE id = %s"  # Define a SQL query to delete a user from the database
    try:  # Try to execute the following code block
        with db.connection.cursor(named_tuple = True) as cursor:  # Create a cursor object to interact with the database
            cursor.execute(delete_query, (user_id,))  # Execute the delete query with the user ID as a parameter
            db.connection.commit()  # Commit the changes to the database
            flash("Пользователь успешно удален", "success")  # Display a success message to the user
    except mysql.connector.errors.DatabaseError:  # If a database error occurs, execute the following code block
        flash("При удалении произошла ошибка", "danger")  # Display an error message to the user
        db.connection.rollback()  # Rollback the changes to the database
    return redirect(url_for("users"))  # Redirect the user to the "users" route after the deletion is complete

@app.route("/update_password", methods=['GET', 'POST'])
@login_required
def update_password():
    user_id = current_user.id
    PERMITTED_PASSWORD = '''abcdefghijklmnopqrstuvwxyzабвгдеёжзийклмнопрстуфхцчшщъыьэюя1234567890~!?@#$%^&*_-+()[]{}></\|"'.,:;'''
    errors = {
        "old": None,
        "check": None,
        "password": None, 
        "isvalidate": 1,
    }
    fields = {
        "old": "",
        "new": "",
        "check": "",
    }
    if request.method == "POST":
        old_passwd = request.form.get("floatingOldPassword")
        new_passwd = request.form.get("floatingNewPassword")
        check_new_passwd = request.form.get("floatingCheckPassword")
        fields["old"] = old_passwd
        fields["new"] = new_passwd
        fields["check"] = check_new_passwd
        query = "SELECT * FROM users WHERE id = %s AND password_hash = SHA2(%s, 256);"
    # Устанавливаем соединение с базой данных и создаем курсор
    with db.connection.cursor(named_tuple = True) as cursor:
        # Выполняем запрос к базе данных с параметрами user_id и old_passwd
        cursor.execute(query, (user_id, old_passwd))
        # Выводим в консоль текст SQL запроса из курсора
        print(cursor.statement)
        # Получаем результат выполнения запроса в переменную db_user
        db_user = cursor.fetchone()
        # Если пользователь не найден в базе данных, добавляем ошибку в словарь ошибок
        if db_user is None:
            errors["old"] = TYPES_ERRORS["incorrect_password"]
            errors["isvalidate"] = 0
        # Проверяем новый пароль на соответствие правилам PERMITTED_PASSWORD
        validate_password = check_password({"password": new_passwd}, PERMITTED_PASSWORD)
        # Если проверка не прошла, добавляем ошибки в словарь ошибок
        if not validate_password.get("password") is None:
            errors["password"] = validate_password["password"]
            errors["check"] = validate_password["password"]
            errors["isvalidate"] = 0
        # Проверяем равенство нового пароля и его повторения
        if new_passwd != check_new_passwd:
            errors["check"] = TYPES_ERRORS["incorrect_checked_password"]
            errors["isvalidate"] = 0
            if errors.get("isvalidate") == 0:
                flash("Проверьте введённые данные", "danger")
                return render_template('update_password.html', errors=errors, fields=fields)
        
            update_query = "UPDATE users SET password_hash = SHA2(%s, 256) WHERE id = %s;"
            try:
                with db.connection.cursor(named_tuple = True) as cursor:
                    cursor.execute(update_query, (new_passwd, user_id))
                    db.connection.commit()
                    flash("Пароль успешно обновлен", "success")
                    return redirect(url_for("index"))
            except mysql.connector.errors.DatabaseError:
                flash("При изменении возникла ошибка", "danger")
                db.connection.rollback()
                return render_template('update_password.html', errors=errors, fields=fields)
    return render_template('update_password.html', errors=errors, fields=fields)