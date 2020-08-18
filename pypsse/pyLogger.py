import logging
import os


def getLogger(name, path, LoggerOptions):
    log_filename = os.path.join(path, name + '.log')

    if LoggerOptions['Clear old log file']:
        if os.path.exists(log_filename):
            os.remove(log_filename)

    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    logger = logging.getLogger(name)
    logger.setLevel(LoggerOptions['Logging Level'])
    if LoggerOptions['Display on screen']:
        handler1 = logging.StreamHandler()
        handler1.setFormatter(formatter)
        logger.addHandler(handler1)
    if LoggerOptions['Log to external file']:
        if not os.path.exists(path):
            os.mkdir(path)
        handler2 = logging.FileHandler(filename=log_filename)
        handler2.setFormatter(formatter)
        logger.addHandler(handler2)
    return logger


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


def getLoggerTag(options):
    return options["Project"]["Active Project"] + "__" + options["Project"]["Active Scenario"]
