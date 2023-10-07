import mysql.connector as connector
from flask import g

# Определяем класс MySQL
class MySQL:
    # Инициализируем класс и устанавливаем свойство приложения
    # Устанавливаем колбэк для выключения контекста приложения
    def __init__(self, app):
        self.app = app
        app.teardown_appcontext(self.close_connection)

    # Определяем свойство connection
    # Если база данных еще не была создана, создаем и ее соединение
    @property
    def connection(self):
        if "db" not in g:
            g.db = connector.connect(**self.config())
        return g.db 

    # Конфигурируем подключение к базе данных
    def config(self):
        return {
            'user': self.app.config["MYSQL_USER"],
            'password': self.app.config["MYSQL_PASSWORD"], 
            'host': self.app.config["MYSQL_HOST"],
            'database': self.app.config["MYSQL_DATABASE"]
        }

    # Закрываем соединение с базой данных
    def close_connection(self, e=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()