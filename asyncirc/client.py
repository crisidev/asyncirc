import types
import asyncio
import inspect

from .message import Message
from .protocol import BaseProtocol

class EchoClientProtocol(BaseProtocol):

    def __init__(self, loop, handlers = {}):
        super().__init__()
        self.name = 'Unidentified'
        self.loop = loop
        self.disconnected = asyncio.Future(loop=self.loop)

    def connection_lost(self, exc):
        self.disconnected.set_result(True)

    def send(self, *args):
        built_ins = {
            name.replace('send_', ''): method \
                    for name, method in inspect.getmembers(self,
                        predicate=inspect.ismethod) \
                    if name.startswith('send_')}
        for msg in args:
            handler = built_ins.get(msg.handler, False)
            if not handler is False:
                handler(msg)
            self.transport.write(bytes(msg))

    def send_identify(self, msg):
        self.name = msg.str_payload()

    def add_handler(self, name, handler):
        setattr(self, name, types.MethodType(handler, self))

    def handle(self, msg: Message):
        built_ins = {
            name.replace('handle_', ''): method \
                    for name, method in inspect.getmembers(self,
                        predicate=inspect.ismethod) \
                    if name.startswith('handle_')}
        handler = built_ins.get(msg.handler, False)
        if handler is False:
            print('WARN: %s %s handler not found: %s' % (
                self.__class__.__qualname__, self.name, msg.handler))
            return
        return handler(msg)

def cli():
    loop = asyncio.get_event_loop()
    message = 'Hello World!'
    coro = loop.create_connection(lambda: EchoClientProtocol(loop),
                                  '127.0.0.1', 8888)
    loop.run_until_complete(coro)
    loop.run_forever()
    loop.close()

if __name__ == '__main__':
    cli()
