from functools import wraps
from flask import abort,flash
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            flash('You dont have a access to this page')
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function