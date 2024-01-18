from flask import Flask, redirect, url_for, render_template, request, jsonify
from mysql.connector import connect
import db
import requests
import datetime
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

conn_dict = {'user': 'root', 'password': 'my-secret-pw', 'host': 'mysqldb', 'database': 'ratings_reviews_db'}

REQUEST_COUNT = Counter('ratings_reviews_request_count', 'Ratings and Reviews Microservice Request Count', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('ratings_reviews_latency_seconds', 'Ratings and Reviews Microservice Request Latency', ['method', 'endpoint'])

def default_handler(encoded_span):
    body = encoded_span
    return requests.post("http://zipkin:9411/api/v2/spans", data=body, headers={'Content-Type': 'application/json'})

@zipkin_client_span(service_name="ratings_reviews", span_name="get_movie")
def get_movie(id):
    headers = create_http_headers()
    r = requests.get("http://movies:8001/movies/" + str(id), headers=headers)
    return r.json()

@zipkin_client_span(service_name="ratings_reviews", span_name="get_users")
def get_users():
    headers = create_http_headers()
    r = requests.get("http://users:8000/all_users", headers=headers)
    return r.json()

@zipkin_client_span(service_name="ratings_reviews", span_name="get_user")
def get_user(id):
    headers = create_http_headers()
    r = requests.get("http://users:8000/user/" + str(id), headers=headers)
    return r.json()

@zipkin_client_span(service_name="ratings_reviews", span_name="get_movies")
def get_movies():
    headers = create_http_headers()
    r = requests.get("http://movies:8001/all_movies", headers=headers)
    return r.json()

@app.route("/movies/<id>/info")
def get_reviews_by_movie_id(id):
    start = time.time()
    with zipkin_span(service_name="ratings_reviews", span_name="get_reviews_by_movie_id",
                     transport_handler=default_handler, port=8002, sample_rate=100, encoding=Encoding.V2_JSON):
        movie = get_movie(id)
        users = get_users()

    with connect(**conn_dict) as connection:
        select_reviews = "SELECT * FROM reviews WHERE movie_id = %s ORDER BY timestamp DESC"
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(select_reviews, (id,))
            reviews = cursor.fetchall()

    with connect(**conn_dict) as connection:
        select_average = "SELECT round(avg(rating), 1) average FROM ratings WHERE movie_id = %s"
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(select_average, (id,))
            average = cursor.fetchone()

    for i in range(len(reviews)):
        for user in users:
            if user['user_id'] == reviews[i]['user_id']:
                reviews[i]['username'] = user['username']

    REQUEST_COUNT.labels(request.method, '/movies/id/info', 200).inc()
    REQUEST_LATENCY.labels(request.method, '/movies/id/info').observe(time.time() - start)
    return render_template('listReviews.html', movie=movie, reviews=reviews, average=average)

@app.route("/reviews/<movie_id>/new", methods=["POST", "GET"])
def add_review(movie_id):
    start = time.time()
    if request.method == "POST":
        username = request.form['username']
        content = request.form['content']

        headers = {}
        headers.update(zipkin.create_http_headers_for_new_span())
        r = requests.get("http://users:8000/users/" + str(username), headers=headers)
        if r.status_code == 404:
            REQUEST_COUNT.labels(request.method, '/reviews/movie_id/new', 404).inc()
            REQUEST_LATENCY.labels(request.method, '/reviews/movie_id/new').observe(time.time() - start)
            return render_template('addReview.html', error="User with this username does not exist!")
        else:
            user = r.json()
            with connect(**conn_dict) as connection:
                insert_review = "INSERT INTO reviews (content, timestamp, user_id, movie_id) VALUES (%s, %s, %s, %s);"
                with connection.cursor() as cursor:
                    cursor.execute(insert_review, (content, datetime.datetime.now(), user['user_id'], movie_id))
                    connection.commit()
            REQUEST_COUNT.labels(request.method, '/reviews/movie_id/new', 200).inc()
            REQUEST_LATENCY.labels(request.method, '/reviews/movie_id/new').observe(time.time() - start)
            return redirect(url_for('get_reviews_by_movie_id', id=movie_id))
    else:
        REQUEST_COUNT.labels(request.method, '/reviews/movie_id/new', 200).inc()
        REQUEST_LATENCY.labels(request.method, '/reviews/movie_id/new').observe(time.time() - start)
        return render_template('addReview.html')

@app.route("/reviews/delete/<id>")
def delete_review_by_id(id):
    start = time.time()
    with connect(**conn_dict) as connection:
        select_review_by_id = "SELECT * FROM reviews WHERE review_id = %s"
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(select_review_by_id, (id,))
            review = cursor.fetchone()

    with connect(**conn_dict) as connection:
        delete_review = "DELETE FROM reviews WHERE review_id = %s"
        with connection.cursor() as cursor:
            cursor.execute(delete_review, (id,))
            connection.commit()
    REQUEST_COUNT.labels(request.method, '/reviews/delete/id', 200).inc()
    REQUEST_LATENCY.labels(request.method, '/reviews/delete/id').observe(time.time() - start)
    return redirect(url_for('get_reviews_by_movie_id', id=review['movie_id']))

@app.route("/ratings/delete/<id>")
def delete_rating_by_id(id):
    start = time.time()
    with connect(**conn_dict) as connection:
        select_rating_by_id = "SELECT * FROM ratings WHERE rating_id = %s"
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(select_rating_by_id, (id,))
            rating = cursor.fetchone()

    with connect(**conn_dict) as connection:
        delete_rating = "DELETE FROM ratings WHERE rating_id = %s"
        with connection.cursor() as cursor:
            cursor.execute(delete_rating, (id,))
            connection.commit()
    REQUEST_COUNT.labels(request.method, '/ratings/delete/id', 200).inc()
    REQUEST_LATENCY.labels(request.method, '/ratings/delete/id').observe(time.time() - start)
    return redirect(url_for('get_ratings_by_user', id=rating['user_id']))

@app.route("/ratings/<movie_id>/new", methods=["POST", "GET"])
def add_rating(movie_id):
    start = time.time()
    if request.method == "POST":
        username = request.form['username']
        mark = request.form['rating']

        headers = {}
        headers.update(zipkin.create_http_headers_for_new_span())
        r = requests.get("http://users:8000/users/" + str(username), headers=headers)
        if r.status_code == 404:
            REQUEST_COUNT.labels(request.method, '/ratings/movie_id/new', 404).inc()
            REQUEST_LATENCY.labels(request.method, '/ratings/movie_id/new').observe(time.time() - start)
            return render_template('addRating.html', error="User with this username does not exist!")
        else:
            user = r.json()

            with connect(**conn_dict) as connection:
                select_rating_by_user_movie = "SELECT * FROM ratings WHERE user_id = %s AND movie_id = %s"
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute(select_rating_by_user_movie, (user['user_id'], movie_id))
                    rating = cursor.fetchone()

            if rating is not None:
                REQUEST_COUNT.labels(request.method, '/ratings/movie_id/new', 400).inc()
                REQUEST_LATENCY.labels(request.method, '/ratings/movie_id/new').observe(time.time() - start)
                return render_template('addRating.html', error="The user has already rated this movie!")
            else:
                with connect(**conn_dict) as connection:
                    insert_rating = "INSERT INTO ratings (rating, user_id, movie_id) VALUES (%s, %s, %s);"
                    with connection.cursor() as cursor:
                        cursor.execute(insert_rating, (mark, user['user_id'], movie_id))
                        connection.commit()
                REQUEST_COUNT.labels(request.method, '/ratings/movie_id/new', 200).inc()
                REQUEST_LATENCY.labels(request.method, '/ratings/movie_id/new').observe(time.time() - start)
                return redirect(url_for('get_ratings_by_user', id=user['user_id']))
    else:
        REQUEST_COUNT.labels(request.method, '/ratings/movie_id/new', 200).inc()
        REQUEST_LATENCY.labels(request.method, '/ratings/movie_id/new').observe(time.time() - start)
        return render_template('addRating.html')

@app.route("/ratings/user/<id>")
def get_ratings_by_user(id):
    start = time.time()
    with zipkin_span(service_name="ratings_reviews", span_name="get_ratings_by_user",
                     transport_handler=default_handler, port=8002, sample_rate=100, encoding=Encoding.V2_JSON):
        user = get_user(id)
        movies = get_movies()

    with connect(**conn_dict) as connection:
        select_ratings = "SELECT * FROM ratings WHERE user_id = %s"
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(select_ratings, (id,))
            ratings = cursor.fetchall()

    for i in range(len(ratings)):
        for movie in movies:
            if movie['movie_id'] == ratings[i]['movie_id']:
                ratings[i]['movie'] = movie['title']

    REQUEST_COUNT.labels(request.method, '/ratings/user/id', 200).inc()
    REQUEST_LATENCY.labels(request.method, '/ratings/user/id').observe(time.time() - start)
    return render_template('listRatings.html', user=user, ratings=ratings)

@app.route("/ratings_reviews/<movie_id>", methods=['DELETE'])
def delete_ratings_reviews(movie_id):
    start = time.time()
    with zipkin_span(service_name="ratings_reviews",
                     zipkin_attrs=ZipkinAttrs(trace_id=request.headers['X-B3-TraceID'],
                                              span_id=request.headers['X-B3-SpanID'],
                                              parent_span_id=request.headers['X-B3-ParentSpanID'],
                                              flags=request.headers['X-B3-Flags'],
                                              is_sampled=request.headers['X-B3-Sampled']),
                     span_name="delete_ratings_reviews",
                     transport_handler=default_handler,
                     port=8002,
                     sample_rate=100,
                     encoding=Encoding.V2_JSON):
        with connect(**conn_dict) as connection:
            delete_reviews = "DELETE FROM reviews WHERE movie_id = %s"
            with connection.cursor() as cursor:
                cursor.execute(delete_reviews, (movie_id,))
                connection.commit()

        with connect(**conn_dict) as connection:
            delete_ratings = "DELETE FROM ratings WHERE movie_id = %s"
            with connection.cursor() as cursor:
                cursor.execute(delete_ratings, (movie_id,))
                connection.commit()
    REQUEST_COUNT.labels(request.method, '/ratings_reviews/movie_id', 200).inc()
    REQUEST_LATENCY.labels(request.method, '/ratings_reviews/movie_id').observe(time.time() - start)
    return jsonify({"message": "Reviews and ratings deleted for movie with id " + str(movie_id)})

if __name__ == '__main__':
    app.run(debug=True, port=8002)