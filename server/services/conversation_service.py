from uuid import UUID
from fastapi import HTTPException
from models import Conversation, Message
from sqlalchemy.orm import Session

class ConversationService:

    def get_or_create_conversation(
        self,
        session:Session,
        conversation_id: UUID | None,
    ):
        if conversation_id is None:
            conversation = Conversation()
            session.add(conversation)

            session.flush()
            return conversation

        conversation = session.get(Conversation, conversation_id)

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )
        return conversation

    def save_message(
        self,
        session: Session,
        conversation_id: UUID,
        role: str,
        content: str,
    ) -> Message:

        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )

        session.add(message)
        session.flush()

        return message
    
    def build_messages(
        self,
        session: Session,
        conversation_id: UUID,
    ):
        history = (
        session.query(Message)
        .filter(Message.conversation_id==conversation_id)
        .order_by(Message.created_at)
        .all()
        )
        
        messages = []

        for msg in history:
            messages.append(
            {
                "role": msg.role,
                "content": msg.content,
            }
        )

        return messages


conversation_service = ConversationService()
