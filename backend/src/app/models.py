import datetime
import enum
import uuid

from sqlalchemy import Boolean, String, ForeignKey, Enum
from sqlalchemy.orm import relationship

from .db import db

class User(db.Model):
    __tablename__ = "User"
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(255), unique=True, nullable=True)
    discord_id = db.Column(db.String(255), unique=True, nullable=True)
    username = db.Column(db.String, unique=True, nullable=False)
    discord_username = db.Column(
        db.String, unique=True, nullable=False
    )  # TODO check if that is the user in discord
    hashed_password = db.Column(db.String(100), nullable=True)
    verified = db.Column(db.Boolean, default=False)
    in_community = db.Column(db.Boolean, default=False)
    created_at = db.Column(
        db.DateTime, default=datetime.datetime.now, server_default=db.text("CURRENT_TIMESTAMP")
    )
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.now, server_default=db.text("CURRENT_TIMESTAMP")
    )
    avatar_url = db.Column(db.String)
    role = db.Column(db.String, default="player")

    # Relationships (Cascade is handled via backref in child models)
    profile = db.relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan" )
    preferences = db.relationship("UserGamePreference", back_populates="user", cascade="all, delete-orphan" )
    availability = db.relationship("UserAvailability", back_populates="user", cascade="all, delete-orphan" )
    notifications = db.relationship("UserNotifications", back_populates="user", cascade="all, delete-orphan" )

    scheduled_sessions_organizer = db.relationship(
        "ScheduledSession",
        foreign_keys="ScheduledSession.organizer_user_id",
        back_populates="session_organizer",
        cascade="all, delete-orphan"
    )
    scheduled_sessions_participant = db.relationship(
        "ScheduledSession",
        foreign_keys="ScheduledSession.second_player_id",
        back_populates="session_participant",
        cascade="all, delete-orphan"
    )

    sent_requests = db.relationship(
        "GameRequest", foreign_keys="GameRequest.sender_user_id", back_populates="sender", cascade="all, delete-orphan"
    )
    received_requests = db.relationship(
        "GameRequest", foreign_keys="GameRequest.recipient_user_id", back_populates="recipient", cascade="all, delete-orphan"
    )
    friend_sent_requests = db.relationship(
        "UserFriends", foreign_keys="UserFriends.sender_user_id", back_populates="friend_sender", cascade="all, delete-orphan"
    )
    friend_received_requests = db.relationship(
        "UserFriends", foreign_keys="UserFriends.recipient_user_id", back_populates="friend_recipient", cascade="all, delete-orphan"
    )

    user_sessions = db.relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "discord_username": self.discord_username,
            "discord_id": self.discord_id,
            "email_verified": self.verified,
            "in_community": self.in_community,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "avatar_url": self.avatar_url,
            "role": self.role
        }


class CommunicationPreferences(Enum):
    WRITTEN = "Written"
    VOICE = "Voice"
    VIDEO = "video"
    NO_TALKING = "No talking"


class UserProfile(db.Model):
    __tablename__ = "UserProfile"
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # >>> תיקון: הוספת ondelete='CASCADE' <<<
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("User.id", ondelete="CASCADE"), nullable=False, unique=True)
    bio = db.Column(db.String(64))
    avatar_url = db.Column(db.String(64), default="https://api.dicebear.com/9.x/thumbs/svg?seed=Jessica")  # TODO ?
    language = db.Column(db.String(64))  # TODO add a list of acceptable languages?
    timezone = db.Column(db.String(64))  # TODO how to do the timezone?
    communication_preferences = db.Column(db.String(64))
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now, server_default=db.text("CURRENT_TIMESTAMP"))

    user = db.relationship("User", back_populates="profile" )

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "language": self.language,
            "timezone": self.timezone,
            "communication_preferences": self.communication_preferences,
            "updated_at": str(self.updated_at)
        }


