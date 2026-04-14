import pandas as pd
import pytest
from load_snowflake import lowercase_columns, make_sf_conn


def test_lowercase_already_lower():
    df = pd.DataFrame({"name": [1], "age": [2]})
    result = lowercase_columns(df)
    assert list(result.columns) == ["name", "age"]


def test_lowercase_mixed_case():
    df = pd.DataFrame({"Name": [1], "AGE": [2], "Order_Id": [3]})
    result = lowercase_columns(df)
    assert list(result.columns) == ["name", "age", "order_id"]


def test_make_sf_conn_raises_on_missing_account(monkeypatch):
    monkeypatch.delenv("SNOWFLAKE_ACCOUNT", raising=False)
    with pytest.raises(KeyError):
        make_sf_conn()
