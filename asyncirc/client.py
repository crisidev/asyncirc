import sys
import types
import asyncio
import inspect
import argparse
from functools import wraps, partial

from .server import Server
from . import message, const
from .protocol import BaseProtocol

async def must_id():
    print('Must identify first')

def IDd(f):
    @wraps(f)
    def wrapper(client, *args, **kwds):
        if not client.identified:
            return must_id()
        return f(client, *args, **kwds)
    return wrapper

class Client(BaseProtocol):

    NO_ID_NAME = 'Unidentified'

    def __init__(self, loop, handlers = {}):
        super().__init__()
        self.name = self.NO_ID_NAME
        self.identified = False
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
    def create_connection(cls, addr=const.ADDR, port=const.PORT,
            loop=asyncio.get_event_loop(), in_loop=False):
        self = cls(loop)
        coro = loop.create_connection(lambda: self, addr, port)
        if in_loop is False:
            self.sock, proto = loop.run_until_complete(coro)
        else:
            def connection_created(task):
                try:
                    self.sock, proto = task.result()
                except Exception as err:
                    return in_loop(err)
                in_loop(None)
            loop.create_task(coro).add_done_callback(connection_created)
        return self

    async def disconnect(self):
        if not self.disconnected.done():
            self.send(message.Terminate)
            await self.disconnected

    async def wait(self, *args):
        res = await asyncio.wait([self.disconnected] + list(args),
                loop=self.loop, return_when=asyncio.FIRST_COMPLETED)
        if self.disconnected.done():
            raise ConnectionResetError
        return res

    async def echo(self, payload):
        future = asyncio.Future(loop=self.loop)
        self.add_handler('handle_echo', lambda client, msg:
            future.set_result(msg.str_payload()))
        self.send(message.Echo(payload))
        await self.wait(future)
        return future.result()

    async def identify(self, name):
        future = asyncio.Future(loop=self.loop)
        self.add_handler('handle_identified', lambda client, msg:
            future.set_result(True))
        self.send(message.Identify(name))
        self.identified = True
        await self.wait(future)

    @IDd
    async def create_room(self, room):
        future = asyncio.Future(loop=self.loop)
        self.add_handler('handle_room_created', lambda client, msg:
            future.set_result(True))
        self.send(message.CreateRoom(room))
        await self.wait(future)

    @IDd
    async def list_rooms(self):
        future = asyncio.Future(loop=self.loop)
        self.add_handler('handle_room_list', lambda client, msg:
            future.set_result(msg.str_payload()))
        self.send(message.ListRooms)
        await self.wait(future)
        return future.result()

    @IDd
    async def join_room(self, room):
        future = asyncio.Future(loop=self.loop)
        self.add_handler('handle_room_joined', lambda client, msg:
            future.set_result(True))
        self.send(message.JoinRoom(room))
        await self.wait(future)

    @IDd
    async def leave_room(self, room):
        future = asyncio.Future(loop=self.loop)
        self.add_handler('handle_room_left', lambda client, msg:
            future.set_result(True))
        self.send(message.LeaveRoom(room))
        await self.wait(future)

    @IDd
    async def room_members(self, room):
        future = asyncio.Future(loop=self.loop)
        self.add_handler('handle_member_list', lambda client, msg:
            future.set_result(msg.str_payload()))
        self.send(message.RoomMembers(room))
        await self.wait(future)
        return future.result()

    @IDd
    async def msg_room(self, room, payload):
        future = asyncio.Future(loop=self.loop)
        none = asyncio.Future(loop=self.loop)
        self.add_handler('handle_room_msgd', lambda client, msg:
            future.set_result(True))
        self.add_handler('handle_no_room', lambda client, msg:
            none.set_result('no such room ' + room))
        self.send(message.MsgRoom(room, payload))
        res = await self.wait(future, none)
        if not future.done():
            future.cancel()
        if not none.done():
            none.cancel()
        else:
            return none.result()

    @IDd
    async def msg_client(self, client_name, payload):
        future = asyncio.Future(loop=self.loop)
        none = asyncio.Future(loop=self.loop)
        self.add_handler('handle_client_msgd', lambda client, msg:
            future.set_result(True))
        self.add_handler('handle_no_client', lambda client, msg:
            none.set_result('no such client ' + client_name))
        self.send(message.MsgClient(client_name, payload))
        res = await self.wait(future, none)
        if not future.done():
            future.cancel()
        if not none.done():
            none.cancel()
        else:
            return none.result()

class CLIClient(Client):

    def handle_broadcast(self, msg):
        print('(%s) %s: %s' % (message.Broadcast.room_name(msg),
            message.Broadcast.client_name(msg), msg.str_payload()))

    def handle_client_msg(self, msg):
        print('[PRIVATE] %s: %s' % (msg.str_header(), msg.str_payload()))

    def handle_req_id(self, msg):
        print('#identify command required first')

    def handle_id_taken(self, msg):
        print('That id has already been registered')

