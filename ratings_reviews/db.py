from mysql.connector import connect, errors
import datetime

rating_list = [{"rating": 8, "user_id": 1, "movie_id": 1},
               {"rating": 9, "user_id": 1, "movie_id": 2},
               {"rating": 6, "user_id": 3, "movie_id": 2}]

review_list = [{"content": "Awesome acting! Great cinematography!", "timestamp": datetime.datetime(2023, 12, 30, 17, 32), "user_id": 2, "movie_id": 1},
               {"content": "Fun movie! Had a great time!", "timestamp": datetime.datetime(2024, 1, 1, 9, 40), "user_id": 2, "movie_id": 3},
               {"content": "One of my favorite movies!", "timestamp": datetime.datetime(2024, 1, 2, 12, 12), "user_id": 1, "movie_id": 1}]

with connect(host='mysqldb', user='root', password='my-secret-pw') as connection:
    try:
        create_db_query = "CREATE DATABASE ratings_reviews_db"
        with connection.cursor() as cursor:
            cursor.execute(create_db_query)
            connection.commit()
    except errors.DatabaseError:
        pass

with connect(host='mysqldb', user='root', password='my-secret-pw', database='ratings_reviews_db') as connection:
    try:
        create_ratings_table_query = """CREATE TABLE ratings(
rating_id INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
rating INT NOT NULL,
user_id INT NOT NULL,
movie_id INT NOT NULL,
CHECK (rating >= 1 AND rating <= 10));"""
        create_reviews_table_query = """CREATE TABLE reviews(
review_id INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
content VARCHAR(1000) NOT NULL,
timestamp DATETIME NOT NULL,
user_id INT NOT NULL,
movie_id INT NOT NULL);"""
        with connection.cursor() as cursor:
            cursor.execute(create_ratings_table_query)
            cursor.execute(create_reviews_table_query)
            connection.commit()
    except errors.ProgrammingError:
        pass

    select_ratings = "SELECT * FROM ratings"
    select_reviews = "SELECT * FROM reviews"
    with connection.cursor() as cursor:
        cursor.execute(select_ratings)
        result = cursor.fetchall()
        if len(result) == 0:
            insert_template = "INSERT INTO ratings (rating, user_id, movie_id) VALUES (%s, %s, %s)"
            for rating in rating_list:
                cursor.execute(insert_template, (rating['rating'], rating['user_id'], rating['movie_id']))
                connection.commit()

    with connection.cursor() as cursor:
        cursor.execute(select_reviews)
        result = cursor.fetchall()
        if len(result) == 0:
            insert_template = "INSERT INTO reviews (content, timestamp, user_id, movie_id) VALUES (%s, %s, %s, %s)"
            for review in review_list:
                cursor.execute(insert_template, (review['content'], review['timestamp'], review['user_id'], review['movie_id']))
                connection.commit()

    with connection.cursor() as cursor:
        cursor.execute(select_ratings)
        result = cursor.fetchall()
        for row in result:
            print(row)

    with connection.cursor() as cursor:
        cursor.execute(select_reviews)
        result = cursor.fetchall()
        for row in result:
            print(row)