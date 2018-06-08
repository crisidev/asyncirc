import asyncio
import inspect
import traceback

from functools import wraps
from typing import Dict, Optional

from .protocol import BaseProtocol
from . import message

class ClientHandler(BaseProtocol):

    def __init__(self, server):
        self.name = ''
        self.identified = False
        self.server = server

    def send(self, msg: message.Message):
        self.transport.write(bytes(msg))

    def disconnect(self):
        self.transport.close()

    def handle(self, msg: message.Message):
        handler = self.server.handlers.get(msg.handler, False)
        if handler is False:
            print('WARN: %s handler not found: %s' % (
                self.__class__.__qualname__, msg.handler))
            return self.send(message.NotFound)
        return handler(self, msg)

class Handler(object):

    def __init__(self, server):
        self.server = server

    def __call__(self, client: ClientHandler, msg: message.Message):
        raise NotImplementedError('handler is not implemented')

class BaseServer(object):

    def __init__(self, handler: Optional[ClientHandler] = ClientHandler,
            handlers: Dict[str, Handler] = {}):
        self.handler = handler
        built_ins = {
            name.replace('handle_', ''): method \
                    for name, method in inspect.getmembers(self,
                        predicate=inspect.ismethod) \
                    if name.startswith('handle_')}
        # Override built in handlers with supplied
        built_ins.update(handlers)
        self.handlers = built_ins

    def __call__(self):
        return self.handler(self)

    def handle_echo(self, client: ClientHandler, msg: message.Message):
        client.send(msg)

    def handle_terminate(self, client: ClientHandler, msg: message.Message):
        client.transport.close()

class Room(object):

    def __init__(self, name: str):
        self.name = name
        self._clients: Dict[str, ClientHandler] = {}

    def join(self, client: ClientHandler):
        self._clients[client.name] = client
        client.send(message.RoomJoined)

    def leave(self, client: ClientHandler):
        if client.name in self._clients:
            self._clients.pop(client.name)
            client.send(message.RoomLeft)

    def clients(self):
        return list(self._clients.keys())

    def broadcast(self, client: ClientHandler, msg: message.Message):
        for relay in self._clients.values():
            relay.send(message.Broadcast(self.name, client.name, msg.payload))

def IDd(f):
    @wraps(f)
    def wrapper(server, client, msg, *args, **kwds):
        if not client.identified:
            return client.send(message.ReqID)
        return f(server, client, msg, *args, **kwds)
    return wrapper

class Server(BaseServer):

    def __init__(self, handler: Optional[ClientHandler] = ClientHandler,
            handlers: Dict[str, Handler] = {}):
        super().__init__(handler, handlers)
        self._clients: Dict[str, List[Message]] = {}
        self._rooms: Dict[str, List[Message]] = {}

    def handle_identify(self, client: ClientHandler, msg: message.Message):
        client_name = msg.str_payload()
        if client_name in self._clients:
            return client.send(message.IDTaken)
        self._clients[client_name] = client
        client.name = client_name
        client.identified = True
        client.send(message.Identified)

    @IDd
    def handle_create_room(self, client: ClientHandler, msg: message.Message):
        room_name = msg.str_payload()
        if not room_name in self._rooms:
            self._rooms[room_name] = Room(room_name)
        return client.send(message.RoomCreated)

    @IDd
    def handle_list_rooms(self, client: ClientHandler, msg: message.Message):
        return client.send(message.RoomList(self._rooms.keys()))

    @IDd
    def handle_join_room(self, client: ClientHandler, msg: message.Message):
        room_name = msg.str_payload()
        if not room_name in self._rooms:
            return client.send(message.NoRoom)
        self._rooms[room_name].join(client)

    @IDd
    def handle_leave_room(self, client: ClientHandler, msg: message.Message):
        room_name = msg.str_payload()
        if not room_name in self._rooms:
            return
        self._rooms[room_name].leave(client)

    @IDd
    def handle_room_members(self, client: ClientHandler, msg: message.Message):
        room_name = msg.str_payload()
        if not room_name in self._rooms:
            return
        client.send(message.MemberList(self._rooms[room_name].clients()))

    @IDd
    def handle_msg_room(self, client: ClientHandler, msg: message.Message):
        room_name = msg.str_header()
        if not room_name in self._rooms:
            return client.send(message.NoRoom)
        self._rooms[room_name].broadcast(client, msg)
        client.send(message.RoomMsgd)

    @IDd
    def handle_msg_client(self, client: ClientHandler, msg: message.Message):
        client_name = msg.str_header()
        if not client_name in self._clients:
            return client.send(message.NoClient(client_name))
        self._clients[client_name].send(message.ClientMsg(client.name,
            msg.payload, unencoded=True))
        client.send(message.ClientMsgd)

def cli():
    loop = asyncio.get_event_loop()
    # Each client connection will create a new protocol instance
    coro = loop.create_server(EchoServerClientProtocol, '127.0.0.1', 8888)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    print('Serving on {}'.format(server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
