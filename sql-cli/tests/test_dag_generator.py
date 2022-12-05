from pathlib import Path

import pytest
from conftest import DEFAULT_DATE

from sql_cli.dag_generator import Workflow, generate_dag
from sql_cli.exceptions import DagCycle, EmptyDag, WorkflowFilesDirectoryNotFound


def test_workflow(workflow, workflow_with_parameters, sql_file, sql_file_with_parameters):
    """Test that a simple build will return the sql files."""
    assert workflow.sorted_workflow_files() == [sql_file]
    assert workflow_with_parameters.sorted_workflow_files() == [sql_file_with_parameters]


def test_workflow_with_cycle(workflow_with_cycle):
    """Test that an exception is being raised when it is not a DAG."""
    with pytest.raises(DagCycle):
        assert workflow_with_cycle.sorted_workflow_files()


def test_workflow_without_workflow_files():
    """Test that an exception is being raised when it does not have any workflow files."""
    with pytest.raises(EmptyDag):
        Workflow(dag_id="workflow_without_workflow_files", start_date=DEFAULT_DATE, workflow_files=[])


@pytest.mark.parametrize("generate_tasks", [True, False])
def test_generate_dag(root_directory, dags_directory, generate_tasks):
    """Test that the whole DAG generation process including sql files parsing works."""
    dag_file = generate_dag(
        directory=root_directory, dags_directory=dags_directory, generate_tasks=generate_tasks
    )
    assert dag_file


@pytest.mark.parametrize("generate_tasks", [True, False])
def test_generate_dag_invalid_directory(root_directory, dags_directory, generate_tasks):
    """Test that an exception is being raised when the directory does not exist."""
    with pytest.raises(WorkflowFilesDirectoryNotFound):
        generate_dag(directory=Path("foo"), dags_directory=dags_directory, generate_tasks=generate_tasks)


compliant_dag = """# NOTE: This is an auto-generated file. Please do not edit this file manually.
from pathlib import Path

from airflow import DAG
from airflow.utils import timezone
from astro import sql as aql
from astro.constants import FileType
from astro.files import File
from astro.table import Metadata, Table

DAGS_FOLDER = Path(__file__).parent.as_posix()

with DAG(
    dag_id="basic",
    start_date=timezone.parse("2020-01-01 00:00:00"),
    schedule_interval=None,
) as dag:
    a = aql.transform_file(
        file_path=f"{DAGS_FOLDER}/include/basic/a.sql",
        parameters={},
        conn_id="my_test_sqlite",
        op_kwargs={
            "output_table": Table(
                name="a",
            ),
        },
        task_id="a",
    )
    b = aql.transform_file(
        file_path=f"{DAGS_FOLDER}/include/basic/b.sql",
        parameters={
            "a": a,
        },
        op_kwargs={
            "output_table": Table(
                name="b",
            ),
        },
        task_id="b",
    )
    c = aql.transform_file(
        file_path=f"{DAGS_FOLDER}/include/basic/c.sql",
        parameters={
            "a": a,
            "b": b,
        },
        op_kwargs={
            "output_table": Table(
                name="c",
            ),
        },
        task_id="c",
    )
"""


def test_generate_dag_black_compliant(root_directory, dags_directory):
    dag_file = generate_dag(directory=root_directory, dags_directory=dags_directory, generate_tasks=True)
    with open(dag_file) as file:
        file_str = file.read()
        assert file_str == compliant_dag
