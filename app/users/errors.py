from flask import render_template
from app.users import users

@users.app_errorhandler(404)
def page_not_found(e):
    return render_template('users/errors/404.html'), 404

@users.app_errorhandler(500)
def internal_server_error(e):
    return render_template('users/errors/500.html'), 500