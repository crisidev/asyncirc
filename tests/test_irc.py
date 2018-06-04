import types
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
        self.loop.run_until_complete(
                asyncio.wait_for(new_client.got_broadcast, 1.0, loop=self.loop))
        room, name, payload = new_client.got_broadcast.result()
        self.assertEqual('test_room', room)
        self.assertEqual('test_client', name)
        self.assertEqual('Hello World!', payload)
        new_client_sock.close()

    def test_05_msg_client(self):
        class GotMsgClient(asyncirc.client.EchoClientProtocol):
            def handle_msg_client(nc, msg):
                nc.got_msg_client.set_result(
                        (msg.str_header(), msg.str_payload()))
        new_client = GotMsgClient(self.loop)
        new_client.got_msg_client = asyncio.Future(loop=self.loop)
        coro = self.loop.create_connection(lambda: new_client,
                '127.0.0.1', self.port)
        new_client_sock, proto = self.loop.run_until_complete(coro)
        new_client.send(asyncirc.message.Identify('test_client_recv'))
        self.client.send(asyncirc.message.Identify('test_client'),
                asyncirc.message.MsgClient('test_client_recv', 'Hello World!'))
        self.loop.run_until_complete(
                asyncio.wait_for(new_client.got_msg_client,
                    1.0, loop=self.loop))
        name, payload = new_client.got_msg_client.result()
        self.assertEqual('test_client', name)
        self.assertEqual('Hello World!', payload)
        new_client_sock.close()

    def test_06_list_rooms(self):
        class GotListRooms(asyncirc.client.EchoClientProtocol):
            def handle_room_list(nc, msg):
                nc.got_rooms.set_result(msg.str_payload())
        rooms = ['Room %d' % (i) for i in range(0, 10)]
        new_client = GotListRooms(self.loop)
        new_client.got_rooms = asyncio.Future(loop=self.loop)
        coro = self.loop.create_connection(lambda: new_client,
                '127.0.0.1', self.port)
        new_client_sock, proto = self.loop.run_until_complete(coro)
        new_client.send(asyncirc.message.Identify('test_client_recv'))
        self.client.send(asyncirc.message.Identify('test_client'))
        for room in rooms:
            created = asyncio.Future(loop=self.loop)
            def handle_room_created(client, msg):
                created.set_result(True)
            self.client.handle_room_created = types.MethodType(
                    handle_room_created, self.client)
            self.client.send(asyncirc.message.CreateRoom(room))
            self.loop.run_until_complete(asyncio.wait_for(created,
                1.0, loop=self.loop))
        new_client.send(asyncirc.message.ListRooms)
        self.loop.run_until_complete(asyncio.wait_for(new_client.got_rooms,
                    1.0, loop=self.loop))
        self.assertEqual(new_client.got_rooms.result(), '\n'.join(rooms))
        new_client_sock.close()

if __name__ == '__main__':
    unittest.main()
