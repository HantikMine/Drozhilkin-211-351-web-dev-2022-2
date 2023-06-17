from flask import Flask, render_template, request, make_response

app = Flask(__name__)
application = app

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/headers')
def headers():
    return render_template("headers.html")
    
@app.route('/args')
def args():
    return render_template("args.html")

@app.route('/cookies')
def cookies():
    resp = make_response(render_template("cookies.html"))
    if 'cookie1' in request.cookies: 
        resp.set_cookie('cookie1', 'test', expires = 0)
    else:
        resp.set_cookie('cookie1', 'test')

    return resp

@app.route('/form', methods = ['GET', 'POST'])
def form():
    return render_template("form.html")

@app.errorhandler(404)
def page_not_found(error):
    return render_template('page_not_found.html'), 404

@app.route('/phone_validator', methods = ['GET', 'POST'])
def phone_validator():
    error_messages = [
        'Ошибка ввода. Неверное количество цифр.', 
        'Ошибка ввода. В номере присутствуют недопустимые символы.',
    ]
    allowed_chars = [' ', '(', ')', '-', '.', '+', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
    phone_number = None
    error_msg = None
    is_invalid = False
    
    if request.method == 'POST':
        num_digits_in_phone = 0
        nums_in_phone_number = ''
        phone_number = request.form.get('phone_number')
        for char in phone_number:
            if char not in allowed_chars:
                error_msg = error_messages[1]
                is_invalid = True
                break
            if char.isdigit():
                num_digits_in_phone += 1
                nums_in_phone_number += str(char)

        if len(nums_in_phone_number) == 11 and ((phone_number[0]=='+' and phone_number[1] == '7') or phone_number[0] == '8'):
            phone_number = f'8-{nums_in_phone_number[1:4]}-{nums_in_phone_number[4:7]}-{nums_in_phone_number[7:9]}-{nums_in_phone_number[9:]}'
        elif len(nums_in_phone_number) == 10:
            phone_number = f'8-{nums_in_phone_number[0:3]}-{nums_in_phone_number[3:6]}-{nums_in_phone_number[6:8]}-{nums_in_phone_number[8:]}'
        elif not is_invalid:
            is_invalid = True
            error_msg = error_messages[0]

    return render_template('phone_validator.html', phone_number=phone_number, is_invalid=is_invalid, error_msg=error_msg)