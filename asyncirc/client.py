import types
import asyncio
import inspect
from functools import wraps

from . import message
from .protocol import BaseProtocol

def ensure_connection(f):
    @wraps(f)
    def wrapper(client, *args, **kwds):
        if not client.connected():
            raise ConnectionResetError()
        return f(client, *args, **kwds)
    return wrapper

class Client(BaseProtocol):

    def __init__(self, loop, handlers = {}):
        super().__init__()
        self.name = 'Unidentified'
        self.loop = loop
        self.disconnected = asyncio.Future(loop=self.loop)

    def connection_lost(self, exc):
        self.disconnected.set_result(True)

    def connected(self):
        return not self.disconnected.done()

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

    def handle(self, msg: message.Message):
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

    @classmethod
    def create_connection(cls, addr, port=13180,
            loop=asyncio.get_event_loop()):
        self = cls(loop)
        coro = loop.create_connection(lambda: self, addr, port)
        self.sock, proto = loop.run_until_complete(coro)
        return self

    async def disconnect(self):
        if not self.disconnected.done():
            self.send(message.Terminate)
            await self.disconnected

    async def wait(self, future):
        res = await asyncio.wait([self.disconnected, future], loop=self.loop,
                return_when=asyncio.FIRST_COMPLETED)
        if self.disconnected.done():
            raise ConnectionResetError
        return res

    @ensure_connection
    async def echo(self, payload):
        future = asyncio.Future(loop=self.loop)
        self.add_handler('handle_echo', lambda client, msg:
            future.set_result(msg.str_payload()))
        self.send(message.Echo(payload))
        await self.wait(future)
        return future.result()

    @ensure_connection
    async def identify(self, name):
        future = asyncio.Future(loop=self.loop)
        self.add_handler('handle_identified', lambda client, msg:
            future.set_result(True))
        self.send(message.Identify(name))
        await self.wait(future)

    @ensure_connection
    async def create_room(self, room):
        future = asyncio.Future(loop=self.loop)
        self.add_handler('handle_room_created', lambda client, msg:
            future.set_result(True))
        self.send(message.CreateRoom(room))
        await self.wait(future)

    @ensure_connection
    async def list_rooms(self):
        future = asyncio.Future(loop=self.loop)
        self.add_handler('handle_room_list', lambda client, msg:
            future.set_result(msg.str_payload()))
        self.send(message.ListRooms)
        await self.wait(future)
        return future.result()

    @ensure_connection
    async def join_room(self, room):
        future = asyncio.Future(loop=self.loop)
        self.add_handler('handle_room_joined', lambda client, msg:
            future.set_result(True))
        self.send(message.JoinRoom(room))
        await self.wait(future)

    @ensure_connection
    async def leave_room(self, room):
        future = asyncio.Future(loop=self.loop)
        self.add_handler('handle_room_left', lambda client, msg:
            future.set_result(True))
        self.send(message.LeaveRoom(room))
        await self.wait(future)

    @ensure_connection
    async def room_members(self, room):
        future = asyncio.Future(loop=self.loop)
        self.add_handler('handle_member_list', lambda client, msg:
            future.set_result(msg.str_payload()))
        self.send(message.RoomMembers(room))
        await self.wait(future)
        return future.result()

    @ensure_connection
    async def msg_room(self, room, payload):
        future = asyncio.Future(loop=self.loop)
        self.add_handler('handle_room_msgd', lambda client, msg:
            future.set_result(True))
        self.send(message.MsgRoom(room, payload))
        await self.wait(future)

    @ensure_connection
    async def msg_client(self, client, payload):
        future = asyncio.Future(loop=self.loop)
        self.add_handler('handle_client_msgd', lambda client, msg:
            future.set_result(True))
        self.send(message.MsgClient(client, payload))
        await self.wait(future)

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
