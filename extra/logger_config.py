import sys
import logging

def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    FORMAT = "\n[%(asctime)s %(filename)s:%(levelname)s: Line %(lineno)s - %(funcName)20s() ] %(message)s\n"
    formatter = logging.Formatter(FORMAT, datefmt="%m/%d/%Y %I:%M:%S %p %Z")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.propagate = False
    return logger
