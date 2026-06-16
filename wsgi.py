"""
Production WSGI application entry point for SwasthAI API.
Use with: gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.app import app

if __name__ == "__main__":
    app.run()
