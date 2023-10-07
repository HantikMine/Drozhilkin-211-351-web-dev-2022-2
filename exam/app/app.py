from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from mysql_db import MySQL
import math
import bleach
import os
import hashlib
import mimetypes
from werkzeug.utils import secure_filename

app = Flask(__name__)
application = app

BOOKS_NUM = 3
ALL_PARAMS = ["title", "description", "year", "publisher", "author", "size"]
ALLOWED_EXTENSIONS = { 'png', 'jpg', 'jpeg'}
DIRECTORY_PATH = os.path.join(os.getcwd(), 'static', 'images')

def valid_files(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

class Book:
    def __init__(self):
        self.title = None
        self.description = None
        self.year = None
        self.publisher = None
        self.author = None
        self.size = None

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

@app.route('/books/<int:book_id>/delete', methods=['POST'])
@login_required
@check_rights('delete')
def book_delete(book_id):
   
    book = downloadBook(book_id=book_id)
    try:
        query = """
               SELECT COUNT(*) AS count_books
               FROM book
               WHERE covers_id = (SELECT covers_id FROM book WHERE id = %s);
        """
        with db.connection.cursor(named_tuple = True) as cursor:
                    cursor.execute(query,(book_id,)) 
                    nums_of_cover = cursor.fetchone().count_books
        if nums_of_cover==1:         
            query = """
                    SELECT covers.file_name FROM book JOIN covers ON book.covers_id = covers.id WHERE book.id = %s
            """
            with db.connection.cursor(named_tuple = True) as cursor:
                        cursor.execute(query,(book_id,)) 
                        cover_name = cursor.fetchone().file_name
                        file_path = os.path.join(DIRECTORY_PATH, cover_name)
            query = """
                   DELETE FROM covers
                   WHERE id = (SELECT covers_id FROM book WHERE id = %s);
            """
            with db.connection.cursor(named_tuple = True) as cursor:
                        cursor.execute(query,(book_id,)) 
                        db.connection.commit()        
        query ="""
                DELETE FROM book
                WHERE id = %s;
        """
        with db.connection.cursor(named_tuple = True) as cursor:
                    cursor.execute(query,(book_id,)) 
                    db.connection.commit()
        if nums_of_cover==1:
             os.remove(file_path) 
        flash(f'Книга {book.title} успешно удалена', 'success')
    except:
        db.connection.rollback()
        flash('Ошибка при удалении', 'danger')    
    return redirect(url_for('index'))   

def downloadGenres(book_id):
    tmp_genres = {}
    if book_id!=-1:
        query = """
                    SELECT genres.id, genres.name FROM book
                    JOIN book_has_genres ON book.id = book_has_genres.book_id
                    JOIN genres ON book_has_genres.genres_id = genres.id
                    WHERE book.id = %s
        """
        with db.connection.cursor(named_tuple = True) as cursor:
            cursor.execute(query, (book_id,))
            genres = cursor.fetchall()
        tmp_genres = [ str(genre.id) for genre in genres]
    query = """
                SELECT * FROM genres
    """
    with db.connection.cursor(named_tuple = True) as cursor:
        cursor.execute(query)
        all_used_genres = cursor.fetchall()
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
            "text": request.form.get('description'),
            "users_id": current_user.id,
            "book_id": book_id
        }
        if params["text"]==None:
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
                    cursor.execute(our_query,(now_params['title'],now_params['description'],now_params['author'],now_params['year'],now_params['size'],now_params['publisher'],book_id)) 
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

def added_new_params(book_obj, params):
    for param in params:
        if params[param]!=None:
            setattr(book_obj, param, params[param])

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

@app.route('/book_add', methods=['GET'])
@login_required
@check_rights("create")    
def book_add():
    all_used_genres,_ = downloadGenres(-1)
    return render_template("book/book_new.html", genres = all_used_genres,  book={})

@app.route('/book_create', methods=['POST'])
@login_required
@check_rights("create")    
def book_create():
    all_used_genres,_ = downloadGenres(-1)
    
    new_genres = request.form.getlist('genre_id')
    now_params = downloadParams(ALL_PARAMS)
    book = Book()
    added_new_params(book,now_params)
    file = request.files["cover_img"]
    for param in now_params:
        if now_params[param]==None or (file.filename=="") or len(new_genres)==0:
            print("test")
            flash("Указаны не все параметры", "danger")
            return render_template("book/book_new.html", genres = all_used_genres, book=book, new_genres=new_genres)
        now_params[param] = bleach.clean(now_params[param])
    md5_hex = hashlib.md5(file.read()).hexdigest()
    file.seek(0)
    try:
        query = """
                SELECT * FROM covers WHERE MD5_hash = %s
        """
        with db.connection.cursor(named_tuple = True) as cursor:
                    cursor.execute(query,(md5_hex,)) 
                    cover = cursor.fetchone()            
        if cover==None:
             if valid_files(file.filename):
                  filename = secure_filename(file.filename)
                  mime_type, _ = mimetypes.guess_type(file.filename)
                  query = """
                    INSERT INTO covers (file_name, MIME_type, MD5_hash) VALUES (%s, %s, %s);
                    """
                  with db.connection.cursor(named_tuple = True) as cursor:
                        cursor.execute(query,(filename,mime_type,md5_hex)) 
                        db.connection.commit()  
                        commit_cover_Id = cursor.lastrowid
             else:
                  flash('Недопустимое расширение файла', 'danger')  
                  return render_template("book/book_new.html", genres = all_used_genres, book=book,  new_genres=new_genres)
        else:
             commit_cover_Id = cover.id               
        query = """
                INSERT INTO book (title, description, author, year, size, publisher, covers_id) VALUES (%s, %s, %s, %s, %s, %s, %s);
                """
        with db.connection.cursor(named_tuple = True) as cursor:
            cursor.execute(query,(now_params['title'],now_params['description'],now_params['author'],now_params['year'],now_params['size'],now_params['publisher'], commit_cover_Id)) 
            db.connection.commit() 
            book_id = cursor.lastrowid     
            for genre in new_genres:
                query = """
                        INSERT INTO book_has_genres (book_id, genres_id) VALUES (%s, %s);
                        """
                with db.connection.cursor(named_tuple = True) as cursor:
                        cursor.execute(query,(book_id,genre)) 
                        db.connection.commit()     
        if cover==None:
             file.save(os.path.join(DIRECTORY_PATH, filename))           
            
    except:
        db.connection.rollback()
        flash('Ошибка при добавлении', 'danger')  
        return render_template("book/book_new.html", genres = all_used_genres, book=book,  new_genres=new_genres)  
    return redirect(url_for('book_show', book_id=book_id))


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