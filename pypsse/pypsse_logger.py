import logging
import os

from pypsse.models import LogSettings


def get_logger(name, path, logger_options: LogSettings = None):
    if logger_options.clear_old_log_file:
        test = os.listdir(os.getcwd())
        for item in test:
            if item.endswith(".log"):
                try:
                    os.remove(item)
                except:
                    logging.warning("Unable to delete the old log file")
    formatter = logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(module)s - %(message)s")

    logger = logging.getLogger(name)
    logger.setLevel(logger_options.logging_level)
    if logger_options.display_on_screen:
        handler1 = logging.StreamHandler()
        handler1.setFormatter(formatter)
        logger.addHandler(handler1)
    if logger_options.log_to_external_file:
        if not os.path.exists(path):
            os.mkdir(path)
        handler2 = logging.FileHandler(filename=os.path.join(path, name + ".log"))
        handler2.setFormatter(formatter)
        logger.addHandler(handler2)
    return logger
