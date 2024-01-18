from mysql.connector import connect, errors

watchlist_list = [{"user_id": 1, "movie_id": 1},
                  {"user_id": 1, "movie_id": 2},
                  {"user_id": 3, "movie_id": 2}]

with connect(host='mysqldb', user='root', password='my-secret-pw') as connection:
    try:
        create_db_query = "CREATE DATABASE watchlist_db"
        with connection.cursor() as cursor:
            cursor.execute(create_db_query)
            connection.commit()
    except errors.DatabaseError:
        pass

with connect(host='mysqldb', user='root', password='my-secret-pw', database='watchlist_db') as connection:
    try:
        create_watchlist_table_query = """CREATE TABLE watchlist(
watch_id INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
user_id INT NOT NULL,
movie_id INT NOT NULL);"""
        with connection.cursor() as cursor:
            cursor.execute(create_watchlist_table_query)
            connection.commit()
    except errors.ProgrammingError:
        pass

    select_watchlist = "SELECT * FROM watchlist"
    with connection.cursor() as cursor:
        cursor.execute(select_watchlist)
        result = cursor.fetchall()
        if len(result) == 0:
            insert_template = "INSERT INTO watchlist (user_id, movie_id) VALUES (%s, %s)"
            for watch in watchlist_list:
                cursor.execute(insert_template, (watch['user_id'], watch['movie_id']))
                connection.commit()

    with connection.cursor() as cursor:
        cursor.execute(select_watchlist)
        result = cursor.fetchall()
        for row in result:
            print(row)
