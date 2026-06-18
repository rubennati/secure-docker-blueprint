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

# --- SMTP / Email ---
_smtp_host = os.environ.get('SEAFILE_SMTP_HOST', '')
if _smtp_host:
    _use_tls = os.environ.get('SEAFILE_SMTP_USE_TLS', 'true').lower() == 'true'
    EMAIL_HOST = _smtp_host
    EMAIL_HOST_USER = os.environ.get('SEAFILE_SMTP_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('SEAFILE_SMTP_PASSWORD', '')
    EMAIL_PORT = int(os.environ.get('SEAFILE_SMTP_PORT', '587'))
    EMAIL_USE_TLS = _use_tls      # STARTTLS — port 587; mutually exclusive with EMAIL_USE_SSL
    EMAIL_USE_SSL = not _use_tls  # Implicit SSL — port 465; set SEAFILE_SMTP_USE_TLS=false to enable
    DEFAULT_FROM_EMAIL = os.environ.get('SEAFILE_SMTP_FROM', EMAIL_HOST_USER)
    SERVER_EMAIL = DEFAULT_FROM_EMAIL

# --- OnlyOffice Integration ---
ENABLE_ONLYOFFICE = True
ONLYOFFICE_APIJS_URL = os.environ.get('ONLYOFFICE_URL', '') + '/web-apps/apps/api/documents/api.js'
ONLYOFFICE_JWT_SECRET = os.environ.get('ONLYOFFICE_JWT_SECRET', '')
ONLYOFFICE_FILE_EXTENSION = ('doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'odt', 'fodt', 'odp', 'fodp', 'ods', 'fods', 'ppsx', 'pps', 'csv')
ONLYOFFICE_EDIT_FILE_EXTENSION = ('docx', 'pptx', 'xlsx', 'csv')
