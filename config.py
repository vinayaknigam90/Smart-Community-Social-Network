import os

class BaseConfig(object):
    SQLALCHEMY_DATABASE_URI = 'postgres://myawsuser:myawsuser@social-community.cznwlohjgx0g.us-west-2.rds.amazonaws.com:5432/socialCommunity'
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    BASIC_AUTH_FORCE = True
    SECRET_KEY = os.urandom(32)
    SQLALCHEMY_POOL_SIZE = 20
    SQLALCHEMY_MAX_OVERFLOW = 100
