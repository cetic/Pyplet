from typing import Protocol


class _ClosingMessageType:
    pass


closing_message = _ClosingMessageType()


class WebSocket(Protocol):
    closing_message = closing_message

    async def receive(self) -> str | bytes | _ClosingMessageType: ...

    async def send(self, message: str | bytes) -> None: ...
