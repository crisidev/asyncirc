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
        self.client = asyncirc.client.EchoClientProtocol\
                .create_connection('127.0.0.1', port=self.port, loop=self.loop)

    def tearDown(self):
        self.client.sock.close()
        self.server_sock.close()
        self.loop.run_until_complete(self.server_sock.wait_closed())
        self.loop.close()

    def test_0020_server_process(self):
        return

    def test_0030_connect(self):
        self.client.send(asyncirc.message.Echo('Hello World!'),
                asyncirc.message.Terminate)
        self.loop.run_until_complete(self.client.disconnected)

    def test_0031_identify(self):
        self.client.send(asyncirc.message.Identify('test_client'),
                asyncirc.message.Terminate)
        self.loop.run_until_complete(self.client.disconnected)
        self.assertEqual(self.server._clients['test_client'].identified, True)

    def test_0040_create_room(self):
        self.client.send(asyncirc.message.Identify('test_client'),
                asyncirc.message.CreateRoom('test_room'),
                asyncirc.message.Terminate)
        self.loop.run_until_complete(self.client.disconnected)
        self.assertIn('test_room', self.server._rooms)

    def test_0060_join_room(self):
        self.client.send(asyncirc.message.Identify('test_client'),
                asyncirc.message.CreateRoom('test_room'),
                asyncirc.message.JoinRoom('test_room'),
                asyncirc.message.Terminate)
        self.loop.run_until_complete(self.client.disconnected)
        self.assertIn('test_client', self.server._rooms['test_room']._clients)

    def test_0100_msg_room(self):
        future = asyncio.Future(loop=self.loop)
        self.client.add_handler('handle_broadcast', lambda client, msg:
            future.set_result((asyncirc.message.Broadcast.room_name(msg),
                asyncirc.message.Broadcast.client_name(msg),
                msg.str_payload())))
        self.client.send(asyncirc.message.Identify('test_client'),
                asyncirc.message.CreateRoom('test_room'),
                asyncirc.message.JoinRoom('test_room'),
                asyncirc.message.MsgRoom('test_room', 'Hello World!'),
                asyncirc.message.Terminate)
        self.loop.run_until_complete(asyncio.wait_for(future,
            1.0, loop=self.loop))
        room, name, payload = future.result()
        self.assertEqual('test_room', room)
        self.assertEqual('test_client', name)
        self.assertEqual('Hello World!', payload)

    def test_05_msg_client(self):
        future = asyncio.Future(loop=self.loop)
        self.client.add_handler('handle_msg_client', lambda client, msg:
            future.set_result((msg.str_header(), msg.str_payload())))
        self.client.send(asyncirc.message.Identify('test_client'),
                asyncirc.message.MsgClient('test_client', 'Hello World!'),
                asyncirc.message.Terminate)
        self.loop.run_until_complete(asyncio.wait_for(future,
            1.0, loop=self.loop))
        name, payload = future.result()
        self.assertEqual('test_client', name)
        self.assertEqual('Hello World!', payload)

    def test_06_list_rooms(self):
        rooms = ['Room %d' % (i) for i in range(0, 10)]
        self.client.send(asyncirc.message.Identify('test_client'))
        for room in rooms:
            created = asyncio.Future(loop=self.loop)
            self.client.add_handler('handle_room_created', lambda client, msg:
                created.set_result(True))
            self.client.send(asyncirc.message.CreateRoom(room))
            self.loop.run_until_complete(asyncio.wait_for(created,
                1.0, loop=self.loop))
        future = asyncio.Future(loop=self.loop)
        self.client.add_handler('handle_room_list', lambda client, msg:
            future.set_result(msg.str_payload()))
        self.client.send(asyncirc.message.ListRooms,
                asyncirc.message.Terminate)
        self.loop.run_until_complete(asyncio.wait_for(future,
            1.0, loop=self.loop))
        self.assertEqual(future.result(), '\n'.join(rooms))

    def test_07_leave_room(self):
        future = asyncio.Future(loop=self.loop)
        self.client.add_handler('handle_room_left', lambda client, msg:
            future.set_result(True))
        self.client.send(asyncirc.message.Identify('test_client'),
                asyncirc.message.CreateRoom('room'),
                asyncirc.message.JoinRoom('room'),
                asyncirc.message.LeaveRoom('room'),
                asyncirc.message.Terminate)
        self.loop.run_until_complete(asyncio.wait_for(future,
            1.0, loop=self.loop))

if __name__ == '__main__':
    unittest.main()
