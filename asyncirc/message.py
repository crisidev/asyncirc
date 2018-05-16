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

    @classmethod
    def decode(cls, msg: bytes):
        initialSize = struct.calcsize(cls.INITIAL_FORMAT)
        initial = cls.INITIAL._make(struct.unpack(cls.INITIAL_FORMAT,
            msg[:initialSize]))
        structFormat = cls.INITIAL_FORMAT + \
                cls.BODY_FORMAT.format(initial.handler_length,
                        initial.header_length, initial.payload_length)
        msgSize = initialSize + struct.calcsize(structFormat)
        msg = cls.MESSAGE._make(struct.unpack(structFormat, msg))
        return cls(msg.handler.decode(cls.ENCODING, errors='ignore'),
                msg.header, msg.payload)
