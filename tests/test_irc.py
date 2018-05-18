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

    def tearDown(self):
        self.client_sock.close()
        self.server_sock.close()
        self.loop.run_until_complete(self.server_sock.wait_closed())
        self.loop.close()

    def test_00_connect(self):
        self.client.send(asyncirc.message.Echo('Hello World!'),
                asyncirc.message.Terminate)
        self.loop.run_until_complete(self.client.disconnected)

    def test_01_identify(self):
        self.client.send(asyncirc.message.Identify('test_client'),
                asyncirc.message.Terminate)
        self.loop.run_until_complete(self.client.disconnected)
        self.assertEqual(self.server._clients['test_client'].identified, True)

    def test_02_create_room(self):
        self.client.send(asyncirc.message.Identify('test_client'),
                asyncirc.message.CreateRoom('test_room'),
                asyncirc.message.Terminate)
        self.loop.run_until_complete(self.client.disconnected)
        self.assertIn('test_room', self.server._rooms)

    def test_03_join_room(self):
        self.client.send(asyncirc.message.Identify('test_client'),
                asyncirc.message.CreateRoom('test_room'),
                asyncirc.message.JoinRoom('test_room'),
                asyncirc.message.Terminate)
        self.loop.run_until_complete(self.client.disconnected)
        self.assertIn('test_client', self.server._rooms['test_room']._clients)

    def test_04_msg_room(self):
        class GotRoomMsg(asyncirc.client.EchoClientProtocol):
            def handle_broadcast(nc, msg):
                nc.got_broadcast.set_result(
                        (asyncirc.message.Broadcast.room_name(msg),
                        asyncirc.message.Broadcast.client_name(msg),
                        msg.str_payload()))
        new_client = GotRoomMsg(self.loop)
        new_client.got_broadcast = asyncio.Future(loop=self.loop)
        coro = self.loop.create_connection(lambda: new_client,
                '127.0.0.1', self.port)
        new_client_sock, proto = self.loop.run_until_complete(coro)
        new_client.send(asyncirc.message.Identify('test_client_recv'),
                asyncirc.message.CreateRoom('test_room'),
                asyncirc.message.JoinRoom('test_room'))
        self.client.send(asyncirc.message.Identify('test_client'),
                asyncirc.message.CreateRoom('test_room'),
                asyncirc.message.JoinRoom('test_room'),
                asyncirc.message.MsgRoom('test_room', 'Hello World!'))
        self.loop.run_until_complete(new_client.got_broadcast)
        room, name, payload = new_client.got_broadcast.result()
        self.assertEqual('test_room', room)
        self.assertEqual('test_client', name)
        self.assertEqual('Hello World!', payload)
        new_client_sock.close()

if __name__ == '__main__':
    unittest.main()
