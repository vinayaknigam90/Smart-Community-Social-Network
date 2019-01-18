class MyExceptions(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        rv['status_code'] = self.status_code
        return rv

class UserExists(MyExceptions):
    """called on user exists"""

class Unauthorized(MyExceptions):
    """called when user unauthorised"""

class CheckPostData(MyExceptions):
    """missing post data"""

class ImproperRequest (MyExceptions):
    """improper post data"""

class AccessGranted (MyExceptions):
    """access granted"""
