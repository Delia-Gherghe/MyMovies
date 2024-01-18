from flask import Flask, redirect, url_for, render_template, request, jsonify
from mysql.connector import connect
import db
from flask_zipkin import Zipkin
import requests
from py_zipkin.zipkin import zipkin_span, ZipkinAttrs
from py_zipkin.encoding import Encoding
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app, Counter, Histogram
import time

app = Flask(__name__)
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {'/metrics': make_wsgi_app()})
zipkin = Zipkin(app, sample_rate=100)
app.config['ZIPKIN_DSN'] = "http://zipkin:9411/api/v2/spans"

conn_dict = {'user': 'root', 'password': 'my-secret-pw', 'host': 'mysqldb', 'database': 'users_db'}

REQUEST_COUNT = Counter('users_request_count', 'Users Microservice Request Count', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('users_request_latency_seconds', 'Users Microservice Request Latency', ['method', 'endpoint'])

def default_handler(encoded_span):
    body = encoded_span
    return requests.post("http://zipkin:9411/api/v2/spans", data=body, headers={'Content-Type': 'application/json'})

@app.route("/")
def home_page():
    return render_template('home.html')

@app.route('/users')
def get_users():
    start = time.time()
    with connect(**conn_dict) as connection:
        select_users = "SELECT * FROM users"
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(select_users)
            users = cursor.fetchall()
    REQUEST_COUNT.labels(request.method, request.path, 200).inc()
    REQUEST_LATENCY.labels(request.method, request.path).observe(time.time() - start)
    return render_template('listUsers.html', users=users)

@app.route("/users/new", methods=["POST", "GET"])
def add_user():
    start = time.time()
    if request.method == "POST":
        username = request.form['username']
        email = request.form['email']
        birthday = request.form['birthday']

        with connect(**conn_dict) as connection:
            select_user_by_name_email = "SELECT * FROM users WHERE lower(username) = lower(%s) OR lower(email) = lower(%s)"
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(select_user_by_name_email, (username, email))
                user = cursor.fetchone()

        if user is not None:
            REQUEST_COUNT.labels(request.method, request.path, 400).inc()
            REQUEST_LATENCY.labels(request.method, request.path).observe(time.time() - start)
            return render_template('addUser.html', error="User with this username or email already exists!")
        else:
            with connect(**conn_dict) as connection:
                insert_user = "INSERT INTO users (username, email, date_of_birth) VALUES (%s, %s, %s);"
                with connection.cursor() as cursor:
                    cursor.execute(insert_user, (username, email, birthday))
                    connection.commit()
            REQUEST_COUNT.labels(request.method, request.path, 200).inc()
            REQUEST_LATENCY.labels(request.method, request.path).observe(time.time() - start)
            return redirect(url_for('get_users'))
    else:
        REQUEST_COUNT.labels(request.method, request.path, 200).inc()
        REQUEST_LATENCY.labels(request.method, request.path).observe(time.time() - start)
        return render_template('addUser.html')

@app.route("/users/<usr>")
def get_user_by_name(usr):
    start = time.time()
    with zipkin_span(service_name="users",
                     zipkin_attrs=ZipkinAttrs(trace_id=request.headers['X-B3-TraceID'],
                                              span_id=request.headers['X-B3-SpanID'],
                                              parent_span_id=request.headers['X-B3-ParentSpanID'],
                                              flags=request.headers['X-B3-Flags'],
                                              is_sampled=request.headers['X-B3-Sampled']),
                     span_name="get_user_by_name",
                     transport_handler=default_handler,
                     port=8000,
                     sample_rate=100,
                     encoding=Encoding.V2_JSON):
        with connect(**conn_dict) as connection:
            select_user_by_name = "SELECT * FROM users WHERE lower(username) = lower(%s)"
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(select_user_by_name, (usr,))
                user = cursor.fetchone()

    if user is None:
        REQUEST_COUNT.labels(request.method, request.path, 404).inc()
        REQUEST_LATENCY.labels(request.method, request.path).observe(time.time() - start)
        return jsonify({'error': 'User with name ' + usr + ' not found!'}), 404
    else:
        REQUEST_COUNT.labels(request.method, request.path, 200).inc()
        REQUEST_LATENCY.labels(request.method, request.path).observe(time.time() - start)
        return jsonify(user)

@app.route("/user/<id>")
def get_user_by_id(id):
    start = time.time()
    with zipkin_span(service_name="users",
                     zipkin_attrs=ZipkinAttrs(trace_id=request.headers['X-B3-TraceID'],
                                              span_id=request.headers['X-B3-SpanID'],
                                              parent_span_id=request.headers['X-B3-ParentSpanID'],
                                              flags=request.headers['X-B3-Flags'],
                                              is_sampled=request.headers['X-B3-Sampled']),
                     span_name="get_user_by_id",
                     transport_handler=default_handler,
                     port=8000,
                     sample_rate=100,
                     encoding=Encoding.V2_JSON):
        with connect(**conn_dict) as connection:
            select_user_by_id = "SELECT * FROM users WHERE user_id = %s"
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(select_user_by_id, (id,))
                user = cursor.fetchone()

    REQUEST_COUNT.labels(request.method, '/user/id', 200).inc()
    REQUEST_LATENCY.labels(request.method, '/user/id').observe(time.time() - start)
    return jsonify(user)

@app.route("/all_users")
def get_all_users():
    start = time.time()
    with zipkin_span(service_name="users",
                     zipkin_attrs=ZipkinAttrs(trace_id=request.headers['X-B3-TraceID'],
                                              span_id=request.headers['X-B3-SpanID'],
                                              parent_span_id=request.headers['X-B3-ParentSpanID'],
                                              flags=request.headers['X-B3-Flags'],
                                              is_sampled=request.headers['X-B3-Sampled']),
                     span_name="get_all_users",
                     transport_handler=default_handler,
                     port=8000,
                     sample_rate=100,
                     encoding=Encoding.V2_JSON):
        with connect(**conn_dict) as connection:
            select_users = "SELECT * FROM users"
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(select_users)
                users = cursor.fetchall()
    REQUEST_COUNT.labels(request.method, request.path, 200).inc()
    REQUEST_LATENCY.labels(request.method, request.path).observe(time.time() - start)
    return jsonify(users)

if __name__ == '__main__':
    app.run(debug=True, port=8000)