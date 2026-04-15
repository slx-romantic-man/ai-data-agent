"""
Conversation Service - Chat history persistence and search.
Uses database for storage instead of JSON files.
Also manages conversation state for multi-turn dialogue.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date
from decimal import Decimal
import asyncio
import json

from sqlalchemy import select, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.access.database.connection import get_db
from app.access.database.models import Conversation as ConversationDB, Message as MessageDB
from app.models.chat import ConversationContext, ConversationState
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _serialize_data(data: Any) -> Any:
    """Recursively serialize data to JSON-compatible format."""
    if data is None:
        return None
    if isinstance(data, (datetime, date)):
        return data.isoformat()
    if isinstance(data, Decimal):
        return float(data)
    if isinstance(data, dict):
        return {k: _serialize_data(v) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return [_serialize_data(item) for item in data]
    return data


class Conversation:
    """Conversation model for storage."""

    def __init__(
        self,
        id: str,
        user_id: str,
        title: str = "",
        messages: List[Dict] = None,
        created_at: datetime = None,
        updated_at: datetime = None
    ):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.messages = messages or []
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "messages": self.messages,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        return cls(
            id=data.get("id", ""),
            user_id=data.get("user_id", ""),
            title=data.get("title", ""),
            messages=data.get("messages", []),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now()
        )


class SearchResult:
    """Search result model."""

    def __init__(
        self,
        conversation_id: str,
        user_id: str,
        username: str,
        title: str,
        matched_message: str,
        timestamp: datetime
    ):
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.username = username
        self.title = title
        self.matched_message = matched_message
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "username": self.username,
            "title": self.title,
            "matched_message": self.matched_message,
            "timestamp": self.timestamp.isoformat()
        }


class ConversationService:
    """
    Service for managing chat history and conversation state.
    Storage: MySQL/PostgreSQL database
    State management: In-memory (can be replaced with Redis)
    """

    def __init__(self):
        self._db = None
        # In-memory storage for conversation state
        self._contexts: Dict[str, ConversationContext] = {}
        self._ttl_minutes = 30

    def _get_context_key(self, user_id: str, session_id: str) -> str:
        """Generate context key."""
        return f"{user_id}:{session_id}"

    def save_context(
        self,
        user_id: str,
        session_id: str,
        context: ConversationContext
    ) -> None:
        """
        Save conversation context for multi-turn dialogue.

        Args:
            user_id: User ID
            session_id: Session ID
            context: Conversation context to save
        """
        key = self._get_context_key(user_id, session_id)
        self._contexts[key] = context
        logger.info(f"Saved conversation context for {key}, state: {context.state}")

    def get_context(
        self,
        user_id: str,
        session_id: str
    ) -> Optional[ConversationContext]:
        """
        Get conversation context.

        Args:
            user_id: User ID
            session_id: Session ID

        Returns:
            Conversation context if exists and not expired, None otherwise
        """
        key = self._get_context_key(user_id, session_id)
        context = self._contexts.get(key)

        if context is None:
            return None

        # Check if expired
        if datetime.now() - context.created_at > timedelta(minutes=self._ttl_minutes):
            logger.info(f"Context expired for {key}, removing")
            del self._contexts[key]
            return None

        return context

    def clear_context(self, user_id: str, session_id: str) -> None:
        """
        Clear conversation context.

        Args:
            user_id: User ID
            session_id: Session ID
        """
        key = self._get_context_key(user_id, session_id)
        if key in self._contexts:
            del self._contexts[key]
            logger.info(f"Cleared conversation context for {key}")

    def is_waiting_for_info(self, user_id: str, session_id: str) -> bool:
        """
        Check if conversation is waiting for user to provide missing info.

        Args:
            user_id: User ID
            session_id: Session ID

        Returns:
            True if waiting for info, False otherwise
        """
        context = self.get_context(user_id, session_id)
        return context is not None and context.state == ConversationState.WAITING_FOR_INFO

    async def _get_db(self):
        """Get database connection."""
        if self._db is None:
            self._db = await get_db()
        return self._db

    def _run_async(self, coro):
        """Run async coroutine in sync context."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return asyncio.run(coro)

    def _db_conv_to_dict(self, db_conv: ConversationDB, messages: List[MessageDB] = None) -> dict:
        """Convert database conversation to dict."""
        msg_list = []
        if messages is None and hasattr(db_conv, 'messages'):
            messages = db_conv.messages
        if messages:
            for msg in messages:
                msg_dict = {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.created_at.isoformat()
                }
                if msg.data:
                    msg_dict["data"] = msg.data
                    # F-23: Restore thought from persisted data
                    if msg.data.get("thought"):
                        msg_dict["thought"] = msg.data["thought"]
                msg_list.append(msg_dict)

        return {
            "id": db_conv.id,
            "user_id": db_conv.username or "",
            "title": db_conv.title or "",
            "messages": msg_list,
            "created_at": db_conv.created_at.isoformat(),
            "updated_at": db_conv.updated_at.isoformat()
        }

    def save_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        data: dict = None,
        thought: list = None
    ) -> Conversation:
        """Save a message to a conversation."""
        return self._run_async(
            self._save_message_async(user_id, session_id, role, content, data, thought)
        )

    async def _save_message_async(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        data: dict = None,
        thought: list = None
    ) -> Conversation:
        """Save a message to a conversation in database."""
        db = await self._get_db()
        now = datetime.now()

        async with db.get_session() as session:
            # Find or create conversation
            result = await session.execute(
                select(ConversationDB).where(ConversationDB.id == session_id)
            )
            db_conv = result.scalar_one_or_none()

            if not db_conv:
                title = content[:50] if content else "新对话"
                db_conv = ConversationDB(
                    id=session_id,
                    user_id=None,  # Will store in username field for now
                    username=user_id,
                    title=title,
                    created_at=now,
                    updated_at=now,
                )
                session.add(db_conv)
                await session.flush()

            # Add message
            # F-23: Persist thought events into data["thought"] for history display
            msg_data = data.copy() if data else {}
            if thought:
                msg_data["thought"] = thought
            db_msg = MessageDB(
                conversation_id=db_conv.id,
                role=role,
                content=content,
                data=_serialize_data(msg_data) if msg_data else None,
                created_at=now,
            )
            session.add(db_msg)

            # Update title from first user message
            if role == "user":
                msg_count_result = await session.execute(
                    select(MessageDB).where(MessageDB.conversation_id == session_id)
                )
                existing_msgs = msg_count_result.scalars().all()
                if len(existing_msgs) <= 1:
                    db_conv.title = content[:50] if content else "新对话"

            db_conv.updated_at = now

            # Build return object
            all_msgs_result = await session.execute(
                select(MessageDB).where(MessageDB.conversation_id == session_id).order_by(MessageDB.created_at)
            )
            all_msgs = all_msgs_result.scalars().all()

            conv_dict = self._db_conv_to_dict(db_conv, all_msgs)
            return Conversation.from_dict(conv_dict)

    def get_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all conversations for a user."""
        return self._run_async(self._get_conversations_async(user_id))

    async def _get_conversations_async(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all conversations for a user from database."""
        db = await self._get_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(ConversationDB)
                .where(ConversationDB.username == user_id)
                .order_by(ConversationDB.updated_at.desc())
            )
            db_convs = result.scalars().all()

            conversations = []
            for db_conv in db_convs:
                # Get message count
                msg_result = await session.execute(
                    select(MessageDB).where(MessageDB.conversation_id == db_conv.id)
                )
                messages = msg_result.scalars().all()

                conv_dict = self._db_conv_to_dict(db_conv, messages)
                conversations.append(conv_dict)

            return conversations

    def get_conversation(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific conversation."""
        return self._run_async(self._get_conversation_async(user_id, session_id))

    async def _get_conversation_async(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific conversation from database."""
        db = await self._get_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(ConversationDB).where(
                    ConversationDB.id == session_id,
                    ConversationDB.username == user_id
                )
            )
            db_conv = result.scalar_one_or_none()

            if not db_conv:
                return None

            # Get messages
            msg_result = await session.execute(
                select(MessageDB)
                .where(MessageDB.conversation_id == db_conv.id)
                .order_by(MessageDB.created_at)
            )
            messages = msg_result.scalars().all()

            return self._db_conv_to_dict(db_conv, messages)

    def delete_conversation(self, user_id: str, session_id: str) -> bool:
        """Delete a conversation."""
        return self._run_async(self._delete_conversation_async(user_id, session_id))

    async def _delete_conversation_async(self, user_id: str, session_id: str) -> bool:
        """Delete a conversation from database."""
        db = await self._get_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(ConversationDB).where(
                    ConversationDB.id == session_id,
                    ConversationDB.username == user_id
                )
            )
            db_conv = result.scalar_one_or_none()

            if not db_conv:
                return False

            await session.delete(db_conv)
            return True

    def search_conversations(self, user_id: str, keyword: str) -> List[Dict[str, Any]]:
        """Search user's conversations by keyword."""
        return self._run_async(self._search_conversations_async(user_id, keyword))

    async def _search_conversations_async(self, user_id: str, keyword: str) -> List[Dict[str, Any]]:
        """Search user's conversations by keyword in database."""
        if not keyword:
            return []

        db = await self._get_db()
        keyword_lower = keyword.lower()
        results = []

        async with db.get_session() as session:
            # Get all conversations for user
            conv_result = await session.execute(
                select(ConversationDB).where(ConversationDB.username == user_id)
            )
            db_convs = conv_result.scalars().all()

            for db_conv in db_convs:
                # Search in messages
                msg_result = await session.execute(
                    select(MessageDB).where(MessageDB.conversation_id == db_conv.id)
                )
                messages = msg_result.scalars().all()

                for msg in messages:
                    content = msg.content or ""
                    if keyword_lower in content.lower():
                        results.append({
                            "conversation_id": db_conv.id,
                            "title": db_conv.title,
                            "matched_message": content[:200],
                            "timestamp": msg.created_at.isoformat(),
                            "role": msg.role
                        })
                        break  # Only include each conversation once

        return results

    def search_all_conversations(
        self,
        keyword: str = None,
        user_service=None,
        username: str = None,
        start_date: str = None,
        end_date: str = None
    ) -> List[Dict[str, Any]]:
        """Search all conversations (admin only)."""
        return self._run_async(
            self._search_all_conversations_async(keyword, user_service, username, start_date, end_date)
        )

    async def _search_all_conversations_async(
        self,
        keyword: str = None,
        user_service=None,
        username: str = None,
        start_date: str = None,
        end_date: str = None
    ) -> List[Dict[str, Any]]:
        """Search all conversations in database (admin only)."""
        results = []
        keyword_lower = keyword.lower() if keyword else None

        # Parse date filters
        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
            except ValueError:
                pass
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
            except ValueError:
                pass

        db = await self._get_db()
        async with db.get_session() as session:
            # Get all conversations
            result = await session.execute(select(ConversationDB))
            db_convs = result.scalars().all()

            for db_conv in db_convs:
                # Filter by date
                if start_dt or end_dt:
                    if start_dt and db_conv.updated_at < start_dt:
                        continue
                    if end_dt and db_conv.updated_at > end_dt:
                        continue

                # Get username
                user_username = db_conv.username or ""
                if user_service:
                    user = user_service.get_user_by_user_id(user_username)
                    if user:
                        user_username = user.username

                # Filter by username
                if username:
                    if username.lower() not in user_username.lower():
                        continue

                # Get messages
                msg_result = await session.execute(
                    select(MessageDB).where(MessageDB.conversation_id == db_conv.id)
                )
                messages = msg_result.scalars().all()

                # Search by keyword
                if keyword_lower:
                    for msg in messages:
                        content = msg.content or ""
                        if keyword_lower in content.lower():
                            results.append({
                                "conversation_id": db_conv.id,
                                "session_id": db_conv.id,
                                "user_id": db_conv.username,
                                "username": user_username,
                                "title": db_conv.title,
                                "matched_message": content[:200],
                                "timestamp": msg.created_at.isoformat(),
                                "updated_at": db_conv.updated_at.isoformat(),
                                "role": msg.role
                            })
                            break
                else:
                    # No keyword filter
                    last_msg = messages[-1] if messages else None
                    results.append({
                        "conversation_id": db_conv.id,
                        "session_id": db_conv.id,
                        "user_id": db_conv.username,
                        "username": user_username,
                        "title": db_conv.title,
                        "matched_message": (last_msg.content or "")[:200] if last_msg else "",
                        "timestamp": db_conv.updated_at.isoformat(),
                        "updated_at": db_conv.updated_at.isoformat(),
                        "message_count": len(messages)
                    })

        # Sort by timestamp descending
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results

    def get_all_conversations(self, user_service=None) -> List[Dict[str, Any]]:
        """Get all conversations (admin only)."""
        return self._run_async(self._get_all_conversations_async(user_service))

    async def _get_all_conversations_async(self, user_service=None) -> List[Dict[str, Any]]:
        """Get all conversations from database (admin only)."""
        db = await self._get_db()
        results = []

        async with db.get_session() as session:
            result = await session.execute(
                select(ConversationDB).order_by(ConversationDB.updated_at.desc())
            )
            db_convs = result.scalars().all()

            for db_conv in db_convs:
                # Get username
                username = db_conv.username or ""
                if user_service:
                    user = user_service.get_user_by_user_id(username)
                    if user:
                        username = user.username

                # Get message count
                msg_result = await session.execute(
                    select(MessageDB).where(MessageDB.conversation_id == db_conv.id)
                )
                messages = msg_result.scalars().all()

                results.append({
                    "conversation_id": db_conv.id,
                    "user_id": db_conv.username,
                    "username": username,
                    "title": db_conv.title,
                    "message_count": len(messages),
                    "created_at": db_conv.created_at.isoformat(),
                    "updated_at": db_conv.updated_at.isoformat()
                })

        return results


# Global conversation service instance
_conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    """Get conversation service instance."""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service