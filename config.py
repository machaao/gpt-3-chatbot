# libs
import os

api_token = os.environ.get("API_TOKEN")
base_url = os.environ.get("BASE_URL", "https://ganglia-dev.machaao.com")
name = os.environ.get("NAME", "")
open_api_key = os.environ.get("OPEN_API_KEY", "")
dashbot_key = os.environ.get("DASHBOT_KEY", "")
port = os.environ.get("PORT", 5000)

dashbot_url = "https://tracker.dashbot.io/track?platform=webchat&v=11.1.0-rest&type={type}&apiKey={apiKey}"
error_message = (
    "invalid configuration detected, check your .env file for missing parameters"
)
