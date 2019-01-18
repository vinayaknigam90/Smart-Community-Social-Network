from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from config import BaseConfig
from flask_bootstrap import Bootstrap
from pymongo import MongoClient
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the Handler for logging data to a file
logger_handler = logging.FileHandler('sscn.log')
logger_handler.setLevel(logging.DEBUG)

# Create a Formatter for formatting the log messages
logger_formatter = logging.Formatter('%(funcName)s - %(name)s - %(levelname)s - %(message)s')

# Add the Formatter to the Handler
logger_handler.setFormatter(logger_formatter)

# Add the Handler to the Logger
logger.addHandler(logger_handler)

app.config.from_object(BaseConfig)
Bootstrap(app)
db = SQLAlchemy(app)


#connecting to MongoDB
client = MongoClient("mongodb://admin:admin@ds251845.mlab.com:51845/socialcommunity")
mongo = client['socialcommunity']
