import asyncio
import inspect
import traceback

from typing import Dict, Optional

from . import message

class BaseProtocol(asyncio.Protocol):

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(peername))
        self.transport = transport

    def data_received(self, data):
        try:
            for msg in message.Message.decode(data):
                try:
                    self.handle(msg)
                except Exception as err:
                    print('ERROR: %s handling message: %s' % (
                        self.__class__.__qualname__, err))
                    traceback.print_exc()
                    self.transport.close()
                    return
        except Exception as err:
            print('ERROR: %s while decoding message: %s: %s' % (
                self.__class__.__qualname__, err, data))
            traceback.print_exc()
            self.transport.close()
            return

    def handle(self, msg: message.Message):
        raise NotImplementedError('handle is not implemented')

class ClientHandler(BaseProtocol):

    def __init__(self, server):
        self.server = server

    def handle(self, msg: message.Message):
        handler = self.server.handlers.get(msg.handler, False)
        if handler is False:
            print('WARN: %s handler not found: %s' % (
                self.__class__.__qualname__, msg.handler))
            self.transport.write(bytes(message.NotFound))
            return
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
        client.transport.write(bytes(msg))

    def handle_terminate(self, client: ClientHandler, msg: message.Message):
        client.transport.close()

class Room(object): pass

class Server(BaseServer):

    def __init__(self, handler: Optional[ClientHandler] = ClientHandler,
            handlers: Dict[str, Handler] = {}):
        super().__init__(handler, handlers)
        self.rooms: Dict[str, List[Message]] = {}

    def handle_create_room(self, client: ClientHandler, msg: message.Message):
        room_name = msg.str_payload()
        if not room_name in self.rooms:
            self.rooms[room_name] = Room()

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
