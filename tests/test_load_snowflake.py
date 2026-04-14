import pandas as pd
import pytest
from load_snowflake import normalize_columns, make_sf_conn


def test_normalize_already_upper():
    df = pd.DataFrame({"NAME": [1], "AGE": [2]})
    result = normalize_columns(df)
    assert list(result.columns) == ["NAME", "AGE"]


def test_normalize_mixed_case():
    df = pd.DataFrame({"Name": [1], "age": [2], "Order_Id": [3]})
    result = normalize_columns(df)
    assert list(result.columns) == ["NAME", "AGE", "ORDER_ID"]


def test_make_sf_conn_raises_on_missing_account(monkeypatch):
    monkeypatch.delenv("SNOWFLAKE_ACCOUNT", raising=False)
    with pytest.raises(KeyError):
        make_sf_conn()
