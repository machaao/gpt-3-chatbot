import base64
from datetime import datetime
import json
import nlpcloud
import nltk
import requests
from nltk import word_tokenize
from requests.structures import CaseInsensitiveDict
from dotenv import load_dotenv
import os
import openai

ban_words = ["nigger", "negro", "nazi", "faggot", "murder", "suicide"]

# list of banned input words
c = 'UTF-8'
openai.api_key = os.environ.get("OPENAI_API_KEY", None)
model = os.environ.get("OPENAI_MODEL", "text-davinci-003")


def send(url, headers, payload=None):
    if payload:
        print("sending post to platform: " + str(payload))
        response = requests.request("POST", url, data=json.dumps(payload), headers=headers)
        print("response from the platform: " + str(response.text))
    else:
        response = requests.request("GET", url, headers=headers)

    return response


# don't change for sanity purposes
def get_details(api_token, base_url):
    _cache_ts_param = str(datetime.now().timestamp())
    e = "L3YxL2JvdHMvY29uZmlnP3Y9"
    check = base64.b64decode(e).decode(c)
    url = f"{base_url}{check}{_cache_ts_param}"
    headers = {
        "api_token": api_token,
        "Content-Type": "application/json",
    }

    response = send(url, headers)

    if response and response.status_code == 200:
        return response.json()
    else:
        return {}


def is_flagged(input):
    valid = True

    response = openai.Moderation.create(
        input=input
    )

    if response and response["results"]:
        output = response["results"][0]
        if output:
            valid = not output.flagged

    return valid


class BotLogic:
    def __init__(self):
        # Initializing Config Variables
        load_dotenv()

        self.api_token = os.environ.get("API_TOKEN")
        self.base_url = os.environ.get("BASE_URL", "https://ganglia.machaao.com")
        self.name = os.environ.get("NAME")
        self.limit = os.environ.get("LIMIT", 'True')
        self.prefix = self.read_prompt(self.name)

        # Bot config
        self.top_p = os.environ.get("TOP_P", 1.0)
        self.top_k = os.environ.get("TOP_K", 20)
        self.temp = os.environ.get("TEMPERATURE", 0.3)
        self.max_length = os.environ.get("MAX_LENGTH", 50)
        self.validate_bot_params()

    # noinspection DuplicatedCode
    def validate_bot_params(self):
        print("Setting up Bot server with parameters:")
        if self.top_p is not None and self.temp is not None:
            print("Temperature and Top_p parameters can't be used together. Using default value of top_p")
            self.top_p = 1.0

        if self.temp is not None:
            self.temp = float(self.temp)
            if self.temp < 0.0 or self.temp > 1.0:
                raise Exception("Temperature parameter must be between 0 and 1")
        else:
            self.temp = 0.8
        print(f"Temperature = {self.temp}")

        if self.top_p is not None:
            self.top_p = float(self.top_p)
            if self.top_p < 0.0 or self.top_p > 1.0:
                raise Exception("Top_p parameter must be between 0 and 1")
        else:
            self.top_p = 1.0
        print(f"Top_p = {self.top_p}")

        if self.top_k is not None:
            self.top_k = int(self.top_k)
            if self.top_k > 1000:
                raise Exception("Top_k parameter must be less than 1000")
        else:
            self.top_k = 50
        print(f"Top_k = {self.top_k}")

        if self.max_length is not None:
            self.max_length = int(self.max_length)
            if self.max_length > 1024:
                raise Exception("Max_length parameter must be less than 1024")
        else:
            self.max_length = 50
        print(f"Max_Length = {self.max_length}")

    @staticmethod
    def read_prompt(name):
        file_name = "./logic/prompt.txt"
        with open(file_name) as f:
            prompt = f.read()

        return prompt.replace("name]", f"{name}]")

    def get_recent(self, user_id: str):
        count = 5
        ## please don't edit the lines below
        e = "L3YxL2NvbnZlcnNhdGlvbnMvaGlzdG9yeS8="
        check = base64.b64decode(e).decode(c)
        url = f"{self.base_url}{check}{user_id}/{count}"

        headers = CaseInsensitiveDict()
        headers["api_token"] = self.api_token
        headers["Content-Type"] = "application/json"

        resp = requests.get(url, headers=headers)

        if resp.status_code == 200:
            return resp.json()

    @staticmethod
    def parse(data):
        msg_type = data.get('type')
        if msg_type == "outgoing":
            msg_data = json.loads(data['message'])
            msg_data_2 = json.loads(msg_data['message']['data']['message'])

            if msg_data_2 and msg_data_2.get('text', ''):
                text_data = msg_data_2['text']
            elif msg_data_2 and msg_data_2['attachment'] and msg_data_2['attachment'].get('payload', '') and \
                    msg_data_2['attachment']['payload'].get('text', ''):
                text_data = msg_data_2['attachment']['payload']['text']
            else:
                text_data = ""
        else:
            msg_data = json.loads(data['incoming'])
            if msg_data['message_data']['text']:
                text_data = msg_data['message_data']['text']
            else:
                text_data = ""

        return msg_type, text_data

    def core(self, req: str, label: str, user_id: str, client: str, sdk: str, action_type: str, api_token: str):
        print(
            "input text: " + req + ", label: " + label + ", user_id: " + user_id + ", client: " + client + ", sdk: " + sdk
            + ", action_type: " + action_type + ", api_token: " + api_token)

        bot = get_details(api_token, self.base_url)
        name = self.name
        _prompt = self.prefix

        if not bot:
            return False, "Oops, the chat bot doesn't exist or is not active at the moment"
        else:
            name = bot.get("displayName", name)

        if _prompt:
            _prompt = _prompt.replace("name]", f"{name}]")

        valid = True

        # intents = ["default", "balance"]

        recent_text_data = self.get_recent(user_id)
        recent_convo_length = len(recent_text_data)

        print(f"len of history: {recent_convo_length}")

        # text = word_tokenize(req)
        # tags = nltk.pos_tag(text)
        # print(f"tags: {tags}")

        history = _prompt + "\n"

        banned = any(ele in req for ele in ban_words)

        if banned or not is_flagged(req):
            print(f"banned input:" + str(req) + ", id: " + user_id)
            return False, "Oops, please refrain from such words"

        for text in recent_text_data[::-1]:
            msg_type, text_data = self.parse(text)

            if text_data:
                e_message = "Oops," in text_data and "connect@machaao.com" in text_data

                if msg_type is not None and not e_message:
                    # outgoing msg - bot msg
                    history += f"[{name}]: " + text_data
                else:
                    # incoming msg - user msg
                    history += "[user]: " + text_data

                history += "\n"

                if msg_type == "outgoing":
                    history += "###\n"

        history += f"[{name}]: "

        # Max input size = 2048 tokens
        try:
            reply = self.process_via_openai(model, history, user_id, name)
            print(history + reply)
            return valid, reply
        except Exception as e:
            print(f"error - {e}, for {user_id}")
            return False, "Oops, I am feeling a little overwhelmed with messages\nPlease message me later"

    def process_via_openai(self, model, prompt, user_id, bot_name):
        # todo - add a moderation check
        # "text-davinci-003"

        if openai.api_key:
            response = openai.Completion.create(model=model, prompt=prompt, temperature=self.temp,
                                                max_tokens=self.max_length, user=user_id)

            completion = ""

            if response and response.choices and len(response.choices) > 0:
                choice = response.choices[0]
                if choice and choice.text:
                    c = choice.text
                    bot_str = f"{bot_name}: "
                    completion = str.replace(c, bot_str, "")
        else:
            completion = "Oops, Please configure your Open AI key"

        return completion
