import asyncio
from typing import List

from .message import Message

class EchoClientProtocol(asyncio.Protocol):
    def __init__(self, loop, messages: List[Message] = []):
        self.loop = loop
        self.messages = messages

    def connection_made(self, transport):
        for message in self.messages:
            msg = bytes(message)
            transport.write(msg)

    def data_received(self, data):
        if not len(data):
            return
        for msg in Message.decode(data):
            print('Data received: {}: {!r}'.format(msg.handler, msg.payload))

    def connection_lost(self, exc):
        print('The server closed the connection')
        print('Stop the event loop')
        self.loop.stop()

def cli():
    loop = asyncio.get_event_loop()
    message = 'Hello World!'
    coro = loop.create_connection(lambda: EchoClientProtocol(loop),
                                  '127.0.0.1', 8888)
    loop.run_until_complete(coro)
    loop.run_forever()
    loop.close()
