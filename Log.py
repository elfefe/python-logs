import inspect
import re
import sys
from datetime import datetime
import logging
import os
import traceback
from pathlib import Path

"""
To install libraries:
    pip install -r requirements.txt
"""
import google.cloud.logging
from google.cloud import error_reporting
from google.cloud.logging import Resource
from google.cloud.logging_v2.handlers import CloudLoggingHandler, setup_logging

"""
Check README.md for more information
"""


def get_google_project_id():
    if os.getenv('ENVIRONEMENT') == "PROD":
        return "odo-prod"
    return "sage-inn-292904"


class Log:
    _LOGS_FOLER = "logs"

    _LOG_FILE_DATE_FORMAT = '%Y-%m-%d'
    _LOGS_DATETIME_FORMAT = '%d-%m-%Y %H:%M:%S.%f'

    _PROJECT_TAG = os.path.basename(Path(__file__).parent.parent.absolute())

    class Level:
        INFO = "I"
        ERROR = "E"
        DEBUG = "D"
        WARNING = "W"

        @staticmethod
        def logger(level):
            if level == Log.Level.INFO:
                return logging.INFO
            if level == Log.Level.ERROR:
                return logging.ERROR
            if level == Log.Level.DEBUG:
                return logging.DEBUG
            if level == Log.Level.WARNING:
                return logging.WARNING
            return logging.NOTSET

    def __init__(self, log_name=None):
        self.log_name = log_name

        self._generate_log_name()
        self._create_dirs()

        self.handler = logging.FileHandler(filename=os.path.join(self.log_dir, "any.log"), encoding='utf-8', mode='a+')
        logging.basicConfig(
            handlers=[
                self.handler
            ],
            format="%(asctime)s %(levelname)s: %(message)s",
            datefmt="%F %T",
            level=logging.NOTSET
        )
        self.logger = logging.getLogger(log_name)

        self.cloud_project_id = None

    def verbose(self, text, level):
        if level == self.Level.ERROR:
            text = f"{text}\n{traceback.format_exc()}"
            if self.cloud_project_id:
                error_client = error_reporting.Client(project=self.cloud_project_id)
                error_client.report_exception()
        self.logger.log(self.Level.logger(level), text)
        if text:
            print(text)
        self._save_file(text, level)

    def info(self, text):
        self.verbose(text, self.Level.INFO)

    def warning(self, text):
        self.verbose(text, self.Level.WARNING)

    def debug(self, text):
        self.verbose(text, self.Level.DEBUG)

    def error(self, error):
        self.verbose(error, self.Level.ERROR)

    def setup_cloud_logging(self, project_id, credentials=None):
        self.cloud_project_id = project_id

        _resource = Resource(
            type="cloud_function",
            labels={
                "project_id": self.cloud_project_id,
                "function_name": self._PROJECT_TAG
            },
        )
        if credentials:
            client = google.cloud.logging.Client(project=self.cloud_project_id, credentials=credentials)
        else:
            client = google.cloud.logging.Client(project=self.cloud_project_id)
        setup_logging(self.handler)
        setup_logging(CloudLoggingHandler(client, resource=_resource))

    def _generate_log_name(self):
        _scripts = inspect.stack()
        _file_path = None
        for _script in _scripts:
            if _script.filename != __file__:
                _file_path = _script.filename
                break
        if _file_path:
            _filename_match = re.search(r"([^\\]+)\.py", _file_path)
            if _filename_match.lastindex > 0:
                self.log_name = _filename_match.group(_filename_match.lastindex)
        if not self.log_name:
            self.log_name = sys.argv[0]
        return self.log_name

    def _create_dirs(self):
        self.date = datetime.now().strftime(self._LOG_FILE_DATE_FORMAT)

        self.logs_dir = self._LOGS_FOLER
        self.log_dir = os.path.abspath(os.path.join(self.logs_dir, self.date))

        os.umask(0)
        os.makedirs(self.log_dir, exist_ok=True)

        self.log_file = os.path.join(self.log_dir, f"{self.log_name}.log")

        print(f"{self.log_name} logs can be found in {self.log_dir}")

    def _save_file(self, log, level):
        with open(self.log_file, "a+") as f:
            at = datetime.now().strftime(self._LOGS_DATETIME_FORMAT)
            f.write(f"{at[:-3]} {level}: {log}\n")
