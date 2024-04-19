from pyrogram import Client, enums
import asyncio
import os
import aiohttp
import websockets
import json


HTTP_URL = os.environ.get('HTTP_URL', 'http://localhost:7777/message')
WS_URL = os.environ.get('WS_URL', 'ws://localhost:7777')


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


async def ping(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as res:
            if (res.status != 200):
                raise Exception('Wrong status code: ' + str(res.status))


def parse_message(message) -> dict | None:
    chat_id = message.chat.id
    message_id = message.id
    date = message.date
    chat_type = message.chat.type
    text = message.text or message.caption
    if (text is None):
        return None
    if (chat_type == enums.ChatType.CHANNEL):
        chat_type = 'channel'
    elif (chat_type == enums.ChatType.SUPERGROUP):
        chat_type = 'supergroup'
    elif (chat_type == enums.ChatType.GROUP):
        chat_type = 'group'
    else:
        return None

    message_data = {
        "id": chat_id,
        "text": text,
        "messageId": message_id,
        "date": date.timestamp(),
        "type": chat_type
    }

    return message_data


async def http_send_message(message_object):
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(HTTP_URL, json=message_object)
    except Exception as e:
        print(f'HTTP send error: {e}')
        exit(1)


async def ws_send_message(socket, message_object):
    try:
        await socket.send(json.dumps(message_object))
    except Exception as e:
        print(f'Websocket send error: {e}')
        exit(1)


async def keep_alive(socket):
    ping_interval = 30
    while True:
        try:
            await socket.ping()
            # print("Ping sended!")
            await asyncio.sleep(ping_interval)
        except Exception as e:
            raise Exception(f"Error: {e}")


async def get_ws():
    socket = await websockets.connect(WS_URL)
    asyncio.create_task(keep_alive(socket))
    return socket


class ClientManager:
    def __init__(self, socket):
        self.session_manager = SessionManager()
        api_id, api_hash = get_credentials()
        self.api_id = api_id
        self.api_hash = api_hash
        self.socket = socket
        self.prev = None

    def init_listeners(self, app):
        @app.on_message()
        async def _(_, message):
            message_object = parse_message(message)
            if (message_object is None):
                return
            asyncio.create_task(ws_send_message(self.socket, message_object))
            # print(message_object)

    async def get_client(self):
        session = self.session_manager.get_session()
        api_id, api_hash = self.api_id, self.api_hash
        app = Client(session, api_id=api_id, api_hash=api_hash)
        self.init_listeners(app)
        if (self.prev is not None):
            await destroy(self.prev)
        self.prev = app
        return app


async def main():
    socket = await get_ws()
    client_manager = ClientManager(socket)
    while True:
        app = await client_manager.get_client()
        await app.start()
        await asyncio.sleep(15)


asyncio.run(main())
