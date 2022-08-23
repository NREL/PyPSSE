import logging
import os

def getReportLogger(LoggerTag, path, LoggerOptions):
    log_filename = os.path.join(path, "{}__reports.log".format(LoggerTag))
    if os.path.exists(log_filename):
        os.remove(log_filename)

    logger = logging.getLogger("Reports")
    logger.handlers = []

    handler = logging.FileHandler(filename=log_filename)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if LoggerOptions['Display on screen']:
        handler1 = logging.StreamHandler()
        handler1.setFormatter(formatter)
        logger.addHandler(handler1)
    return logger

