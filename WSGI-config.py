import sys

project_home = '/home/purposeally/purpose_ally_bot'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# sys.path.append('/home/purposeally/.local/lib/python3.11/site-packages')

from webhook_server import flask_app as application