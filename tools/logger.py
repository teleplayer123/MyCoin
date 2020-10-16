import logging
import os

class Logger:

    def __init__(self, logger_name, filename):
        if not os.path.exists("logs"):
            os.mkdir("logs")
        fh = logging.FileHandler(os.path.join("logs", filename))
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        fh.setFormatter(formatter)
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(fh)

    def get_logger(self):
        return self.logger