from mysql.connector import connect, errors
import datetime

user_list = [{'username': 'John_Doe', 'email': 'johndoe@yahoo.com', 'dob': datetime.date(1988, 12, 2)},
             {'username': 'MaryJ', 'email': 'maryj@gmail.com', 'dob': datetime.date(1995, 8, 10)},
             {'username': 'DjokerNole', 'email': 'djokernole@gmail.com', 'dob': datetime.date(1987, 5, 22)}]

with connect(host='mysqldb', user='root', password='my-secret-pw') as connection:
    try:
        create_db_query = "CREATE DATABASE users_db"
        with connection.cursor() as cursor:
            cursor.execute(create_db_query)
            connection.commit()
    except errors.DatabaseError:
        pass

with connect(host='mysqldb', user='root', password='my-secret-pw', database='users_db') as connection:
    try:
        create_table_query = """CREATE TABLE users(
user_id INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
username VARCHAR(100) NOT NULL UNIQUE,
email VARCHAR(50) NOT NULL UNIQUE,
date_of_birth DATE NOT NULL);"""
        with connection.cursor() as cursor:
            cursor.execute(create_table_query)
            connection.commit()
    except errors.ProgrammingError:
        pass

    select_users = "SELECT * FROM users"
    with connection.cursor() as cursor:
        cursor.execute(select_users)
        result = cursor.fetchall()
        if len(result) == 0:
            insert_template = "INSERT INTO users (username, email, date_of_birth) VALUES (%s, %s, %s)"
            for user in user_list:
                cursor.execute(insert_template, (user['username'], user['email'], user['dob']))
                connection.commit()

    with connection.cursor() as cursor:
        cursor.execute(select_users)
        result = cursor.fetchall()
        for row in result:
            print(row)