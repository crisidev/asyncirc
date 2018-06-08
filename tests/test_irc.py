import types
import asyncio
import unittest

import asyncirc

class TestIRC(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        self.server = asyncirc.server.Server.start(addr='127.0.0.1', port=0,
                loop=self.loop)
        self.client = asyncirc.client.Client\
                .create_connection('127.0.0.1', port=self.server.port,
                        loop=self.loop)

    def tearDown(self):
        self.run_async(self.client.disconnect())
        self.client.sock.close()
        self.server._sock.close()
        self.loop.run_until_complete(self.server._sock.wait_closed())
        self.loop.close()

    def run_async(self, coro):
        return self.loop.run_until_complete(asyncio.wait_for(coro,
            1.0, loop=self.loop))

    def test_0020_server_process(self):
        return

    def test_0030_connect(self):
        self.run_async(self.client.echo('Hello World!'))

    def test_0031_identify(self):
        self.run_async(self.client.identify('test_client'))
        self.assertEqual(self.server._clients['test_client'].identified, True)

    def test_0040_create_room(self):
        self.run_async(self.client.identify('test_client'))
        self.run_async(self.client.create_room('test_room'))
        self.run_async(self.client.disconnect())
        self.assertIn('test_room', self.server._rooms)

    def test_0050_list_rooms(self):
        rooms = ['Room %d' % (i) for i in range(0, 10)]
        self.run_async(self.client.identify('test_client'))
        for room_name in rooms:
            self.run_async(self.client.create_room(room_name))
        room_list = self.run_async(self.client.list_rooms())
        self.assertEqual(room_list, '\n'.join(rooms))

    def test_0060_join_room(self):
        self.run_async(self.client.identify('test_client'))
        self.run_async(self.client.create_room('test_room'))
        self.run_async(self.client.join_room('test_room'))
        self.run_async(self.client.disconnect())
        self.assertIn('test_client', self.server._rooms['test_room']._clients)

    def test_0070_leave_room(self):
        self.run_async(self.client.identify('test_client'))
        self.run_async(self.client.create_room('test_room'))
        self.run_async(self.client.join_room('test_room'))
        self.run_async(self.client.leave_room('test_room'))

    def test_0080_room_members(self):
        members = ['client%d' % (i) for i in range(0, 10)]
        clients = []
        self.run_async(self.client.identify('test_client'))
        self.run_async(self.client.create_room('test_room'))
        self.run_async(self.client.join_room('test_room'))
        for client_name in members:
            client = asyncirc.client.Client.create_connection(
                    '127.0.0.1', port=self.server.port, loop=self.loop)
            self.run_async(client.identify(client_name))
            self.run_async(client.join_room('test_room'))
            clients.append(client)
        member_list = self.run_async(self.client.room_members('test_room'))
        for client in clients:
            self.run_async(client.disconnect())
        self.assertEqual(member_list , '\n'.join(['test_client'] + members))

    def test_0090_multiple_clients(self):
        clients = []
        for i in range(0, 10):
            client = asyncirc.client.Client.create_connection(
                    '127.0.0.1', port=self.server.port, loop=self.loop)
            self.run_async(client.identify('client%d' % (i)))
            clients.append(client)
        for client in clients:
            self.run_async(client.disconnect())

    def test_0100_msg_room(self):
        members = ['client%d' % (i) for i in range(0, 10)]
        self.run_async(self.client.identify('test_client'))
        self.run_async(self.client.create_room('test_room'))
        self.run_async(self.client.join_room('test_room'))
        future = asyncio.Future(loop=self.loop)
        self.client.add_handler('handle_broadcast', lambda client, msg:
            future.set_result((asyncirc.message.Broadcast.room_name(msg),
                asyncirc.message.Broadcast.client_name(msg),
                msg.str_payload())))
        self.run_async(self.client.msg_room('test_room', 'Hello World!'))
        self.loop.run_until_complete(asyncio.wait_for(future,
            1.0, loop=self.loop))
        room, name, payload = future.result()
        self.assertEqual('test_room', room)
        self.assertEqual('test_client', name)
        self.assertEqual('Hello World!', payload)

    def test_0110_join_multiple_rooms(self):
        rooms = ['Room %d' % (i) for i in range(0, 10)]
        self.run_async(self.client.identify('test_client'))
        for room_name in rooms:
            self.run_async(self.client.create_room(room_name))
            self.run_async(self.client.join_room(room_name))
        room_list = self.run_async(self.client.list_rooms())
        self.assertEqual(room_list, '\n'.join(rooms))

    def test_0120_msg_multiple_rooms(self):
        rooms = ['Room %d' % (i) for i in range(0, 10)]
        msgs = {}
        future = asyncio.Future(loop=self.loop)
        def handle_broadcast(client, msg):
            msgs[asyncirc.message.Broadcast.room_name(msg)] = msg.str_payload()
            if len(msgs) is len(rooms):
                future.set_result(True)
        self.client.add_handler('handle_broadcast', handle_broadcast)
        self.run_async(self.client.identify('test_client'))
        for room_name in rooms:
            self.run_async(self.client.create_room(room_name))
            self.run_async(self.client.join_room(room_name))
            self.run_async(self.client.msg_room(room_name, 'Hi ' + room_name))
        self.loop.run_until_complete(asyncio.wait_for(future,
            1.0, loop=self.loop))
        for room_name in rooms:
            self.assertIn(room_name, msgs)
            self.assertEqual(msgs[room_name], 'Hi ' + room_name)

    def test_0130_client_disconnect(self):
        self.run_async(self.client.disconnect())

    def test_0140_server_disconnect_client(self):
        self.run_async(self.client.identify('test_client'))
        self.server._clients['test_client'].disconnect()
        with self.assertRaises(ConnectionResetError):
            self.run_async(self.client.echo('echo!'))

    def test_0150_server_handles_client_crash(self):
        client = asyncirc.client.Client.create_connection(
                '127.0.0.1', port=self.server.port, loop=self.loop)
        self.run_async(client.identify('crash_client'))
        self.run_async(client.create_room('room'))
        self.run_async(client.join_room('room'))
        self.run_async(self.client.identify('test_client'))
        self.run_async(self.client.join_room('room'))
        client.sock.close()
        self.run_async(self.client.msg_client('crash_client', 'Bye!'))

    def test_0160_client_handles_server_crash(self):
        self.run_async(self.client.identify('test_client'))
        self.server._sock.close()
        self.loop.run_until_complete(self.server._sock.wait_closed())
        self.run_async(self.client.echo('echo!'))

    def test_0180_priave_messaging(self):
        self.run_async(self.client.identify('test_client'))
        future = asyncio.Future(loop=self.loop)
        self.client.add_handler('handle_client_msg', lambda client, msg:
            future.set_result((msg.str_header(), msg.str_payload())))
        self.run_async(self.client.msg_client('test_client', 'Hello World!'))
        self.loop.run_until_complete(asyncio.wait_for(future,
            1.0, loop=self.loop))
        name, payload = future.result()
        self.assertEqual('test_client', name)
        self.assertEqual('Hello World!', payload)

if __name__ == '__main__':
    unittest.main()
