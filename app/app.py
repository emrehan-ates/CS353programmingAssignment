
import re  
import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import datetime 

app = Flask(__name__) 

app.secret_key = 'abcdefgh'
  
app.config['MYSQL_HOST'] = 'db'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'cs353hw4db'
  
mysql = MySQL(app)  

@app.route('/')

@app.route('/login', methods =['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM User WHERE username = % s AND password = % s', (username, password, ))
        user = cursor.fetchone()
        if user:              
            session['loggedin'] = True
            session['userid'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            message = 'Logged in successfully!'
            return redirect(url_for('tasks'))
        else:
            message = 'Please enter correct username / password !'
    return render_template('login.html', message = message)


@app.route('/register', methods =['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form :
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM User WHERE username = % s', (username, ))
        account = cursor.fetchone()
        if account:
            message = 'Choose a different username!'
  
        elif not username or not password or not email:
            message = 'Please fill out the form!'

        else:
            cursor.execute('INSERT INTO User ( username, email, password) VALUES ( % s, % s, % s)', (username, email, password,))
            mysql.connection.commit()
            message = 'User successfully created!'

    elif request.method == 'POST':

        message = 'Please fill all the fields!'
    return render_template('register.html', message = message)

@app.route('/tasks', methods =['GET', 'POST'])
def tasks():
    user_id = session.get('userid')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST' and 'title' in request.form and 'description' in request.form and 'deadline' in request.form and 'task_type' in request.form:
        title = request.form['title']
        description = request.form['description']
        deadline_str = request.form['deadline']  # This is a string in format 'YYYY-MM-DDTHH:MM'
        deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        task_type = request.form['task_type']
        status = 'Todo'
        creation = datetime.now()
        creation = creation.strftime('%Y-%m-%d %H:%M:%S')
        completion_time = None
        cursor.execute('insert into Task(title, description, status, deadline, creation_time, completion_time, user_id, task_type) values (%s, %s, %s, %s, %s, %s, %s, %s)', (title, description, status, deadline, creation, completion_time, user_id, task_type,))
        mysql.connection.commit()

    cursor.execute('select * from Task where user_id=%s and status=%s order by deadline asc', (user_id,'Todo',))
    currentlist = cursor.fetchall()
    cursor.execute('select * from Task where user_id=%s and status=%s order by completion_time ', (user_id,'Done',))
    donelist = cursor.fetchall()
    return render_template('tasks.html', currentlist = currentlist, donelist = donelist)


@app.route('/delete', methods = ['POST'])
def delete():
    user_id = session.get('userid')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    task_id = request.form['task_id']
    cursor.execute('delete from Task where task_id=%s', (task_id,))
    mysql.connection.commit()
    return redirect(url_for('tasks'))


@app.route('/edit/<int:task_id>', methods=['GET','POST'])
def edit(task_id):
    user_id = session.get('user_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        deadline_str = request.form['deadline']
        task_type = request.form['task_type']
        deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')

        cursor.execute('update Task SET title=%s, description=%s, deadline=%s, task_type=%s where task_id=%s', (title, description, deadline, task_type, task_id,))
        mysql.connection.commit()
        return redirect(url_for('tasks'))
    
    cursor.execute('select * from Task where task_id=%s', (task_id,))
    task = cursor.fetchone()
    return render_template('edit.html', task = task)


@app.route('/done', methods=['POST'])
def done():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    task_id = request.form['task_id']
    done_at = datetime.now()
    done_at = done_at.strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('update Task SET status=%s, completion_time = %s where task_id=%s', ('Done', done_at,task_id,))
    mysql.connection.commit()
    return redirect(url_for('tasks'))

@app.route('/analysis', methods =['GET', 'POST'])
def analysis():
    user_id = session.get('userid')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    query1 = "select title, task_type, deadline, status from Task where user_id = %s order by deadline ASC"
    query2 = "select title, completion_time, (completion_time - creation_time)/3600 as time_spent from Task where user_id=%s AND status='Done' order by completion_time ASC"
    query3 = "select title, task_type, deadline from Task where user_id = %s AND status='Todo' order by deadline ASC"
    query4 = "select title, (completion_time - deadline)/3600 as latency from Task where user_id = %s AND completion_time > deadline"
    query5 = "select Task.task_type as task_type, COUNT(*) as completed_tasks from Task JOIN TaskType on Task.task_type = TaskType.type where Task.status = 'Done' and Task.user_id = %s group by Task.task_type order by completed_tasks DESC"

    cursor.execute(query1, (user_id,))
    tasks_by_deadline = cursor.fetchall()
    cursor.execute(query2, (user_id,))
    tasks_by_completion_time = cursor.fetchall()
    cursor.execute(query3, (user_id,))
    uncompleted_tasks = cursor.fetchall()
    cursor.execute(query4, (user_id,))
    overdue_tasks = cursor.fetchall()
    cursor.execute(query5, (user_id,))
    completed_tasks_by_type = cursor.fetchall()

    return render_template("analysis.html", tasks_by_deadline = tasks_by_deadline, tasks_by_completion_time = tasks_by_completion_time, uncompleted_tasks = uncompleted_tasks, overdue_tasks = overdue_tasks, completed_tasks_by_type = completed_tasks_by_type )


@app.route('/logout', methods=['GET','POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
