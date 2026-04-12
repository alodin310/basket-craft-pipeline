import os
import pymysql
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

MYSQL = dict(
    host=os.environ["MYSQL_HOST"],
    port=int(os.environ["MYSQL_PORT"]),
    user=os.environ["MYSQL_USER"],
    password=os.environ["MYSQL_PASSWORD"],
    database=os.environ["MYSQL_DB"],
    cursorclass=pymysql.cursors.Cursor,
)

RDS = dict(
    host=os.environ["RDS_HOST"],
    port=int(os.environ["RDS_PORT"]),
    user=os.environ["RDS_USER"],
    password=os.environ["RDS_PASSWORD"],
    dbname=os.environ["RDS_DATABASE"],
)

TABLES = [
    "employees",
    "order_item_refunds",
    "order_items",
    "orders",
    "products",
    "users",
    "website_pageviews",
    "website_sessions",
]

MYSQL_TO_PG = {
    "int": "INTEGER",
    "int unsigned": "INTEGER",
    "smallint unsigned": "SMALLINT",
    "text": "TEXT",
    "timestamp": "TIMESTAMP",
}


def map_type(mysql_type):
    if mysql_type in MYSQL_TO_PG:
        return MYSQL_TO_PG[mysql_type]
    if mysql_type.startswith("varchar"):
        return mysql_type.upper().replace("VARCHAR", "VARCHAR")
    if mysql_type.startswith("decimal"):
        return mysql_type.upper().replace("DECIMAL", "NUMERIC")
    return "TEXT"


def extract_to_rds():
    rds = psycopg2.connect(**RDS)

    with rds, rds.cursor() as rds_cur:
        rds_cur.execute("CREATE SCHEMA IF NOT EXISTS raw")

        for table in TABLES:
            # Reconnect to MySQL for each table to avoid timeout
            mysql = pymysql.connect(**MYSQL)
            with mysql.cursor() as my_cur:
                # Get column definitions from MySQL
                my_cur.execute(f"DESCRIBE {table}")
                columns = my_cur.fetchall()

                col_defs = ", ".join(
                    f"{col[0]} {map_type(col[1])}" for col in columns
                )
                col_names = ", ".join(col[0] for col in columns)

                my_cur.execute(f"SELECT * FROM {table}")

            rds_cur.execute(f"DROP TABLE IF EXISTS raw.{table} CASCADE")
            rds_cur.execute(f"CREATE TABLE raw.{table} ({col_defs})")

            total = 0
            while True:
                chunk = my_cur.fetchmany(5000)
                if not chunk:
                    break
                execute_values(
                    rds_cur,
                    f"INSERT INTO raw.{table} ({col_names}) VALUES %s",
                    chunk,
                    page_size=5000,
                )
                total += len(chunk)

            mysql.close()

            print(f"  raw.{table}: {total:,} rows loaded")

    print("Extract to RDS complete.")


if __name__ == "__main__":
    extract_to_rds()
