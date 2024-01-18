from flask import Flask, redirect, url_for, render_template, request, jsonify
from mysql.connector import connect
import db
import requests
from flask_zipkin import Zipkin
from py_zipkin.zipkin import zipkin_span, ZipkinAttrs
from py_zipkin.encoding import Encoding
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app, Counter, Histogram
import time

app = Flask(__name__)
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {'/metrics': make_wsgi_app()})
zipkin = Zipkin(app, sample_rate=100)
app.config['ZIPKIN_DSN'] = "http://zipkin:9411/api/v2/spans"

conn_dict = {'user': 'root', 'password': 'my-secret-pw', 'host': 'mysqldb', 'database': 'movies_db'}

REQUEST_COUNT = Counter('movies_request_count', 'Movies Microservice Request Count', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('movies_request_latency_seconds', 'Movies Microservice Request Latency', ['method', 'endpoint'])

def default_handler(encoded_span):
    body = encoded_span
    return requests.post("http://zipkin:9411/api/v2/spans", data=body, headers={'Content-Type': 'application/json'})

@app.route("/genres")
def get_genres():
    start = time.time()
    with connect(**conn_dict) as connection:
        select_genres = "SELECT * FROM genres ORDER BY name"
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(select_genres)
            genres = cursor.fetchall()
    REQUEST_COUNT.labels(request.method, request.path, 200).inc()
    REQUEST_LATENCY.labels(request.method, request.path).observe(time.time() - start)
    return render_template('listGenres.html', genres=genres)

@app.route("/genres/new", methods=["POST", "GET"])
def add_genre():
    start = time.time()
    if request.method == "POST":
        name = request.form['name']

        with connect(**conn_dict) as connection:
            insert_genre = "INSERT INTO genres (name) VALUES (%s);"
            with connection.cursor() as cursor:
                cursor.execute(insert_genre, (name,))
                connection.commit()
        REQUEST_COUNT.labels(request.method, request.path, 200).inc()
        REQUEST_LATENCY.labels(request.method, request.path).observe(time.time() - start)
        return redirect(url_for('get_genres'))
    else:
        REQUEST_COUNT.labels(request.method, request.path, 200).inc()
        REQUEST_LATENCY.labels(request.method, request.path).observe(time.time() - start)
        return render_template('addGenre.html')

@app.route("/genres/<id>")
def get_genre_info(id):
    start = time.time()
    with connect(**conn_dict) as connection:
        select_genre_by_id = "SELECT * FROM genres WHERE genre_id = %s"
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(select_genre_by_id, (id,))
            genre = cursor.fetchone()

    with connect(**conn_dict) as connection:
        select_movies_by_genre_id = "SELECT * FROM movies WHERE genre_id = %s ORDER BY title"
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(select_movies_by_genre_id, (id,))
            movies = cursor.fetchall()

    REQUEST_COUNT.labels(request.method, '/genres/id', 200).inc()
    REQUEST_LATENCY.labels(request.method, '/genres/id').observe(time.time() - start)
    return render_template('infoGenre.html', genre=genre, movies=movies)

@app.route("/movies/<genre_id>/new", methods=["POST", "GET"])
def add_genre_movie(genre_id):
    start = time.time()
    if request.method == "POST":
        title = request.form['title']
        year = request.form['year']
        duration = request.form['duration']

        with connect(**conn_dict) as connection:
            insert_movie = "INSERT INTO movies (title, year, duration, genre_id) VALUES (%s, %s, %s, %s)"
            with connection.cursor() as cursor:
                cursor.execute(insert_movie, (title, year, duration, genre_id))
                connection.commit()
        REQUEST_COUNT.labels(request.method, '/movies/genre_id/new', 200).inc()
        REQUEST_LATENCY.labels(request.method, '/movies/genre_id/new').observe(time.time() - start)
        return redirect(url_for('get_genre_info', id=genre_id))
    else:
        REQUEST_COUNT.labels(request.method, '/movies/genre_id/new', 200).inc()
        REQUEST_LATENCY.labels(request.method, '/movies/genre_id/new').observe(time.time() - start)
        return render_template('addMovie.html')

@app.route("/movies/delete/<id>")
def delete_movie_by_id(id):
    start = time.time()
    with connect(**conn_dict) as connection:
        select_movie_by_id = "SELECT * FROM movies WHERE movie_id = %s"
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(select_movie_by_id, (id,))
            movie = cursor.fetchone()

    with connect(**conn_dict) as connection:
        delete_movie = "DELETE FROM movies WHERE movie_id = %s"
        with connection.cursor() as cursor:
            cursor.execute(delete_movie, (id,))
            connection.commit()

    headers = {}
    headers.update(zipkin.create_http_headers_for_new_span())
    requests.delete("http://ratings_reviews:8002/ratings_reviews/" + str(id), headers=headers)
    headers = {}
    headers.update(zipkin.create_http_headers_for_new_span())
    requests.delete("http://watchlists:8003/watchlist/" + str(id), headers=headers)

    REQUEST_COUNT.labels(request.method, '/movies/delete/id', 200).inc()
    REQUEST_LATENCY.labels(request.method, '/movies/delete/id').observe(time.time() - start)
    return redirect(url_for('get_genre_info', id=movie['genre_id']))

@app.route("/movies")
def get_movies():
    start = time.time()
    with connect(**conn_dict) as connection:
        select_movies = "SELECT movie_id, title, year, duration, name AS genre_name FROM movies m, genres g WHERE g.genre_id = m.genre_id ORDER BY title"
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(select_movies)
            movies = cursor.fetchall()
    REQUEST_COUNT.labels(request.method, request.path, 200).inc()
    REQUEST_LATENCY.labels(request.method, request.path).observe(time.time() - start)
    return render_template('listMovies.html', movies=movies)

@app.route("/movies/<id>")
def get_movie_by_id(id):
    start = time.time()
    with zipkin_span(service_name="movies",
                     zipkin_attrs=ZipkinAttrs(trace_id=request.headers['X-B3-TraceID'],
                                              span_id=request.headers['X-B3-SpanID'],
                                              parent_span_id=request.headers['X-B3-ParentSpanID'],
                                              flags=request.headers['X-B3-Flags'],
                                              is_sampled=request.headers['X-B3-Sampled']),
                     span_name="get_movie_by_id",
                     transport_handler=default_handler,
                     port=8001,
                     sample_rate=100,
                     encoding=Encoding.V2_JSON):
        with connect(**conn_dict) as connection:
            select_movie_by_id = "SELECT * FROM movies WHERE movie_id = %s"
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(select_movie_by_id, (id,))
                movie = cursor.fetchone()

    REQUEST_COUNT.labels(request.method, '/movies/id', 200).inc()
    REQUEST_LATENCY.labels(request.method, '/movies/id').observe(time.time() - start)
    return jsonify(movie)

@app.route("/all_movies")
def get_all_movies():
    start = time.time()
    with zipkin_span(service_name="movies",
                     zipkin_attrs=ZipkinAttrs(trace_id=request.headers['X-B3-TraceID'],
                                              span_id=request.headers['X-B3-SpanID'],
                                              parent_span_id=request.headers['X-B3-ParentSpanID'],
                                              flags=request.headers['X-B3-Flags'],
                                              is_sampled=request.headers['X-B3-Sampled']),
                     span_name="get_all_movies",
                     transport_handler=default_handler,
                     port=8001,
                     sample_rate=100,
                     encoding=Encoding.V2_JSON):
        with connect(**conn_dict) as connection:
            select_movies = "SELECT * FROM movies"
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(select_movies)
                movies = cursor.fetchall()

    REQUEST_COUNT.labels(request.method, request.path, 200).inc()
    REQUEST_LATENCY.labels(request.method, request.path).observe(time.time() - start)
    return jsonify(movies)

if __name__ == '__main__':
    app.run(debug=True, port=8001)