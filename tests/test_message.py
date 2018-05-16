import struct
import unittest

from asyncirc.message import Message

class TestMessage(unittest.TestCase):

    handler = 'echo'
    header = b'header'
    payload = b'Hello World!'

    def test_00_encode(self):
        msg = bytes(Message(self.handler, self.header, self.payload))
        self.assertEqual(msg,
            struct.pack('!Q', len(self.handler.encode(Message.ENCODING))) + \
            struct.pack('!Q', len(self.header)) + \
            struct.pack('!Q', len(self.payload)) + \
            self.handler.encode(Message.ENCODING) + \
            self.header + \
            self.payload)

    def test_01_decode(self):
        msg = bytes(Message(self.handler, self.header, self.payload))
        msg = Message.decode(msg)
        self.assertEqual(msg.header_length, len(self.header))
        self.assertEqual(msg.header_length, len(self.header))
        self.assertEqual(msg.payload_length, len(self.payload))
        self.assertEqual(msg.handler, self.handler)
        self.assertEqual(msg.header, self.header)
        self.assertEqual(msg.payload, self.payload)

if __name__ == '__main__':
    unittest.main()
