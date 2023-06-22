from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from mysql_db import MySQL
import math
import bleach
import os

app = Flask(__name__)
application = app

BOOKS_NUM = 3
ALL_PARAMS = ["title", "short_desc", "year", "publisher", "author", "size"]

app.config.from_pyfile('config.py')
db = MySQL(app)

from auth import bp as bp_auth, init_login_manager, check_rights

init_login_manager(app)
app.register_blueprint(bp_auth)

def downloadBook(book_id):
    our_query = """
            SELECT * FROM book WHERE id = %s
    """
    with db.connection.cursor(named_tuple = True) as cursor:
        cursor.execute(our_query, (book_id,))
        req_book = cursor.fetchone()
    return req_book

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    our_query = """SELECT 
                b.*, 
                GROUP_CONCAT(g.name SEPARATOR ', ') AS genres,
                c.file_name,
                COUNT(DISTINCT r.id) AS reviews_count,
                TRUNCATE(AVG(r.grade), 1) AS avg_review_grade
                FROM book b
                INNER JOIN book_has_genres bg ON b.id = bg.book_id
                INNER JOIN genres g ON bg.genres_id = g.id
                LEFT JOIN covers c ON b.covers_id = c.id
                LEFT JOIN reviews r ON b.id = r.book_id
                GROUP BY b.id, b.title, b.description, b.year, b.publisher, b.author, b.size, b.covers_id
                ORDER BY b.year DESC
                LIMIT %s
                OFFSET %s
                ;"""
    with db.connection.cursor(named_tuple = True) as cursor:
        cursor.execute(our_query,(BOOKS_NUM, BOOKS_NUM * (page - 1)))
        db_books = cursor.fetchall() 
    our_query = 'SELECT count(*) as page_count FROM book' 
    with db.connection.cursor(named_tuple = True) as cursor:
        cursor.execute(our_query)
        db_nums = cursor.fetchone().page_count
    page_nums = math.ceil(db_nums / BOOKS_NUM)
    return render_template('index.html',books = db_books, page = page,page_count = page_nums)

@app.route('/book/<int:book_id>/book_delete', methods=['POST'])
@login_required
@check_rights('delete')
def book_delete(book_id):
    req_book = downloadBook(book_id=book_id)
    try:
        our_query = """
                SELECT covers.file_name FROM book JOIN covers ON book.covers_id = covers.id WHERE book.id = %s
        """
        with db.connection.cursor(named_tuple = True) as cursor:
                    cursor.execute(our_query,(book_id,)) 
                    cover_name = cursor.fetchone().file_name
        directory = os.getcwd()
        file_path = os.path.join(directory, 'static', 'images', cover_name)
        os.remove(file_path) 
        our_query ="""
                DELETE FROM book WHERE id=%s;
        """
        with db.connection.cursor(named_tuple = True) as cursor:
                    cursor.execute(our_query,(book_id,)) 
                    db.connection.commit()
        flash(f'Книга {req_book.title} успешно удалена', 'success')
    except:
        flash('Ошибка при удалении', 'danger')    
    return redirect(url_for('index'))   

def downloadGenres(book_id):
    our_query = """
                SELECT genres.id, genres.name FROM book
                JOIN book_has_genres ON book.id = book_has_genres.book_id
                JOIN genres ON book_has_genres.genres_id = genres.id
                WHERE book.id = %s
    """
    with db.connection.cursor(named_tuple = True) as cursor:
        cursor.execute(our_query, (book_id,))
        genres = cursor.fetchall()
    our_query = """
                SELECT * FROM genres
    """
    with db.connection.cursor(named_tuple = True) as cursor:
        cursor.execute(our_query)
        all_used_genres = cursor.fetchall()
    tmp_genres = [ str(genre.id) for genre in genres]
    return all_used_genres, tmp_genres

@app.route('/book/<int:book_id>/book_edit', methods=['GET'])
@login_required
@check_rights("edit")    
def book_edit(book_id):
    book = downloadBook(book_id=book_id)
    all_used_genres, tmp_genres = downloadGenres(book_id=book_id)
    return render_template("book/book_edit.html", genres = all_used_genres, book=book, new_genres=tmp_genres)

@app.route('/book/<int:book_id>/comment', methods=['GET', 'POST'])
@login_required
def book_review(book_id):
    review_yours, reviews_alls = downloadRev(book_id=book_id) 
    our_query = """
        INSERT INTO reviews (grade, text, users_id, book_id) 
        VALUES (%(grade)s, %(text)s, %(users_id)s, %(book_id)s);
    """
    if review_yours!=None:
        flash("Можно добавить только одну рецензию", "warning")
        return redirect(url_for('book_show', book_id=book_id, all_reviews=reviews_alls, your_review=review_yours))
    if request.method == 'POST':
        grade = request.form.get('grade')
        params = {
            "grade": grade,
            "text": request.form.get('short_desc'),
            "users_id": current_user.id,
            "book_id": book_id
        }
        if len(params["text"])==0:
            flash("Тест рецензии не должен быть пустым", "warning")
            return redirect(url_for('book_review', book_id=book_id))
        for param in params:
            param = bleach.clean(param)
        try:
            with db.connection.cursor(named_tuple = True) as cursor:
                cursor.execute(our_query,params=params) 
                db.connection.commit()
            flash("Рецензия успешно добавлена", "success")
            return redirect(url_for('book_show', book_id=book_id,all_reviews=reviews_alls, your_review=review_yours))
        except:
            flash('Ошибка при добавлении рецензии', 'danger')
            return redirect(url_for('book_review', book_id=book_id))
    return render_template('comment.html', book_id = book_id)

