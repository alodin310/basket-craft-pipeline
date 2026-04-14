import os
import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

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


def lowercase_columns(df):
    df.columns = [c.lower() for c in df.columns]
    return df


def make_rds_engine():
    url = (
        f"postgresql+psycopg2://{os.environ['RDS_USER']}:{os.environ['RDS_PASSWORD']}"
        f"@{os.environ['RDS_HOST']}:{os.environ['RDS_PORT']}/{os.environ['RDS_DATABASE']}"
    )
    return create_engine(url)


def make_sf_conn():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
    )


def load_tables():
    engine = make_rds_engine()
    sf = make_sf_conn()

    with engine.connect() as conn:
        for table in TABLES:
            df = pd.read_sql(f"SELECT * FROM raw.{table}", conn)
            df = lowercase_columns(df)
            success, nchunks, nrows, _ = write_pandas(
                sf,
                df,
                table_name=table,
                database=os.environ["SNOWFLAKE_DATABASE"].upper(),
                schema=os.environ["SNOWFLAKE_SCHEMA"].upper(),
                overwrite=True,
                auto_create_table=True,
            )
            print(f"  {table}: {nrows:,} rows loaded")

    sf.close()
    print("Load to Snowflake complete.")


if __name__ == "__main__":
    load_tables()
