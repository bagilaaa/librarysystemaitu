import json

from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
from psycopg2 import sql

app = Flask(__name__)
app.secret_key = 'ff6c0d2e0f495a630213a60910d0bc4d0931a42384ae4e06'

db_params = {
    'dbname': 'postgres',
    'user': 'postgres',
    'password': '2007',
    'host': 'localhost',
    'port': '5432'
}

def create_table():
    connection = psycopg2.connect(**db_params)
    cursor = connection.cursor()

    create_table_query = '''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            email VARCHAR(100) NOT NULL,
            password VARCHAR(50) NOT NULL,
            speciality VARCHAR(50) NOT NULL,
            "group" VARCHAR(50) NOT NULL
        );
    '''

    cursor.execute(create_table_query)
    connection.commit()

    cursor.close()
    connection.close()

#get data about books from JSON file
def load_data():
    # download data from json
    with open('data.json', 'r') as f:
        data = json.load(f)
    return data

# creating route to the pages
@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/home')
def home():
    items = load_data()
    return render_template('home.html', items=items)

@app.route('/admin_home')
def admin_home():
    items = load_data()
    return render_template('admin_home.html', items=items)

@app.route('/admin_about')
def admin_about():
    return render_template('admin_about.html')

# registering new user
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']

            # checking if the user exists in the table users
            connection = psycopg2.connect(**db_params)
            cursor = connection.cursor()

            select_query = sql.SQL('SELECT * FROM users WHERE username = {} OR email = {};').format(
                sql.Literal(username),
                sql.Literal(email)
            )

            cursor.execute(select_query)
            existing_user = cursor.fetchone()
            # if exists then display message
            if existing_user:
                cursor.close()
                connection.close()
                return "User with this username or email already exists. Please choose a different username or email."

            # registering new user and add to the table
            insert_query = sql.SQL(
                'INSERT INTO users (username, email, password, speciality, "group") VALUES ({}, {}, {}, {}, {});').format(
                sql.Literal(username),
                sql.Literal(email),
                sql.Literal(password),
                sql.Literal(request.form['speciality']),
                sql.Literal(request.form['group'])
            )

            cursor.execute(insert_query)
            connection.commit()

            cursor.close()
            connection.close()

            return redirect(url_for('home'))
        except Exception as e:
            return f"Error during registration: {str(e)}"

    return render_template('register.html')

# login user
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        connection = psycopg2.connect(**db_params)
        cursor = connection.cursor()
        # checking of user with this username and password
        select_query = sql.SQL('SELECT * FROM users WHERE username = {} AND password = {};').format(
            sql.Literal(username),
            sql.Literal(password)
        )

        cursor.execute(select_query)
        user = cursor.fetchone()

        cursor.close()
        connection.close()
        #if user exists then transfer to home page
        if user:
            return redirect(url_for('home'))
        else:         #if user do not exists then display message
            return 'Login failed. Check your username and password.'

    return render_template('login.html')


@app.route('/book/<book_name>')
def book(book_name):
    # get info about books from json
    with open('data.json', 'r') as file:
        books = json.load(file)

    # choosing and finding selected book
    selected_book = next((b for b in books if b['name'] == book_name), None)
    # open selected book in html
    if selected_book:
        return render_template('book.html', book=selected_book)
    else:
        return render_template('error.html', error_message=f'Book "{book_name}" not found')

@app.route('/add_to_profile', methods=['POST'])
def add_to_profile():
    if request.method == 'POST':
        book_name = request.form.get('book_name')

        # initialize an empty list
        added_books = session.get('added_books', [])

        # adding book to the list
        added_books.append(book_name)
        session['added_books'] = added_books

        return redirect(url_for('book', book_name=book_name))
    else:
        return redirect(url_for('home'))

@app.route('/profile')
def profile():
        # display books in the user profile
    added_books = session.get('added_books', [])
    return render_template('profile.html', added_books=added_books)


@app.route('/delete_from_profile', methods=['POST'])
def delete_from_profile():
    if request.method == 'POST':
        book_name = request.form.get('book_name')

        # list
        added_books = session.get('added_books', [])

        # delete the book from the list
        added_books.remove(book_name)

        # show updated list
        session['added_books'] = added_books

        return redirect(url_for('profile'))
    else:
        return redirect(url_for('home'))


@app.route('/logout')
def logout():
    # log out from profile
    session.clear()
    # redirect to welcome page
    return redirect(url_for('welcome'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        connection = psycopg2.connect(**db_params)
        cursor = connection.cursor()

        query = '''
            SELECT * FROM admins
            WHERE username = %s AND email = %s AND password = %s;
        '''

        cursor.execute(query, (username, email, password))
        admin = cursor.fetchone()

        cursor.close()
        connection.close()

        if admin:
            session['is_admin'] = True
            return redirect(url_for('admin_home'))
        else:
            return 'Admin login failed. Check your credentials.'

    return render_template('admin_login.html')

# function only for admins to admin pages
def admin_required(func):
    def wrapper(*args, **kwargs):
        if session.get('is_admin', False):
            return func(*args, **kwargs)
        else:
            return redirect(url_for('home'))
    return wrapper

@app.route('/admin/users')
def admin_users():
    # check if the user is admin
    is_admin = session.get('is_admin', False)

    if not is_admin:
        return redirect(url_for('welcome'))  #if is not admin transfer to welcome page

    # to check for the admin values
    connection = psycopg2.connect(**db_params)
    cursor = connection.cursor()

    query = '''
        SELECT * FROM users;
    '''

    cursor.execute(query)
    all_users = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('admin_users.html', all_users=all_users)

# display onformation about user, page available only for admins
@app.route('/profile/<int:user_id>', methods=['GET'])
def user_profile(user_id):
    connection = psycopg2.connect(**db_params)
    cursor = connection.cursor()

    query = '''
        SELECT id, username, email, speciality, "group"
        FROM users
        WHERE id = %s;
    '''

    cursor.execute(query, (user_id,))
    user_info = cursor.fetchone()

    cursor.close()
    connection.close()

    # open selected user profile
    if user_info:
        return render_template('user_profile.html', user_info=user_info)
    else:
        return render_template('error.html', error_message='User not found')


if __name__ == '__main__':
    app.run(debug=True)