class Game(db.Model):
    __tablename__ = 'Game'
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_name = db.Column(db.String, unique=True, nullable=False)
    category = db.Column(db.String, nullable=True)
    min_players = db.Column(db.Integer, nullable=True)
    max_players = db.Column(db.Integer, nullable=True)
    avg_session_duration = db.Column(db.Integer, nullable=True)  # minutes
    difficulty_level = db.Column(db.String, nullable=True)  # easy, medium, hard
    icon_url = db.Column(db.String, nullable=True)
    icon = db.Column(db.String, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    game_site_url = db.Column(db.String, nullable=True)

    preferences = db.relationship("UserGamePreference", back_populates="game", cascade="all, delete-orphan" )
    scheduled_sessions = db.relationship("ScheduledSession", back_populates="game", cascade="all, delete-orphan" )
    game_requests = db.relationship("GameRequest", back_populates="game", cascade="all, delete-orphan" )

    def to_dict(self):
        return {
            "id": str(self.id),
            "game_name": self.game_name,
            "category": self.category,
            "min_players": self.min_players,
            "max_players": self.max_players,
            "avg_session_duration": self.avg_session_duration,
            "difficulty_level": self.difficulty_level,
            "icon_url": self.icon_url,
            "icon": self.icon,
            "is_active": self.is_active,
            "game_site_url": self.game_site_url
        }


class UserNotifications(db.Model):
    __tablename__ = "UserNotifications"
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("User.id"), nullable=False)
    title = db.Column(String, nullable=False, default="General")
    message = db.Column(String, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(
        db.DateTime, default=datetime.datetime.now, server_default=db.text("CURRENT_TIMESTAMP")
    )
    user = db.relationship("User", back_populates="notifications")

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": str(self.title) if self.title else "General message",
            "message": str(self.message),
            "is_read": str(self.is_read),
            "created_at": str(self.created_at)
        }

class FriendStatus(str, enum.Enum):
    PENDING = "Pending"
    ACCEPTED = "Accepted"
    BLOCKED = "Blocked"

class UserFriends(db.Model):
    __tablename__ = "UserFriends"
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    recipient_user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    message = db.Column(db.Text)
    status = db.Column(Enum(FriendStatus), default="Pending", nullable=False)

    created_at = db.Column(
        db.DateTime, default=datetime.datetime.now, server_default=db.text("CURRENT_TIMESTAMP")
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.datetime.now,
        server_default=db.text("CURRENT_TIMESTAMP"),
        onupdate=datetime.datetime.now(),
        nullable=False
    )
    friend_sender = db.relationship("User", foreign_keys=[sender_user_id], back_populates="friend_sent_requests")
    friend_recipient = db.relationship(
        "User", foreign_keys=[recipient_user_id], back_populates="friend_received_requests"
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "sender_user_id": str(self.sender_user_id),
            "recipient_user_id": str(self.recipient_user_id),
            "message": str(self.message),
            "status": str(self.status),
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at)
        }


class UserGamePreference(db.Model):
    __tablename__ = "UserGamePreference"
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # >>> תיקון: הוספת ondelete='CASCADE' <<<
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    game_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("Game.id"), nullable=False)

    user = db.relationship("User", back_populates="preferences")
    game = db.relationship("Game", back_populates="preferences")

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "game_id": str(self.game_id)
        }


class UserAvailability(db.Model):
    __tablename__ = "UserAvailability"
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # >>> תיקון: הוספת ondelete='CASCADE' <<<
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    day_of_week = db.Column(String, nullable=False)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    is_recurring = db.Column(Boolean)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now, server_default=db.text("CURRENT_TIMESTAMP"))

    user = db.relationship("User", back_populates="availability")

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "day_of_week": str(self.day_of_week),
            "start_time": str(self.start_time) if self.start_time else None,
            "end_time": str(self.end_time) if self.end_time else None,
            "is_recurring": str(self.is_recurring),
            "updated_at": str(self.updated_at)
        }


class EmailVerification(db.Model):
    __tablename__ = "EmailVerification"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # זה כבר היה נכון - ondelete='CASCADE'
    user_id = db.Column(
        db.UUID(as_uuid=True), db.ForeignKey("User.id", ondelete="CASCADE"), nullable=False
    )
    verification_code = db.Column(db.String(255), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime(timezone=False))
    created_at = db.Column(
        db.DateTime, default=datetime.datetime.now, server_default=db.text("CURRENT_TIMESTAMP")
    )
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.now, server_default=db.text("CURRENT_TIMESTAMP")
    )

    def __repr__(self):
        return f"<EmailVerification {self.verification_code}>"


