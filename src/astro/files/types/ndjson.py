import io
import json
import time
from typing import Optional

import pandas as pd

from astro.constants import DEFAULT_CHUNK_SIZE
from astro.constants import FileType as FileTypeConstants
from astro.files.types.base import FileType


class NDJSONFileType(FileType):
    """Concrete implementation to handle NDJSON file type"""

    def export_to_dataframe(self, stream, **kwargs):
        """read ndjson file from one of the supported locations and return dataframe

        :param stream: file stream object
        """
        start = time.time()
        return NDJSONFileType.flatten(self.normalize_config, stream)
        print(">>>>>>>>>>>>>>>> 6 NDJSONFileType.flatten: ", time.time() - start)

    def create_from_dataframe(self, df: pd.DataFrame, stream: io.TextIOWrapper) -> None:
        """Write ndjson file to one of the supported locations

        :param df: pandas dataframe
        :param stream: file stream object
        """
        df.to_json(stream, orient="records", lines=True)

    @property
    def name(self):
        return FileTypeConstants.NDJSON

    @staticmethod
    def flatten(
        normalize_config: Optional[dict], stream: io.TextIOWrapper
    ) -> pd.DataFrame:
        """
        Flatten the nested ndjson/json.

        :param normalize_config: parameters in dict format of pandas json_normalize() function.
            https://pandas.pydata.org/docs/reference/api/pandas.json_normalize.html
        :param stream: io.TextIOWrapper object for the file
        :type normalize_config: dict
        :type stream: io.TextIOWrapper
        :return: return dataframe containing the loaded data
        :rtype: `pandas.DataFrame`
        """
        normalize_config = normalize_config or {}

        df = None
        start = time.time()
        rows = stream.readlines(DEFAULT_CHUNK_SIZE)
        print(">>>>>>>>>>>>>>>> 7 stream.readlines: ", time.time() - start)
        while len(rows) > 0:
            if df is None:
                df = pd.DataFrame(
                    pd.json_normalize(
                        [json.loads(row) for row in rows], **normalize_config
                    )
                )
            start = time.time()
            rows = stream.readlines(DEFAULT_CHUNK_SIZE)
            print(">>>>>>>>>>>>>>>> 7 stream.readlines: ", time.time() - start)
        return df
