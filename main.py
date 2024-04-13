from pyrogram import Client
import asyncio
import os
import requests


URL = os.environ.get('URL', 'http://localhost:7777/message')


class Data:
    def __init__(self,id, text, is_photo):
        self.id = id
        self.text = text
        self.is_photo = is_photo


class SessionManager:
    def __init__(self):
        self.session = 'first'

    def update_session(self):
        if self.session == 'first':
            self.session = 'second'
        else:
            self.session = 'first'

    def get_session(self):
        session = self.session
        self.update_session()
        return "sessions/" + session


def get_credentials():
    api_id = int(os.environ['TG_API_ID']) if 'TG_API_ID' in os.environ else None
    api_hash = os.environ.get('TG_API_HASH')

    if (api_id is None or api_hash is None):
        raise Exception('Please set TG_API_ID and TG_API_HASH in environment variables')

    return api_id, api_hash


async def destroy(app):
    async for _ in app.get_dialogs():
        pass
    await app.stop()


def parse_message(message) -> dict:
    chat_id = message.chat.id
    text = message.text
    is_photo = False
    if (text is None):
        text = message.caption
        is_photo = True

    message_data = {
        "chat_id": chat_id,
        "text": text,
        "photo": is_photo
    }

    return message_data


def send_message(message_object):
    try:
        requests.post(URL, message_object)
    except Exception as e:
        print(e)


def client_manager():
    api_id, api_hash = get_credentials()
    session_manager = SessionManager()

    def init_listeners(app):
        @app.on_message()
        def _(_, message):
            message_object = parse_message(message)
            print(message_object)
            send_message(message_object)

    def get_client():
        session = session_manager.get_session()
        app = Client(session, api_id=api_id, api_hash=api_hash)
        init_listeners(app)
        return app

    return get_client


def ping(url):
    try:
        req = requests.get(url)
        if (req.status_code != 200):
            raise Exception('Wrong status code: ' + str(req.status_code))
    except Exception as e:
        print(e)
        exit(1)


async def main():
    prev = None
    get_client = client_manager()
    while True:
        app = get_client()
        await app.start()
        # print('Connected!')
        if (prev is not None):
            await destroy(prev)
        prev = app
        await asyncio.sleep(15)


ping(URL)
asyncio.run(main())
