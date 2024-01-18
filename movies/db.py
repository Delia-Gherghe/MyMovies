from mysql.connector import connect, errors

genre_list = [{"name": "Horror"},
              {"name": "Comedy"},
              {"name": "Sci-Fi"}]

movie_list = [{"title": "Dune", "year": 2021, "duration": 155, "genre_id": 3},
              {"title": "Avatar", "year": 2009, "duration": 162, "genre_id": 3},
              {"title": "Barbie", "year": 2023, "duration": 114, "genre_id": 2}]

with connect(host='mysqldb', user='root', password='my-secret-pw') as connection:
    try:
        create_db_query = "CREATE DATABASE movies_db"
        with connection.cursor() as cursor:
            cursor.execute(create_db_query)
            connection.commit()
    except errors.DatabaseError:
        pass

with connect(host='mysqldb', user='root', password='my-secret-pw', database='movies_db') as connection:
    try:
        create_genres_table_query = """CREATE TABLE genres(
genre_id INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
name VARCHAR(50) NOT NULL);"""
        create_movies_table_query = """CREATE TABLE movies(
movie_id INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
title VARCHAR(50) NOT NULL,
year INT,
duration INT,
genre_id INT REFERENCES genres(genre_id) ON DELETE SET NULL);"""
        with connection.cursor() as cursor:
            cursor.execute(create_genres_table_query)
            cursor.execute(create_movies_table_query)
            connection.commit()
    except errors.ProgrammingError:
        pass

    select_genres = "SELECT * FROM genres"
    select_movies = "SELECT * FROM movies"
    with connection.cursor() as cursor:
        cursor.execute(select_genres)
        result = cursor.fetchall()
        if len(result) == 0:
            insert_template = "INSERT INTO genres (name) VALUES (%s)"
            for genre in genre_list:
                cursor.execute(insert_template, (genre['name'],))
                connection.commit()

    with connection.cursor() as cursor:
        cursor.execute(select_movies)
        result = cursor.fetchall()
        if len(result) == 0:
            insert_template = "INSERT INTO movies (title, year, duration, genre_id) VALUES (%s, %s, %s, %s)"
            for movie in movie_list:
                cursor.execute(insert_template, (movie['title'], movie['year'], movie['duration'], movie['genre_id']))
                connection.commit()

    with connection.cursor() as cursor:
        cursor.execute(select_genres)
        result = cursor.fetchall()
        for row in result:
            print(row)

    with connection.cursor() as cursor:
        cursor.execute(select_movies)
        result = cursor.fetchall()
        for row in result:
            print(row)