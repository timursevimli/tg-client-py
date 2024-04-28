from dotenv import load_dotenv
from pyrogram import Client, enums
import asyncio
import os
import aiohttp
import websockets
import json
from cachetools import TTLCache

load_dotenv()


PING_INTERVAL = 30
HTTP_URL = os.environ.get('HTTP_URL', 'http://localhost:7777/message')
WS_URL = os.environ.get('WS_URL', 'ws://localhost:7777')
API_ID = int(os.environ['TG_API_ID']) if 'TG_API_ID' in os.environ else None
API_HASH = os.environ.get('TG_API_HASH')
if (API_ID is None or API_HASH is None):
    msg = 'Please set TG_API_ID and TG_API_HASH in environment variables'
    raise Exception(msg)


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


async def destroy(app):
    await asyncio.sleep(1)
    async for _ in app.get_dialogs():
        pass
    await app.stop()


async def ping(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as res:
            if (res.status != 200):
                raise Exception('Wrong status code: ' + str(res.status))


def parse_message(message_data) -> dict | None:
    chat_id = message_data.chat.id
    message_id = message_data.id
    date = message_data.date
    chat_type = message_data.chat.type
    message = message_data.text or message_data.caption

    if (message is None):
        return None

    if (chat_type == enums.ChatType.CHANNEL):
        chat_type = 'channel'
    elif (chat_type == enums.ChatType.SUPERGROUP):
        chat_type = 'supergroup'
    elif (chat_type == enums.ChatType.GROUP):
        chat_type = 'group'
    else:
        return None

    result = {
        "channelId": chat_id,
        "message": message,
        "messageId": message_id,
        "date": date.timestamp(),
        "type": chat_type
    }

    return result


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
    while True:
        try:
            await socket.ping()
            # print("Ping sended!")
            await asyncio.sleep(PING_INTERVAL)
        except Exception as e:
            raise Exception(f"Error: {e}")


async def get_ws():
    socket = await websockets.connect(WS_URL)
    asyncio.create_task(keep_alive(socket))
    return socket


def generate_key(channel_id, message_id): 
    return str(channel_id) + str(message_id)


class ClientManager:
    def __init__(self, socket):
        self.session_manager = SessionManager()
        self.socket = socket
        self.prev = None
        self.cache = TTLCache(maxsize=100, ttl=1)

    def init_listeners(self, app):
        @app.on_message()
        async def _(_, message):
            message_object = parse_message(message)
            if (message_object is None):
                return
            channel_id = message_object["channelId"]
            message_id = message_object["messageId"]
            key = generate_key(channel_id, message_id)
            if (self.cache.get(key) is not None):
                # print("cache hit!!!")
                return;
            self.cache[key] = True
            asyncio.create_task(ws_send_message(self.socket, message_object))
            print(message_object)

    async def get_client(self):
        session = self.session_manager.get_session()
        app = Client(session, api_id=API_ID, api_hash=API_HASH)
        self.init_listeners(app)
        await app.start()
        if (self.prev is not None):
            # print("reconnecting!")
            asyncio.create_task(destroy(self.prev))
        self.prev = app
        return app


async def main():
    while True:
        try:
            socket = await get_ws()
            print("Connected to the server!")
            client_manager = ClientManager(socket)
            while True:
                await client_manager.get_client()
                await asyncio.sleep(15)
        except Exception as e:
            print(f'An error ocurred: {e}')
            await asyncio.sleep(5)
            continue

asyncio.run(main())
