# libs
import json
import sys
import traceback
import jwt
import requests
from dotenv import load_dotenv

# core
from flask import Flask, request
from machaao import Machaao
from logic.bot_logic import BotLogic

# helpers
from utils import get_base_message, get_quick_reply

# constants
from config import api_token, open_api_key, base_url, dashbot_key, dashbot_url, port

app = Flask(__name__)

load_dotenv()

params = [api_token, base_url, open_api_key]

# error = not name or not base_url or not api_token or not nlp_token
error = False

if not dashbot_key:
    print("Dashbot key not present in env. Disabling dashbot logging")

if not error:
    machaao = Machaao(api_token, base_url)
else:
    print(error)

# api_token = bot_params["API_TOKEN"]
# base_url = bot_params["BASE_URL"]

logic = BotLogic()


# noinspection PyProtectedMember
def exception_handler(exception):
    caller = sys._getframe(1).f_code.co_name
    print(f"{caller} function failed")
    if hasattr(exception, "message"):
        print(exception.message)
    else:
        print("Unexpected error: ", sys.exc_info()[0])


def extract_sender(req):
    try:
        return req.headers["user_id"]
    except Exception as e:
        exception_handler(e)


def send_reply(valid: bool, text: str, user_id: str, client: str, sdk: float):
    try:

        msg = get_base_message(user_id, text)

        if valid and msg and msg["message"]:
            msg["message"]["quick_replies"] = [
                get_quick_reply("text", "👍", "👍"),
                get_quick_reply("text", "❤️", "❤️"),
                get_quick_reply("text", "😊", "😊"),
                get_quick_reply("text", "😎", "😎"),
                get_quick_reply("text", "😡", "😡"),
            ]

        if (
            msg
            and msg["message"]
            and msg["message"]["quick_replies"]
            and client != "web"
        ):
            msg["message"]["quick_replies"].append(
                get_quick_reply("text", "balance", "Balance")
            )

        machaao.send_message(payload=msg)

        if dashbot_key:
            send_to_dashbot(text=text, user_id=user_id, msg_type="send")

    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        exception_handler(e)


def extract_message(req):
    """
    Decrypts the request body, and parses the incoming message
    """
    decoded_jwt = None
    body = req.json
    if body and body["raw"]:
        decoded_jwt = jwt.decode(body["raw"], api_token, algorithms=["HS512"])
    text = decoded_jwt["sub"]
    if type(text) == str:
        text = json.loads(decoded_jwt["sub"])

    sdk = text["messaging"][0]["version"]
    sdk = sdk.replace("v", "")
    client = text["messaging"][0]["client"]

    try:
        action_type = text["messaging"][0]["message_data"]["action_type"]
    except Exception as e:
        action_type = "text"
        traceback.print_exc(file=sys.stdout)
        exception_handler(e)

    return (
        text["messaging"][0]["message_data"]["text"],
        text["messaging"][0]["message_data"]["label"],
        client,
        sdk,
        action_type,
    )


def send_to_dashbot(text, user_id, msg_type):
    try:
        payload = {
            "text": text,
            "userId": user_id,
        }

        if msg_type == "recv":
            url = dashbot_url.format(type="incoming", apiKey=dashbot_key)
        else:
            url = dashbot_url.format(type="outgoing", apiKey=dashbot_key)

        header = {"Content-Type": "application/json"}
        requests.post(url=url, data=json.dumps(payload), headers=header)

    except Exception as e:
        exception_handler(e)


@app.route("/", methods=["GET"])
def root():
    return "ok"


@app.route("/webhooks/machaao/incoming", methods=["GET", "POST"])
def receive():
    return process_response(request)


def process_response(request):
    _api_token = request.headers["api_token"]
    sender_id = extract_sender(request)
    recv_text, label, client, sdk, action_type = extract_message(request)

    if dashbot_key:
        send_to_dashbot(text=recv_text, user_id=sender_id, msg_type="recv")

    valid_request, reply = logic.core(
        recv_text, label, sender_id, client, sdk, action_type, _api_token
    )

    send_reply(valid_request, reply, sender_id, client, eval(sdk))

    return "ok"


if __name__ == "__main__":
    app.run(debug=True, port=port)
