from dotenv import load_dotenv
from telethon import TelegramClient, events, utils
import asyncio
import os
import threading
import websocket
import datetime
import ssl
import json

load_dotenv()

RESTART_INTERVAL = 5
SESSION_INTERVAL = 15
CACHE_TTL = 10
CACHE_MAXSIZE = 300
PING_INTERVAL = 30
WS_URL = os.environ.get('WS_URL', 'wss://localhost:7777')
API_ID = int(os.environ['TG_API_ID']) or 0
API_HASH = os.environ.get('TG_API_HASH') or ''
API_KEY = os.environ.get('API_KEY') or ''

if (API_ID == 0 or API_HASH == '' or API_KEY == ''):
    msg = 'Please set environment variables'
    raise Exception(msg)

with open('config.json', 'r') as f:
    config = json.load(f)

ignored_channels = config["ignored_channels"]

connection_open_event = threading.Event()

def convert_to_ms(timestamp):
    return int(timestamp * 1000)


def parse_chat_id(number):
    number = abs(number)
    if number >= 1000000000000:
        number %= 1000000000000
    return number


def parse_message(event) -> dict | None:
    chat_id = event.chat.id
    message_id = event.id
    date = event.date
    try:
        message = event.text or event.caption
    except:
        message = None

    if message is None:
        return None

    current_time = datetime.datetime.now().timestamp()
    message_time = date.timestamp()
    difference_time = current_time - message_time

    result = {
        "channelId": parse_chat_id(chat_id),
        "message": message,
        "messageId": message_id,
        "messageTime": convert_to_ms(message_time),
        "currentTime": convert_to_ms(current_time),
        "differenceTime": convert_to_ms(difference_time)
    }

    return result


async def ws_send_message(socket, message_object):
    try:
        socket.send(json.dumps(message_object))
    except Exception as e:
        print(f'Websocket send error: {e}')
        os._exit(1)


def on_error(_, error):
    print(error)
    os._exit(1)


def on_message(_, message):
    print(message)


def on_close(_, code, message):
    if code != None:
        print('Connection closed with code: ' + str(code), message)
    raise Exception('Websocket connection closed!')


def on_open(_):
    connection_open_event.set()
    print('Websocket connection established!')


def run_ws(ws):
    ws.run_forever(ping_interval=PING_INTERVAL, sslopt={"cert_reqs": ssl.CERT_NONE})


async def get_ws():
    header = { 'Authorization': 'Bearer ' + API_KEY }
    ws = websocket.WebSocketApp(WS_URL, header,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open,
        on_message=on_message,
    )
    threading.Thread(target=run_ws, args=(ws,)).start()
    while not connection_open_event.is_set():
        print("Waiting for connection...")
        connection_open_event.wait(timeout=1)
    return ws


async def main():
    socket = await get_ws()
    session = 'sessions/telethon'
    client = TelegramClient(session, API_ID, API_HASH)
    await client.start()
    print('Client started!')

    @client.on(events.NewMessage())
    async def _(event):
        # print(event)
        message_object = parse_message(event)
        if (message_object is None):
            return
        channel_id = message_object["channelId"]
        if (channel_id in ignored_channels):
            return
        asyncio.create_task(ws_send_message(socket, message_object))
        print(message_object)

    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting...")
        os._exit(0)
    except Exception as e:
        print(f'An error occurred: {e}')
        os._exit(1)
