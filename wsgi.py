"""
WSGI Application entry point for Gunicorn / Render / Heroku production deployments.
"""

from app import app as application

if __name__ == '__main__':
    application.run()
