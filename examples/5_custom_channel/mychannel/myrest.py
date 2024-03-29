import asyncio
import inspect
import json
import logging
from asyncio import Queue, CancelledError
from sanic import Blueprint, response
from sanic.request import Request
from sanic.response import HTTPResponse, ResponseStream
from typing import Text, Dict, Any, Optional, Callable, Awaitable, NoReturn, Union

import rasa.utils.endpoints
from rasa.core.channels.channel import (
    InputChannel,
    CollectingOutputChannel,
    UserMessage,
)


logger = logging.getLogger(__name__)


class RestInput(InputChannel):
    """A custom http input channel.

    This implementation is the basis for a custom implementation of a chat
    frontend. You can customize this to send messages to Rasa and
    retrieve responses from the assistant."""

    @classmethod
    def name(cls) -> Text:
        return "rest"

    @staticmethod
    async def on_message_wrapper(
        on_new_message: Callable[[UserMessage], Awaitable[Any]],
        text: Text,
        queue: Queue,
        sender_id: Text,
        input_channel: Text,
        metadata: Optional[Dict[Text, Any]],
    ) -> None:
        collector = QueueOutputChannel(queue)

        message = UserMessage(
            text, collector, sender_id, input_channel=input_channel, metadata=metadata
        )
        await on_new_message(message)

        await queue.put("DONE")

    async def _extract_sender(self, req: Request) -> Optional[Text]:
        return req.json.get("sender", None)

    # noinspection PyMethodMayBeStatic
    def _extract_message(self, req: Request) -> Optional[Text]:
        return req.json.get("message", None)

    def _extract_input_channel(self, req: Request) -> Text:
        return req.json.get("input_channel") or self.name()

    def get_metadata(self, request: Request) -> Optional[Dict[Text, Any]]:
        """Extracts additional information from the incoming request.

         Implementing this function is not required. However, it can be used to extract
         metadata from the request. The return value is passed on to the
         ``UserMessage`` object and stored in the conversation tracker.

        Args:
            request: incoming request with the message of the user

        Returns:
            Metadata which was extracted from the request.
        """
        return request.json.get("metadata", None)

    def stream_response(
        self,
        on_new_message: Callable[[UserMessage], Awaitable[None]],
        text: Text,
        sender_id: Text,
        input_channel: Text,
        metadata: Optional[Dict[Text, Any]],
    ) -> Callable[[Any], Awaitable[None]]:
        """Streams response to the client.

         If the stream option is enabled, this method will be called to
         stream the response to the client

        Args:
            on_new_message: sanic event
            text: message text
            sender_id: message sender_id
            input_channel: input channel name
            metadata: optional metadata sent with the message

        Returns:
            Sanic stream
        """

        async def stream(resp: Any) -> None:
            q: Queue = Queue()
            task = asyncio.ensure_future(
                self.on_message_wrapper(
                    on_new_message, text, q, sender_id, input_channel, metadata
                )
            )
            while True:
                result = await q.get()
                if result == "DONE":
                    break
                else:
                    await resp.write(json.dumps(result) + "\n")
            await task

        return stream

    def blueprint(
        self, on_new_message: Callable[[UserMessage], Awaitable[None]]
    ) -> Blueprint:
        """Groups the collection of endpoints used by rest channel."""
        module_type = inspect.getmodule(self)
        if module_type is not None:
            module_name = module_type.__name__
        else:
            module_name = None

        custom_webhook = Blueprint(
            "custom_webhook_{}".format(type(self).__name__),
            module_name,
        )

        # noinspection PyUnusedLocal
        @custom_webhook.route("/", methods=["GET"])
        async def health(request: Request) -> HTTPResponse:
            return response.json({"status": "ok"})

        @custom_webhook.route("/mywebhook", methods=["POST"])
        async def receive(request: Request) -> Union[ResponseStream, HTTPResponse]:
            sender_id = await self._extract_sender(request)
            text = self._extract_message(request)
            print("This is a custom webhook made by me.")
            # 保存 sender id 和 text
            should_use_stream = rasa.utils.endpoints.bool_arg(
                request, "stream", default=False
            )
            input_channel = self._extract_input_channel(request)
            # 似乎 input channel 在 app.ctx.input_channel 定义了？

            metadata = self.get_metadata(request)
            print(f">>> you could see the following information: sender_id {sender_id}, \n text {text}")
            print(f">>> the custom channel is used for custom front-end interaction, if you want to save")
            print(f"middleware information, please use custom trackerstore, see next example")

            # 以下的 on_new_message 在 channel.register 中定义了，为：
            #    async def handler(message: UserMessage) -> None:
            #    await app.ctx.agent.handle_message(message)


            if should_use_stream:
                return response.stream(
                    self.stream_response(
                        on_new_message, text, sender_id, input_channel, metadata
                    ),
                    content_type="text/event-stream",
                )
            else:
                collector = CollectingOutputChannel()
                # noinspection PyBroadException
                try:
                    await on_new_message(
                        UserMessage(
                            text,
                            collector,
                            sender_id,
                            input_channel=input_channel,
                            metadata=metadata,
                        )
                    )
                except CancelledError:
                    logger.error(
                        f"Message handling timed out for user message '{text}'.",
                        exc_info=True,
                    )
                except Exception:
                    logger.exception(
                        f"An exception occured while handling "
                        f"user message '{text}'."
                    )
                # 保存 collector
                
                return response.json(collector.messages)

        return custom_webhook


class QueueOutputChannel(CollectingOutputChannel):
    """Output channel that collects send messages in a list

    (doesn't send them anywhere, just collects them)."""

    # FIXME: this is breaking Liskov substitution principle
    # and would require some user-facing refactoring to address
    messages: Queue  # type: ignore[assignment]

    @classmethod
    def name(cls) -> Text:
        """Name of QueueOutputChannel."""
        return "queue"

    # noinspection PyMissingConstructor
    def __init__(self, message_queue: Optional[Queue] = None) -> None:
        super().__init__()
        self.messages = Queue() if not message_queue else message_queue

    def latest_output(self) -> NoReturn:
        raise NotImplementedError("A queue doesn't allow to peek at messages.")

    async def _persist_message(self, message: Dict[Text, Any]) -> None:
        await self.messages.put(message)
