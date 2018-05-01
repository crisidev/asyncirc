import asyncio
import unittest

import asyncirc

class TestServerMethods(unittest.TestCase):

    def test_start(self):
        loop = asyncio.get_event_loop()
        # Each client connection will create a new protocol instance
        coro = loop.create_server(asyncirc.server.EchoServerClientProtocol,
                '127.0.0.1', 8888)
        server = loop.run_until_complete(coro)
        message = 'Hello World!'
        coro = loop.create_connection(lambda: \
                asyncirc.client.EchoClientProtocol(message, loop),
                                      '127.0.0.1', 8888)
        client, proto = loop.run_until_complete(coro)

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass

        client.close()
        # Close the server
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()

if __name__ == '__main__':
    unittest.main()
