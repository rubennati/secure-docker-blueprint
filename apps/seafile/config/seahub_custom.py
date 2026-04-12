# =============================================
# Custom Seahub Settings (managed by blueprint)
# =============================================
# These settings are appended to seahub_settings.py
# by entrypoint.sh on container start.
#
# Secrets are injected via environment variables
# (exported by entrypoint.sh from Docker Secrets).

import os

# --- Metadata Server ---
ENABLE_METADATA_MANAGEMENT = True
METADATA_SERVER_URL = 'http://seafile-md-server:8084'

# --- Thumbnail Server ---
ENABLE_VIDEO_THUMBNAIL = True

# --- OnlyOffice Integration ---
ENABLE_ONLYOFFICE = True
ONLYOFFICE_APIJS_URL = os.environ.get('ONLYOFFICE_URL', '') + '/web-apps/apps/api/documents/api.js'
ONLYOFFICE_JWT_SECRET = os.environ.get('ONLYOFFICE_JWT_SECRET', '')
ONLYOFFICE_FILE_EXTENSION = ('doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'odt', 'fodt', 'odp', 'fodp', 'ods', 'fods', 'ppsx', 'pps', 'csv')
ONLYOFFICE_EDIT_FILE_EXTENSION = ('docx', 'pptx', 'xlsx', 'csv')
