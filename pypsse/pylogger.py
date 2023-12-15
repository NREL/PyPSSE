import logging
import os


def get_report_logger(logger_tag, path, logger_options):
    log_filename = os.path.join(path, f"{logger_tag}__reports.log")
    if os.path.exists(log_filename):
        os.remove(log_filename)

    logger = logging.getLogger("Reports")
    logger.handlers = []

    handler = logging.FileHandler(filename=log_filename)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if logger_options["Display on screen"]:
        handler1 = logging.StreamHandler()
        handler1.setFormatter(formatter)
        logger.addHandler(handler1)
    return logger
