from typing import Protocol, Union


class _ClosingMessageType:
    pass


closing_message = _ClosingMessageType()


class WebSocket(Protocol):
    closing_message = closing_message

    async def receive(self) -> Union[str, bytes, _ClosingMessageType]: ...

    async def send(self, message: Union[str, bytes]) -> None: ...
