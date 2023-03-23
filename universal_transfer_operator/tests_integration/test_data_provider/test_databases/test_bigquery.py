"""Tests specific to the BigQuery Database implementation."""
import pathlib
from pathlib import Path

import pandas as pd
import pytest
import sqlalchemy

from universal_transfer_operator.constants import TransferMode
from universal_transfer_operator.data_providers.database.google.bigquery import BigqueryDataProvider
from universal_transfer_operator.data_providers.filesystem.base import FileStream
from universal_transfer_operator.datasets.file.base import File
from universal_transfer_operator.datasets.table import Metadata, Table
from universal_transfer_operator.settings import BIGQUERY_SCHEMA

DEFAULT_CONN_ID = "google_cloud_default"
CUSTOM_CONN_ID = "gcp_conn"
SUPPORTED_CONN_IDS = [DEFAULT_CONN_ID, CUSTOM_CONN_ID]
CWD = pathlib.Path(__file__).parent


@pytest.mark.integration
def test_bigquery_run_sql():
    """Test run_sql against bigquery database"""
    statement = "SELECT 1 + 1;"
    database = BigqueryDataProvider(
        dataset=Table(name="some_table", conn_id="gcp_conn"), transfer_mode=TransferMode.NONNATIVE
    )
    response = database.run_sql(statement, handler=lambda x: x.first())
    assert response[0] == 2


@pytest.mark.integration
def test_table_exists_raises_exception():
    """Test if table exists in bigquery database"""
    database = BigqueryDataProvider(
        Table(name="inexistent-table", metadata=Metadata(schema=BIGQUERY_SCHEMA), conn_id=CUSTOM_CONN_ID),
        transfer_mode=TransferMode.NONNATIVE,
    )
    table = Table(name="inexistent-table", metadata=Metadata(schema=BIGQUERY_SCHEMA))
    assert not database.table_exists(table)


@pytest.mark.integration
@pytest.mark.parametrize(
    "dataset_table_fixture",
    [
        {
            "dataset": "BigqueryDataProvider",
            "table": Table(
                metadata=Metadata(schema=BIGQUERY_SCHEMA),
                columns=[
                    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
                    sqlalchemy.Column("name", sqlalchemy.String(60), nullable=False, key="name"),
                ],
            ),
        }
    ],
    indirect=True,
    ids=["bigquery"],
)
def test_bigquery_create_table_with_columns(dataset_table_fixture):
    """Test table creation with columns data"""
    database, table = dataset_table_fixture

    # Looking for specific columns in INFORMATION_SCHEMA.COLUMNS as Bigquery can add/remove columns in the table.
    statement = (
        f"SELECT TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE "
        f"FROM {table.metadata.schema}.INFORMATION_SCHEMA.COLUMNS WHERE table_name='{table.name}'"
    )
    response = database.run_sql(statement, handler=lambda x: x.first())
    assert response is None

    database.create_table(table)
    response = database.run_sql(statement, handler=lambda x: x.fetchall())
    rows = response
    assert len(rows) == 2
    assert rows[0] == (
        "astronomer-dag-authoring",
        f"{table.metadata.schema}",
        f"{table.name}",
        "id",
        "INT64",
    )

    assert rows[1] == (
        "astronomer-dag-authoring",
        f"{table.metadata.schema}",
        f"{table.name}",
        "name",
        "STRING(60)",
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "dataset_table_fixture",
    [
        {
            "dataset": "BigqueryDataProvider",
            "table": Table(metadata=Metadata(schema=BIGQUERY_SCHEMA)),
        },
    ],
    indirect=True,
    ids=["bigquery"],
)
def test_load_pandas_dataframe_to_table(dataset_table_fixture):
    """Test load_pandas_dataframe_to_table against bigquery"""
    database, table = dataset_table_fixture

    pandas_dataframe = pd.DataFrame(data={"id": [1, 2]})
    database.load_pandas_dataframe_to_table(pandas_dataframe, table)

    statement = f"SELECT * FROM {database.get_table_qualified_name(table)};"
    response = database.run_sql(statement, handler=lambda x: x.fetchall())

    rows = response
    assert len(rows) == 2
    assert rows[0] == (1,)
    assert rows[1] == (2,)


@pytest.mark.integration
@pytest.mark.parametrize(
    "dataset_table_fixture",
    [
        {
            "dataset": "BigqueryDataProvider",
            "table": Table(metadata=Metadata(schema=BIGQUERY_SCHEMA)),
        },
    ],
    indirect=True,
    ids=["bigquery"],
)
def test_load_file_to_table_natively_for_not_optimised_path(dataset_table_fixture):
    """Test loading on files to bigquery natively for non optimized path."""
    database, target_table = dataset_table_fixture
    filepath = f"{str(CWD)}/../../data/sample.csv"
    response = database.load_file_to_table_natively(File(filepath), target_table)
    assert response is None


@pytest.mark.integration
@pytest.mark.parametrize(
    "dataset_table_fixture",
    [
        {
            "dataset": "BigqueryDataProvider",
            "table": Table(metadata=Metadata(schema=BIGQUERY_SCHEMA)),
        },
    ],
    indirect=True,
    ids=["snowflake"],
)
def test_write_method(dataset_table_fixture):
    """Test write() for snowflake"""
    dp, table = dataset_table_fixture
    file_path = f"{str(CWD)}/../../data/sample.csv"
    fs = FileStream(
        remote_obj_buffer=file_path,
        actual_file=File(
            path=file_path,
        ),
        actual_filename=Path(file_path),
    )
    dp.write(source_ref=fs)
    rows = dp.fetch_all_rows(table=dp.dataset)
    rows.sort(key=lambda x: x[0])
    assert rows == [(1, "First"), (2, "Second"), (3, "Third with unicode पांचाल")]