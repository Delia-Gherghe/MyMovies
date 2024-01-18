from flask import Flask, redirect, url_for, render_template, request, jsonify
from mysql.connector import connect
import db
import requests
from flask_zipkin import Zipkin
from py_zipkin.zipkin import zipkin_span, ZipkinAttrs, zipkin_client_span
from py_zipkin.request_helpers import create_http_headers
from py_zipkin.encoding import Encoding
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app, Counter, Histogram
import time

app = Flask(__name__)
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {'/metrics': make_wsgi_app()})
zipkin = Zipkin(app, sample_rate=100)
app.config['ZIPKIN_DSN'] = "http://zipkin:9411/api/v2/spans"

conn_dict = {'user': 'root', 'password': 'my-secret-pw', 'host': 'mysqldb', 'database': 'watchlist_db'}

REQUEST_COUNT = Counter('watchlists_request_count', 'Watchlist Microservice Request Count', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('watchlists_request_latency_seconds', 'Watchlist Microservice Request Latency', ['method', 'endpoint'])

def default_handler(encoded_span):
    body = encoded_span
    return requests.post("http://zipkin:9411/api/v2/spans", data=body, headers={'Content-Type': 'application/json'})

@zipkin_client_span(service_name="watchlists", span_name="get_user")
def get_user(id):
    headers = create_http_headers()
    r = requests.get("http://users:8000/user/" + str(id), headers=headers)
    return r.json()

@zipkin_client_span(service_name="watchlists", span_name="get_movies")
def get_movies():
    headers = create_http_headers()
    r = requests.get("http://movies:8001/all_movies", headers=headers)
    return r.json()

@app.route("/watchlist/delete/<id>")
def delete_watch_by_id(id):
    start = time.time()
    with connect(**conn_dict) as connection:
        select_watch_by_id = "SELECT * FROM watchlist WHERE watch_id = %s"
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(select_watch_by_id, (id,))
            watch = cursor.fetchone()

    with connect(**conn_dict) as connection:
        delete_watch = "DELETE FROM watchlist WHERE watch_id = %s"
        with connection.cursor() as cursor:
            cursor.execute(delete_watch, (id,))
            connection.commit()
    REQUEST_COUNT.labels(request.method, '/watchlist/delete/id', 200).inc()
    REQUEST_LATENCY.labels(request.method, '/watchlist/delete/id').observe(time.time() - start)
    return redirect(url_for('get_watchlist_by_user', id=watch['user_id']))

@app.route("/watchlist/<movie_id>/new", methods=["POST", "GET"])
def add_watch(movie_id):
    start = time.time()
    headers = {}
    headers.update(zipkin.create_http_headers_for_new_span())
    r = requests.get("http://movies:8001/movies/" + str(movie_id), headers=headers)
    movie = r.json()

    if request.method == "POST":
        username = request.form['username']

        headers = {}
        headers.update(zipkin.create_http_headers_for_new_span())
        r = requests.get("http://users:8000/users/" + str(username), headers=headers)
        if r.status_code == 404:
            REQUEST_COUNT.labels(request.method, '/watchlist/movie_id/new', 404).inc()
            REQUEST_LATENCY.labels(request.method, '/watchlist/movie_id/new').observe(time.time() - start)
            return render_template('addWatch.html', movie=movie, error="User with this username does not exist!")
        else:
            user = r.json()

            with connect(**conn_dict) as connection:
                select_watch_by_user_movie = "SELECT * FROM watchlist WHERE user_id = %s AND movie_id = %s"
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute(select_watch_by_user_movie, (user['user_id'], movie_id))
                    watch = cursor.fetchone()

            if watch is not None:
                REQUEST_COUNT.labels(request.method, '/watchlist/movie_id/new', 400).inc()
                REQUEST_LATENCY.labels(request.method, '/watchlist/movie_id/new').observe(time.time() - start)
                return render_template('addWatch.html', movie=movie, error="The user has already added this movie to their watchlist!")
            else:
                with connect(**conn_dict) as connection:
                    insert_watch = "INSERT INTO watchlist (user_id, movie_id) VALUES (%s, %s);"
                    with connection.cursor() as cursor:
                        cursor.execute(insert_watch, (user['user_id'], movie_id))
                        connection.commit()
                REQUEST_COUNT.labels(request.method, '/watchlist/movie_id/new', 200).inc()
                REQUEST_LATENCY.labels(request.method, '/watchlist/movie_id/new').observe(time.time() - start)
                return redirect(url_for('get_watchlist_by_user', id=user['user_id']))
    else:
        REQUEST_COUNT.labels(request.method, '/watchlist/movie_id/new', 200).inc()
        REQUEST_LATENCY.labels(request.method, '/watchlist/movie_id/new').observe(time.time() - start)
        return render_template('addWatch.html', movie=movie)

@app.route("/watchlist/user/<id>")
def get_watchlist_by_user(id):
    start = time.time()
    with zipkin_span(service_name="watchlists", span_name="get_watchlist_by_user",
                     transport_handler=default_handler, port=8003, sample_rate=100, encoding=Encoding.V2_JSON):
        user = get_user(id)
        movies = get_movies()

    with connect(**conn_dict) as connection:
        select_watchlist = "SELECT * FROM watchlist WHERE user_id = %s"
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(select_watchlist, (id,))
            watchlist = cursor.fetchall()

    for i in range(len(watchlist)):
        for movie in movies:
            if movie['movie_id'] == watchlist[i]['movie_id']:
                watchlist[i]['movie'] = movie['title']

    REQUEST_COUNT.labels(request.method, '/watchlist/user/id', 200).inc()
    REQUEST_LATENCY.labels(request.method, '/watchlist/user/id').observe(time.time() - start)
    return render_template('listWatchlist.html', user=user, watchlist=watchlist)

@app.route("/watchlist/<movie_id>", methods=['DELETE'])
def delete_watchlist(movie_id):
    start = time.time()
    with zipkin_span(service_name="watchlists",
                     zipkin_attrs=ZipkinAttrs(trace_id=request.headers['X-B3-TraceID'],
                                              span_id=request.headers['X-B3-SpanID'],
                                              parent_span_id=request.headers['X-B3-ParentSpanID'],
                                              flags=request.headers['X-B3-Flags'],
                                              is_sampled=request.headers['X-B3-Sampled']),
                     span_name="delete_watchlist",
                     transport_handler=default_handler,
                     port=8003,
                     sample_rate=100,
                     encoding=Encoding.V2_JSON):
        with connect(**conn_dict) as connection:
            delete_watches = "DELETE FROM watchlist WHERE movie_id = %s"
            with connection.cursor() as cursor:
                cursor.execute(delete_watches, (movie_id,))
                connection.commit()

    REQUEST_COUNT.labels(request.method, '/watchlist/movie_id', 200).inc()
    REQUEST_LATENCY.labels(request.method, '/watchlist/movie_id').observe(time.time() - start)
    return jsonify({"message": "Watches deleted for movie with id " + str(movie_id)})

if __name__ == '__main__':
    app.run(debug=True, port=8003)