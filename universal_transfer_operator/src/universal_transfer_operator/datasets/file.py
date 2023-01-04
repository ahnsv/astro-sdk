from __future__ import annotations

import io
import pathlib

import pandas as pd
import smart_open
from attr import define, field

from universal_transfer_operator.constants import FileType
from universal_transfer_operator.datasets.base import UniversalDataset


@define
class File(UniversalDataset):
    """
    Repersents all file dataset.

    :param path: Path to a file in the filesystem/Object stores
    :param conn_id: Airflow connection ID
    :param filetype: constant to provide an explicit file type
    :param normalize_config: parameters in dict format of pandas json_normalize() function.
    :param is_bytes: is bytes
    """

    path: str = field(default="")
    conn_id: str = field(default="")
    filetype: FileType | None = None
    normalize_config: dict | None = None
    is_bytes: bool = False

    @property
    def size(self) -> int:
        """
        Return the size in bytes of the given file.

        :return: File size in bytes
        """
        size: int = self.location.size
        return size

    def is_binary(self) -> bool:
        """
        Return a constants.FileType given the filepath. Uses a naive strategy, using the file extension.

        :return: True or False
        """
        result: bool = self.type.name == FileType.PARQUET
        return result

    def is_pattern(self) -> bool:
        """
        Returns True when file path is a pattern(eg. s3://bucket/folder or /folder/sample_* etc)

        :return: True or False
        """
        return not pathlib.PosixPath(self.path).suffix

    def create_from_dataframe(self, df: pd.DataFrame, store_as_dataframe: bool = True) -> None:
        """Create a file in the desired location using the values of a dataframe.

        :param store_as_dataframe: Whether the data should later be deserialized as a dataframe or as a file containing
            delimited data (e.g. csv, parquet, etc.).
        :param df: pandas dataframe
        """
        self.is_dataframe = store_as_dataframe
        with smart_open.open(self.path, mode="wb", transport_params=self.location.transport_params) as stream:
            self.type.create_from_dataframe(stream=stream, df=df)

    def export_to_dataframe(self, **kwargs) -> pd.DataFrame:
        """Read file from all supported location and convert them into dataframes."""
        mode = "rb" if self.is_binary() else "r"
        with smart_open.open(self.path, mode=mode, transport_params=self.location.transport_params) as stream:
            return self.type.export_to_dataframe(stream, **kwargs)

    def _convert_remote_file_to_byte_stream(self) -> io.IOBase:
        """
        Read file from all supported location and convert them into a buffer that can be streamed into other data
        structures.
        Due to noted issues with using smart_open with pandas (like
        https://github.com/RaRe-Technologies/smart_open/issues/524), we create a BytesIO or StringIO buffer
        before exporting to a dataframe. We've found a sizable speed improvement with this optimization

        :returns: an io object that can be streamed into a dataframe (or other object)
        """

        mode = "rb" if self.is_binary() else "r"
        remote_obj_buffer = io.BytesIO() if self.is_binary() else io.StringIO()
        with smart_open.open(self.path, mode=mode, transport_params=self.location.transport_params) as stream:
            remote_obj_buffer.write(stream.read())
        remote_obj_buffer.seek(0)
        return remote_obj_buffer

    def export_to_dataframe_via_byte_stream(self, **kwargs) -> pd.DataFrame:
        """Read files from all supported locations and convert them into dataframes.
        Due to noted issues with using smart_open with pandas (like
        https://github.com/RaRe-Technologies/smart_open/issues/524), we create a BytesIO or StringIO buffer
        before exporting to a dataframe. We've found a sizable speed improvement with this optimization.
        """

        return self.type.export_to_dataframe(self._convert_remote_file_to_byte_stream(), **kwargs)

    def exists(self) -> bool:
        """Check if the file exists or not"""
        file_exists: bool = self.location.exists()
        return file_exists

    def __str__(self) -> str:
        return self.path

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.location == other.location and self.type == other.type

    def __hash__(self) -> int:
        return hash((self.path, self.conn_id, self.filetype))
