import os
import sys
import logging
from datetime import datetime

class _OneLineWarningFormatter(logging.Formatter):
    """
    Custom log formatter that collapses multi-line log records onto a single
    line.

    Inherits from ``logging.Formatter`` and overrides ``format`` to replace
    newline characters with spaces and strip leading/trailing whitespace.
    """
    def format(
            self,
            record
    ) -> str:
        """
        Format a log record as a single line.

        Parameters
        ----------
        record : logging.LogRecord
            The log record to format.

        Returns
        -------
        str
            Formatted log string with newlines replaced by spaces.
        """
        return super().format(record).replace("\n", " ").strip()

class Logger:
    """
    Package-level logger factory for the ``ece866`` package.

    Provides static methods to initialize and retrieve named loggers with
    consistent formatting, file output, console output, and warning capture.

    Attributes
    ----------
    created : str
        Timestamp of logger creation, formatted as ``'YYYY-MM-DD-HH-MM-SS'``.
    """
    def __init__(self):
        # Immediately store the creation timestamp
        self.created = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

    def init(
            self,
            write_file : bool=True,
            log_dir : str=None,
            log_name: str=None,
            log_level : int=logging.INFO,
            stamp_file : bool=True
    ):
        """
        Initialize the ``ece866`` package logger with file and console handlers.

        Sets up log formatting, warning capture via ``logging.captureWarnings``,
        and a global exception hook to log uncaught exceptions at ``CRITICAL``
        level. If the log file already exists, it is removed before
        initialization.

        Parameters
        ----------
        write_file : bool, optional
            Flag indicating whether to direct log to output file. Default is
            ``True``.
        log_dir : str, optional
            The directory that the output log file will be written to. If
            ``None``, the current working directory is used.
        log_name : str, optional
            The name of the output log file. If ``None``, the log file name is a
            timestamped log file named ``ece866-YYYY-MM-DD-HH-MM-SS.log``.
        log_level : int, optional
            Logging level for the logger. Should be one of the standard
            :mod:`logging` module constants (e.g. ``logging.DEBUG``,
            ``logging.INFO``, ``logging.WARNING``). Default is ``logging.INFO``.
        stamp_file : bool, optional
            If ``True``, append a timestamp of the format
            ``YYYY-MM-DD-HH-MM-SS`` to the end of the log file name. Default is
            ``True``.

        Notes
        -----
        ``KeyboardInterrupt`` is excluded from the exception hook and is handled
        by the default system handler so that ``Ctrl+C`` exits silently.

        Both the ``ece866`` logger and the ``py.warnings`` logger (used by
        ``logging.captureWarnings``) are attached to the same file and console
        handlers.
        """
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            package_logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
        sys.excepthook = handle_exception

        if write_file:
            if log_dir is None:
                log_dir = os.getcwd()
            if log_name is None:
                log_name = f"ece866"
                # Always stamp the file if using the default log name
                stamp_file = True
            else:
                # Remove extension if provided
                log_name = log_name.replace(".log", "")
            if stamp_file:
                log_name = f"{log_name}-{self.created}"
            write_file = os.path.join(log_dir, f"{log_name}.log")

            log_dir = os.path.dirname(write_file)
            os.makedirs(log_dir, exist_ok=True)

            if os.path.isfile(write_file):
                os.remove(write_file)

        formatter = _OneLineWarningFormatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")

        logging.captureWarnings(True)

        package_logger = logging.getLogger("ece866")
        package_logger.setLevel(log_level)
        warnings_logger = logging.getLogger("py.warnings")

        if write_file:
            file_handler = logging.FileHandler(write_file)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)

            package_logger.addHandler(file_handler)
            warnings_logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)

        package_logger.addHandler(console_handler)
        warnings_logger.addHandler(console_handler)

    @staticmethod
    def get(
            logger_name : str=None
    ) -> logging.Logger:
        """
        Retrieve a logger by name.

        Parameters
        ----------
        logger_name : str, optional
            Name of the logger to retrieve. Defaults to ``"ece866"`` if
            ``None``.

        Returns
        -------
        logging.Logger
            The named logger instance.
        """
        if logger_name is None:
            logger_name = "ece866"
        return logging.getLogger(logger_name)