class ClientCLI(asyncio.Protocol):

    def __init__(self, loop=asyncio.get_event_loop()):
        super().__init__()
        self.loop = loop
        self.clients = {}
        self.rooms = {}
        self.active = None
        self.methods = {
            name.replace('handle_', ''): method \
                    for name, method in inspect.getmembers(self,
                        predicate=inspect.ismethod) \
                    if name.startswith('handle_')}
        self.helpers = {
            name.replace('helper_', ''): method \
                    for name, method in inspect.getmembers(self,
                        predicate=inspect.ismethod) \
                    if name.startswith('helper_')}

    def data_received(self, data):
        data = data.decode(encoding='utf-8', errors='ignore').split()
        if not data:
            return
        if data[0][0] == '/':
            self.handle_method(data[0][1:], *data[1:])
        elif data[0][0] == '#':
            self.on_active(data[0][1:], *data[1:])

    def handle_method(self, method_name, *args):
        method = self.methods.get(method_name, False)
        if method is False:
            return print('Unknown method')
        try:
            method(*args)
        except TypeError as err:
            print('An error has occurred:', err)
            helper = self.helpers.get(method_name, False)
            if not helper is False:
                helper()
        except Exception as err:
            print('An error has occurred:', err)

    def handle_connect(self, server_id, *args, addr=const.ADDR,
            port=const.PORT):
        def connected(err):
            if not err is None:
                return print('Error connecting to', server_id, err)
            if len(self.clients) is 0:
                self.active = server_id
            self.clients[server_id] = client
            print('Connected to', server_id)
        client = CLIClient.create_connection(addr=addr, port=port,
                loop=self.loop, in_loop=connected)

    def helper_connect(self):
        print('/connect server_id address port')

    def handle_disconnect(self, server_id):
        if server_id in self.clients:
            coro = self.clients[server_id].disconnect()
            self.loop.create_task(coro).add_done_callback(lambda task:
                    print('Disconnected from', server_id))
            del self.clients[server_id]
            if self.active == server_id:
                self.active = None if not len(self.clients) \
                        else list(self.clients.keys())[0]

    def helper_disconnect(self):
        print('/disconnect server_id')

    def handle_active(self, *args):
        if args:
            if not args[0] in self.clients:
                return print('No active connection to', args[0])
            self.active = args[0]
        print('Active connection:', self.active)

    def ackd(self, task, server_id='unknown server',
            method_name='unknown method', client=None):
        res = None
        try:
            res = task.result()
        except ConnectionResetError:
            print('Connection distrupted', end='. ')
            self.handle_disconnect(server_id)
        if res is None and client.identified:
            print(server_id, 'ACKd your', method_name)
        elif not res is None:
            print(res)

    def on_active(self, method_name, *args):
        if self.active is None:
            return print('No active connections')
        server_id = self.active
        client = self.clients[server_id]
        methods = {name: method for name, method in inspect.getmembers(client,
            predicate=inspect.ismethod)}
        method = methods.get(method_name, False)
        if method is False:
            return print('No such method', method_name, 'for', server_id)
        try:
            coro = method(*args)
            self.loop.create_task(coro).add_done_callback(partial(self.ackd,
                server_id=server_id, method_name=method_name, client=client))
        except TypeError as err:
            if 'positional arguments but' in str(err):
                num = int(str(err).split()[-7]) - 2
                try:
                    new_args = list(args[:num]) + [' '.join(args[num:])]
                    coro = method(*new_args)
                    self.loop.create_task(coro).add_done_callback(
                            partial(self.ackd, server_id=server_id,
                                method_name=method_name, client=client))
                except TypeError as err:
                    print('Incorrect usage:', err)
            else:
                print('Incorrect usage:', err)

def cli():
    parser = argparse.ArgumentParser(description='asyncirc client')
    parser.add_argument('-s', '--server', action='store_true', default=False,
            help='Start a server in the background')
    parser.add_argument('--addr', type=str, default=const.ADDR,
            help='Address to bind to')
    parser.add_argument('--port', type=int, default=const.PORT,
            help='Port to bind to')
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    if args.server:
        server = Server.start(addr=args.addr, port=args.port, loop=loop)
        print('Server hosted on port {}'.format(server.port))
    coro = loop.connect_read_pipe(lambda: ClientCLI(loop=loop), sys.stdin)
    loop.run_until_complete(coro)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    if args.server:
        server._sock.close()
        loop.run_until_complete(server._sock.wait_closed())
    loop.close()

if __name__ == '__main__':
    cli()
