from pypsse.models import LogSettings
import logging
import os


def getLogger(name, path, LoggerOptions:LogSettings=None):

    if LoggerOptions.clear_old_log_file:
        test = os.listdir(os.getcwd())
        for item in test:
            if item.endswith(".log"):
                try:
                    os.remove(item)
                except:
                    pass
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    logger = logging.getLogger(name)
    logger.setLevel(LoggerOptions.logging_level)
    if LoggerOptions.display_on_screen:
        handler1 = logging.StreamHandler()
        handler1.setFormatter(formatter)
        logger.addHandler(handler1)
    if LoggerOptions.log_to_external_file:
        if not os.path.exists(path):
            os.mkdir(path)
        handler2 = logging.FileHandler(filename=os.path.join(path, name + '.log'))
        handler2.setFormatter(formatter)
        logger.addHandler(handler2)
    return logger
