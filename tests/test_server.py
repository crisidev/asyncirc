import asyncio
import unittest

import asyncirc

class TestServerMethods(unittest.TestCase):

    def test_start(self):
        server = asyncirc.server.Server()
        loop = asyncio.new_event_loop()
        # Each client connection will create a new protocol instance
        coro = loop.create_server(server, '127.0.0.1', 8888)
        server = loop.run_until_complete(coro)
        coro = loop.create_connection(lambda: \
                asyncirc.client.EchoClientProtocol(loop,
                    [asyncirc.message.Echo('Hello World!'),
                    asyncirc.message.Terminate]),
                '127.0.0.1', 8888)
        client, proto = loop.run_until_complete(coro)

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass

        client.close()
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()

if __name__ == '__main__':
    unittest.main()
