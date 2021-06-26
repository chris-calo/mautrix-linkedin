from typing import List, Optional, TYPE_CHECKING, Union

from mautrix.bridge import BaseMatrixHandler
from mautrix.errors import MatrixError
from mautrix.types import (
    EncryptedEvent,
    Event,
    EventID,
    EventType,
    MessageEvent,
    MessageType,
    PresenceEvent,
    PresenceEventContent,
    PresenceState,
    ReactionEvent,
    ReactionEventContent,
    ReceiptEvent,
    RedactionEvent,
    RelationType,
    RoomID,
    SingleReceiptEventContent,
    StateEvent,
    TextMessageEventContent,
    TypingEvent,
    UserID,
)

from . import portal as po, puppet as pu, user as u

if TYPE_CHECKING:
    from .__main__ import LinkedInBridge


class MatrixHandler(BaseMatrixHandler):
    def __init__(self, bridge: "LinkedInBridge") -> None:
        prefix, suffix = (
            bridge.config["bridge.username_template"].format(userid=":").split(":")
        )
        homeserver = bridge.config["homeserver.domain"]
        self.user_id_prefix = f"@{prefix}"
        self.user_id_suffix = f"{suffix}:{homeserver}"
        super().__init__(bridge=bridge)

    async def send_welcome_message(self, room_id: RoomID, inviter: "u.User") -> None:
        await super().send_welcome_message(room_id, inviter)
        if not inviter.notice_room:
            inviter.notice_room = room_id
            await inviter.save()
            await self.az.intent.send_notice(
                room_id,
                "This room has been marked as your LinkedIn Messages bridge notice "
                "room.",
            )

    def filter_matrix_event(self, evt: Event) -> bool:
        if isinstance(evt, (ReceiptEvent, TypingEvent, PresenceEvent)):
            return False
        elif not isinstance(
            evt,
            (ReactionEvent, RedactionEvent, MessageEvent, StateEvent, EncryptedEvent),
        ):
            return True
        return (
            evt.sender == self.az.bot_mxid
            or pu.Puppet.get_id_from_mxid(evt.sender) is not None
        )

    async def handle_presence(
        self,
        user_id: UserID,
        info: PresenceEventContent,
    ) -> None:
        print(f"user ({user_id}) is present {info}")
        if not self.config["bridge.presence"]:
            return

    @staticmethod
    async def handle_typing(room_id: RoomID, typing: List[UserID]) -> None:
        print(f"room: {room_id}: typing {typing}")
        portal: Optional[po.Portal] = await po.Portal.get_by_mxid(room_id)
        if not portal:
            return
        # https://www.linkedin.com/voyager/api/messaging/conversations?action=typing
        # {"conversationId":"2-ZmRhMGVmZDYtNDVjYS00Y2Y2LWE3ZTYtNmFkM2FlMGMxMDA1XzAxMg=="}

    async def handle_ephemeral_event(
        self,
        evt: Union[ReceiptEvent, PresenceEvent, TypingEvent],
    ):
        if evt.type == EventType.PRESENCE:
            await self.handle_presence(evt.sender, evt.content)
        elif evt.type == EventType.TYPING:
            await self.handle_typing(evt.room_id, evt.content.user_ids)
        elif evt.type == EventType.RECEIPT:
            await self.handle_receipt(evt)
