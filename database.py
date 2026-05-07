import os
import psycopg2


def get_connection():
    host = os.environ.get("DB_HOST")
    print("host------------------: ", host)
    conn = psycopg2.connect(
        # host= os.environ.get("DB_HOST"),
        # database= os.environ.get("DB_NAME"),
        # user= os.environ.get("DB_USER"),
        # password= os.environ.get("DB_PASSWORD"),
        host='localhost',
        database='catalogo_filmes',
        user='postgres',
        password='1234',
    )
    return conn

