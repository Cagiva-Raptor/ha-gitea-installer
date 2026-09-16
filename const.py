"""Constants for the Gitea Installer integration."""

DOMAIN = "gitea_installer"
NAME = "Gitea Installer"

CONF_GITEA_URL = "gitea_url"
CONF_OWNER = "owner"
CONF_REPO = "repo"
CONF_BRANCH = "branch"
CONF_TOKEN = "token"
CONF_UPDATE_INTERVAL_HOURS = "update_interval_hours"

DEFAULT_BRANCH = "main"
DEFAULT_UPDATE_INTERVAL_HOURS = 6

PLATFORMS = ["update", "button"]

# Services
SERVICE_UPDATE = "update"