@app.route('/book/<int:book_id>/update', methods=['POST'])
@login_required
@check_rights("edit")
def book_update(book_id):
    book = downloadBook(book_id=book_id)
    all_used_genres, tmp_genres = downloadGenres(book_id=book_id)
    now_params = downloadParams(ALL_PARAMS)
    new_genres = request.form.getlist('genre_id')
    for param in now_params:
        if now_params[param]==None:
            flash("Указаны не все параметры", "danger")
            return render_template("book/book_edit.html", genres = all_used_genres, book=book, new_genres=tmp_genres)
        now_params[param] = bleach.clean(now_params[param])
   
    our_query = """
        UPDATE book SET title=%s, description=%s, author=%s, year=%s, size=%s, publisher=%s WHERE id=%s;
    """
    try:
        with db.connection.cursor(named_tuple = True) as cursor:
                    cursor.execute(our_query,(now_params['title'],now_params['short_desc'],now_params['author'],now_params['year'],now_params['size'],now_params['publisher'],book_id)) 
                    db.connection.commit()
        our_query = """
                DELETE FROM book_has_genres WHERE book_id = %s;
                """
        with db.connection.cursor(named_tuple = True) as cursor:
                    cursor.execute(our_query,(book_id,)) 
                    db.connection.commit()
        for genre in new_genres:
            our_query = """
                INSERT INTO book_has_genres (book_id, genres_id) VALUES (%s, %s);
                """
            with db.connection.cursor(named_tuple = True) as cursor:
                    cursor.execute(our_query,(book_id,genre)) 
                    db.connection.commit()    
        flash(f"Книга '{now_params['title']}' успешно обновлена", "success")
    except:
        flash("При сохранении возникла ошибка", "danger")
        return render_template("book/book_edit.html", genres = all_used_genres, book=book, new_genres=tmp_genres)
    return redirect(url_for('book_show', book_id=book_id))


def downloadParams(names_list):
    res = {}
    for name in names_list:
        res[name] = request.form.get(name) or None 
    return res

@app.route('/book/<int:book_id>')
def book_show(book_id):
        our_query = """SELECT 
                    b.*, 
                    GROUP_CONCAT(g.name SEPARATOR ', ') AS genres,
                    c.file_name,
                    COUNT(DISTINCT r.id) AS reviews_count,
                    TRUNCATE(AVG(r.grade), 1) AS avg_review_grade
                    FROM book b
                    INNER JOIN book_has_genres bg ON b.id = bg.book_id
                    INNER JOIN genres g ON bg.genres_id = g.id
                    LEFT JOIN covers c ON b.covers_id = c.id
                    LEFT JOIN reviews r ON b.id = r.book_id
                    WHERE b.id = %s
                    GROUP BY b.id, b.title, b.description, b.year, b.publisher, b.author, b.size, b.covers_id
                    ;"""
        with db.connection.cursor(named_tuple = True) as cursor:
            cursor.execute(our_query,(book_id,))
            db_book = cursor.fetchone() 
        review_yours, reviews_alls = downloadRev(book_id=book_id)   
        return render_template('book/book_show.html', book=db_book, your_review=review_yours, all_reviews=reviews_alls)

def downloadRev(book_id):
        review_yours = None
        if current_user.is_authenticated: 
            our_query = """SELECT * FROM reviews WHERE users_id = %s AND book_id = %s ;"""
            with db.connection.cursor(named_tuple = True) as cursor:
                cursor.execute(our_query,(current_user.id, book_id))
                review_yours = cursor.fetchone() 
                our_query =  """SELECT reviews.*, CONCAT(users.last_name, ' ', users.first_name, ' ', users.middle_name) AS full_name
                            FROM reviews 
                            INNER JOIN users ON reviews.users_id = users.id 
                            WHERE  reviews.users_id != %s AND reviews.book_id = %s;"""
            with db.connection.cursor(named_tuple = True) as cursor:
                cursor.execute(our_query,(current_user.id, book_id))
                reviews_alls = cursor.fetchall() 
        else:
            our_query =  """SELECT reviews.*, CONCAT(users.last_name, ' ', users.first_name, ' ', users.middle_name) AS full_name
                        FROM reviews 
                        INNER JOIN users ON reviews.users_id = users.id 
                        WHERE reviews.book_id = %s ;"""   
            with db.connection.cursor(named_tuple = True) as cursor:
                cursor.execute(our_query,(book_id,))
                reviews_alls = cursor.fetchall()   
        return review_yours,reviews_alls