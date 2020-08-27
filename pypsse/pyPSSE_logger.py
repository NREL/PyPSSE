import logging
import os


def getLogger(name, path, LoggerOptions=None):

    if LoggerOptions['Clear old log file']:
        test = os.listdir(os.getcwd())
        for item in test:
            if item.endswith(".log"):
                try:
                    os.remove(item)
                except:
                    pass
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
        handler2 = logging.FileHandler(filename=os.path.join(path, name + '.log'))
        handler2.setFormatter(formatter)
        logger.addHandler(handler2)
    return logger
