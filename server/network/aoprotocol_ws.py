import asyncio

from websockets import ConnectionClosed

from server.network.aoprotocol import AOProtocol


class AOProtocolWS(AOProtocol):
    """A websocket wrapper around AOProtocol."""

    class TransportWrapper:
        """A class to wrap asyncio's Transport class."""

        def __init__(self, websocket):
            self.ws = websocket

        def get_extra_info(self, key):
            """Get extra info about the client.
            Used for getting the remote address.

            :param key: requested key

            """
            remote_address = self.ws.remote_address
            if (remote_address[0] == "127.0.0.1"):
                # See if proxy
                try:
                    remote_address = (
                        self.ws.request_headers['X-Forwarded-For'], 0)
                except Exception:
                    pass
            info = {"peername": remote_address}
            return info[key]

        def write(self, message):
            """Write message to the socket.

            :param message: message in bytes

            """
            message = message.decode("utf-8")
            asyncio.ensure_future(self.ws_try_writing_message(message))

        def close(self):
            """Disconnect the client by force."""
            asyncio.ensure_future(self.ws.close())

        async def ws_try_writing_message(self, message):
            """
            Try writing the message if the client has not already closed
            the connection.
            """
            try:
                await self.ws.send(message)
            except ConnectionClosed:
                return

    def __init__(self, server, websocket):
        super().__init__(server)
        self.ws = websocket
        self.ws_connected = True

        self.ws_on_connect()

    def ws_on_connect(self):
        """Handle a new client connection."""
        self.connection_made(self.TransportWrapper(self.ws))

    async def ws_handle(self):
        try:
            data = await self.ws.recv()
            self.data_received(data)
        except Exception as exc:
            # Any event handled in data_received could raise any exception
            self.ws_connected = False
            self.connection_lost(exc)


def new_websocket_client(server):
    """
    Factory for creating a new WebSocket client.
    :param server: server object

    """

    async def func(websocket, _):
        client = AOProtocolWS(server, websocket)
        while client.ws_connected:
            await client.ws_handle()

    return func
