import asyncio
import unittest

import asyncirc

class TestIRC(unittest.TestCase):

    def setUp(self):
        self.server = asyncirc.server.Server()
        self.loop = asyncio.new_event_loop()
        coro = self.loop.create_server(self.server, '127.0.0.1', 0)
        self.server_sock = self.loop.run_until_complete(coro)
        self.port = self.server_sock.sockets[0].getsockname()[1]
        self.client = asyncirc.client.EchoClientProtocol(self.loop)
        coro = self.loop.create_connection(lambda: self.client,
                '127.0.0.1', self.port)
        self.client_sock, proto = self.loop.run_until_complete(coro)

    def runOps(self):
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass

    def tearDown(self):
        self.client_sock.close()
        self.server_sock.close()
        self.loop.run_until_complete(self.server_sock.wait_closed())
        self.loop.close()

    def test_connect(self):
        self.client.send(asyncirc.message.Echo('Hello World!'),
                asyncirc.message.Terminate)
        self.runOps()

    def test_create_room(self):
        self.client.send(asyncirc.message.CreateRoom('test_room'),
                asyncirc.message.Terminate)
        self.runOps()
        self.assertIn('test_room', self.server.rooms)

if __name__ == '__main__':
    unittest.main()