class ScheduledSession(db.Model):
    """Manages scheduled gaming sessions."""

    __tablename__ = "ScheduledSession"
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("Game.id"), nullable=False)
    # >>> תיקון: הוספת ondelete='CASCADE' ל-organizer <<<
    organizer_user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    # >>> תיקון: הוספת ondelete='CASCADE' ל-second_player <<<
    second_player_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    scheduled_date = db.Column(db.Date)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    timezone = db.Column(db.String, default="IDT")
    status = db.Column(db.String, default="accepted")
    # >>> תיקון: הוספת ondelete='CASCADE' ל-GameRequest <<<
    session_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("GameRequest.id", ondelete="CASCADE"), nullable=False)
    session_type = db.Column(db.String, default="private")
    max_participants = db.Column(db.Integer, default=2)
    description = db.Column(db.Text)
    meeting_link = db.Column(db.String)
    reminder_sent = db.Column(db.Boolean, default=False, server_default=db.false())
    game_site_url = db.Column(db.String, nullable=True)

    created_at = db.Column(
        db.DateTime, default=datetime.datetime.now, server_default=db.text("CURRENT_TIMESTAMP")
    )

    session_organizer = db.relationship(
        "User", foreign_keys=[organizer_user_id], back_populates="scheduled_sessions_organizer"
    )
    session_participant = db.relationship(
        "User", foreign_keys=[second_player_id], back_populates="scheduled_sessions_participant"
    )
    game = db.relationship("Game", back_populates="scheduled_sessions")
    user_session = db.relationship("GameRequest", foreign_keys=[session_id], back_populates='scheduled_sessions')

    def to_dict(self):
        return {
            "id": str(self.id),
            "game_id": str(self.game_id) if self.game_id else None,
            "organizer_user_id": str(self.organizer_user_id),
            "second_player_id": str(self.second_player_id),
            "scheduled_date": str(self.scheduled_date) if self.scheduled_date else None,
            "start_time": str(self.start_time) if self.start_time else None,
            "end_time": str(self.end_time) if self.end_time else None,
            "timezone": self.timezone,
            "status": self.status if self.status else "pending",
            "session_id": str(self.session_id) if self.session_id else None,
            "session_type": self.session_type,
            "max_participants": self.max_participants,
            "description": self.description,
            "meeting_link": self.meeting_link,
            "reminder_sent": self.reminder_sent,
            "game_site_url": self.game_site_url,
            "created_at": str(self.created_at) if self.created_at else None
        }

    def to_dict_essentials(self):
        return {
            "id": str(self.id),
            "game_id": str(self.game_id) if self.game_id else None,
            "organizer_user_id": str(self.organizer_user_id),
            "second_player_id": str(self.second_player_id),
            "scheduled_date": str(self.scheduled_date) if self.scheduled_date else None,
            "start_time": str(self.start_time) if self.start_time else None,
            "end_time": str(self.end_time) if self.end_time else None,            
            "status": self.status,
            "meeting_link": self.meeting_link,
        }


class GameRequest(db.Model):
    """Handles requests to play a game with another user."""

    __tablename__ = "GameRequest"
    # Removed primary_key=True from other columns
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # >>> תיקון: הוספת ondelete='CASCADE' ל-sender_user_id <<<
    sender_user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    # >>> תיקון: הוספת ondelete='CASCADE' ל-recipient_user_id <<<
    recipient_user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    game_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("Game.id"), nullable=False)
    suggested_time = db.Column(db.DateTime)
    message = db.Column(db.Text)
    status = db.Column(db.String, default="pending")

    created_at = db.Column(
        db.DateTime, default=datetime.datetime.now, server_default=db.text("CURRENT_TIMESTAMP")
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.datetime.now,
        server_default=db.text("CURRENT_TIMESTAMP"),
        onupdate=datetime.datetime.now(),
        nullable=False
    )

    sender = db.relationship("User", foreign_keys=[sender_user_id], back_populates="sent_requests")
    recipient = db.relationship(
        "User", foreign_keys=[recipient_user_id], back_populates="received_requests"
    )
    game = db.relationship("Game", back_populates="game_requests")
    scheduled_sessions = db.relationship("ScheduledSession", back_populates="user_session", cascade="all, delete-orphan" )

    def to_dict(self):
        return {
            "id": str(self.id),
            "sender_user_id": str(self.sender_user_id) if self.sender_user_id else None,
            "recipient_user_id": str(self.recipient_user_id) if self.recipient_user_id else None,
            "game_id": str(self.game_id) if self.game_id else None,
            "suggested_time": str(self.suggested_time) if self.suggested_time else None,
            "message": self.message,
            "status": self.status,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at)
        }


class UserSession(db.Model):
    """Tracks user session data."""

    __tablename__ = "UserSession"
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # >>> תיקון: הוספת ondelete='CASCADE' <<<
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    session_token = db.Column(db.UUID(as_uuid=True), nullable=False)
    expires_at = db.Column(db.DateTime)
    last_activity = db.Column(db.DateTime)
    user_agent = db.Column(db.Text)
    ip_address = db.Column(db.String)

    user = db.relationship("User", back_populates="user_sessions")

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "session_token": str(self.session_token),
            "expires_at": str(self.expires_at) if self.expires_at else None,
            "last_activity": str(self.last_activity) if self.last_activity else None,
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
        }