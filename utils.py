def get_base_message(user_id: str, text: str):
    return {"users": [user_id], "message": {"text": text, "quick_replies": []}}


def get_quick_reply(content_type: str, payload: str, title: str):
    return {"content_type": content_type, "payload": payload, "title": title}
