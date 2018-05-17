import asyncio
import traceback

from .message import Message

class BaseProtocol(asyncio.Protocol):

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        self.transport = transport

    def data_received(self, data):
        if not len(data):
            return
        try:
            for msg in Message.decode(data):
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

    def handle(self, msg: Message):
        raise NotImplementedError('handle is not implemented')
