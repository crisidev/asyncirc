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

    def test_00_connect(self):
        self.client.send(asyncirc.message.Echo('Hello World!'),
                asyncirc.message.Terminate)
        self.runOps()

    def test_01_identify(self):
        self.client.send(asyncirc.message.Identify('test_client'),
                asyncirc.message.Terminate)
        self.runOps()
        self.assertEqual(self.server._clients['test_client'].identified, True)

    def test_02_create_room(self):
        self.client.send(asyncirc.message.Identify('test_client'),
                asyncirc.message.CreateRoom('test_room'),
                asyncirc.message.Terminate)
        self.runOps()
        self.assertIn('test_room', self.server._rooms)

    def test_03_join_room(self):
        self.client.send(asyncirc.message.Identify('test_client'),
                asyncirc.message.CreateRoom('test_room'),
                asyncirc.message.JoinRoom('test_room'),
                asyncirc.message.Terminate)
        self.runOps()
        self.assertIn('test_client', self.server._rooms['test_room']._clients)

    def test_04_msg_room(self):
        check_room = 'Not received'
        check_name = 'Not received'
        check_payload = 'Not received'
        class GotRoomMsg(asyncirc.client.EchoClientProtocol):
            def handle_broadcast(new_client, msg):
                check_room = asyncirc.message.Broadcast.room_name(msg)
                check_name = asyncirc.message.Broadcast.client_name(msg)
                check_payload = msg.str_payload()
        new_client = GotRoomMsg(self.loop)
        coro = self.loop.create_connection(lambda: new_client,
                '127.0.0.1', self.port)
        new_client_sock, proto = self.loop.run_until_complete(coro)
        new_client.send(asyncirc.message.Identify('test_client_recv'),
                asyncirc.message.CreateRoom('test_room'),
                asyncirc.message.JoinRoom('test_room'))
        self.client.send(asyncirc.message.Identify('test_client'),
                asyncirc.message.CreateRoom('test_room'),
                asyncirc.message.JoinRoom('test_room'),
                asyncirc.message.MsgRoom('test_room', 'Hello World!'),
                asyncirc.message.Terminate)
        self.runOps()
        new_client_sock.close()
        self.assertEqual('test_room', check_room)
        self.assertEqual('test_client', check_name)
        self.assertEqual('Hello World!', check_payload)

if __name__ == '__main__':
    unittest.main()
