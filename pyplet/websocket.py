"""WebSocket protocol primitives for Pyplet.

This module defines the WebSocket typing protocol shared by client and server,
including a sentinel value used to signal that the connection has closed.

Docstring style: Google.
"""

from typing import Protocol, Union


class _ClosingMessageType:
    """Opaque sentinel type used to signal WebSocket closure.

    Instances of this type are never created by user code. Instead, the module
    exposes a single ``closing_message`` object which can be used for identity
    checks (``is``) to detect when a WebSocket is closed.
    """

    pass


closing_message = _ClosingMessageType()


class WebSocket(Protocol):
    """Structural protocol for Pyplet WebSocket objects.

    Implementations must provide ``receive`` and ``send`` asynchronous methods.
    The attribute ``closing_message`` is available to compare received values
    and detect a closed connection.
    """

    closing_message = closing_message

    async def receive(self) -> Union[str, bytes, _ClosingMessageType]:
        """Receive the next message from the peer.

        Returns:
            Either a text string, a byte payload, or the ``closing_message``
            sentinel when the connection is closed.
        """

        ...

    async def send(self, message: Union[str, bytes]) -> None:
        """Send a message to the peer.

        Args:
            message: Text or bytes to send.
        """

        ...
