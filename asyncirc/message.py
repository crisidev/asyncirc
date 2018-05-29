import collections
import struct

class Message(object):

    # Network Byte Order (big-endian)
    # Handler - String of length 50
    ENCODING = 'utf-8'
    INITIAL_FORMAT = '!QQQ'
    BODY_FORMAT = '{}s{}s{}s'
    INITIAL_FIELDS = 'handler_length header_length payload_length'
    BODY_FIELDS = 'handler header payload'
    INITIAL = collections.namedtuple('Initial', INITIAL_FIELDS)
    MESSAGE = collections.namedtuple('Message', INITIAL_FIELDS + ' ' + \
            BODY_FIELDS)

    def __init__(self, handler: str, header: bytes, payload: bytes):
        self.handler = handler
        self.header = header
        self.payload = payload
        self.handler_length = len(self.handler.encode(self.ENCODING))
        self.header_length = len(header)
        self.payload_length = len(payload)

    def __bytes__(self) -> bytes:
        return struct.pack(self.INITIAL_FORMAT + \
                self.BODY_FORMAT.format(self.handler_length, self.header_length,
                    self.payload_length),
                self.handler_length, self.header_length, self.payload_length,
                self.handler.encode(self.ENCODING), self.header, self.payload)

    def str_payload(self) -> str:
        return self.payload.decode(self.ENCODING, errors='ignore')

    def str_header(self) -> str:
        return self.header.decode(self.ENCODING, errors='ignore')

    @classmethod
    def decode(cls, msg: bytes):
        while len(msg):
            initialSize = struct.calcsize(cls.INITIAL_FORMAT)
            initial = cls.INITIAL._make(struct.unpack(cls.INITIAL_FORMAT,
                msg[:initialSize]))
            structFormat = cls.INITIAL_FORMAT + \
                    cls.BODY_FORMAT.format(initial.handler_length,
                            initial.header_length, initial.payload_length)
            msgSize = struct.calcsize(structFormat)
            message = cls.MESSAGE._make(struct.unpack(structFormat,
                msg[:msgSize]))
            yield cls(message.handler.decode(cls.ENCODING, errors='ignore'),
                    message.header, message.payload)
            msg = msg[msgSize:]

class Echo(Message):

    def __init__(self, text):
        super().__init__('echo', b'', text.encode(self.ENCODING))

NotFound = Message('not_found', b'', b'Handler Not Found')
Terminate = Message('terminate', b'', b'')

# IRC Messages
ReqID = Message('req_id', b'', b'')

class Identify(Message):

    def __init__(self, client_name):
        super().__init__('identify', b'', client_name.encode(self.ENCODING))

class IDLock(Message):

    def __init__(self, password):
        super().__init__('id_lock', b'', password.encode(self.ENCODING))

Prove = Message('prove', b'', b'')
IDTaken = Message('id_taken', b'', b'')

class IDProve(Message):

    def __init__(self, password):
        super().__init__('id_prove', b'', password.encode(self.ENCODING))

class CreateRoom(Message):

    def __init__(self, room_name):
        super().__init__('create_room', b'', room_name.encode(self.ENCODING))

class JoinRoom(Message):

    def __init__(self, room_name):
        super().__init__('join_room', b'', room_name.encode(self.ENCODING))

class MsgRoom(Message):

    def __init__(self, room_name, payload):
        super().__init__('msg_room', room_name.encode(self.ENCODING),
                payload.encode(self.ENCODING))

class Broadcast(Message):

    def __init__(self, room_name, client_name, payload):
        super().__init__('broadcast', ':'.join([room_name, client_name])\
                .encode(self.ENCODING), payload)

    def client_name(self):
        return self.str_header().split(':')[1] \
                if ':' in self.str_header() else 'Anonymous'

    def room_name(self):
        return self.str_header().split(':')[0] \
                if ':' in self.str_header() else self.str_header()

class NoRoom(Message):

    def __init__(self, room_name):
        super().__init__('no_room', b'', room_name.encode(self.ENCODING))

class MsgClient(Message):

    def __init__(self, client_name, payload, unencoded=False):
        super().__init__('msg_client', client_name.encode(self.ENCODING),
                payload if unencoded else payload.encode(self.ENCODING))

class NoClient(Message):

    def __init__(self, client_name):
        super().__init__('no_client', b'', client_name.encode(self.ENCODING))
