"""
BuildBot Collaboration Features
Team collaboration with @mentions, comments, and notifications.
Compatible with Python 3.14+
"""

import json
import logging
import re
from datetime import datetime
from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications."""
    BUILD_COMPLETE = "build_complete"
    BUILD_FAILED = "build_failed"
    MENTION = "mention"
    COMMENT = "comment"
    SCHEDULE_REMINDER = "schedule_reminder"
    APPROVAL_REQUIRED = "approval_required"


@dataclass
class TeamMember:
    """Represents a team member."""
    username: str
    display_name: str
    email: str = ""
    gchat_id: str = ""
    role: str = "developer"  # developer, lead, admin
    notifications_enabled: bool = True
    favorite_jobs: list[str] = field(default_factory=list)


@dataclass
class Comment:
    """Comment on a build."""
    id: str
    build_job: str
    build_number: int
    author: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    mentions: list[str] = field(default_factory=list)
    reactions: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class Notification:
    """User notification."""
    id: str
    user: str
    type: NotificationType
    title: str
    message: str
    link: str = ""
    read: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    data: dict = field(default_factory=dict)


class CollaborationManager:
    """Manages team collaboration features."""
    
    def __init__(self, data_dir: str = "collab_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.members: dict[str, TeamMember] = {}
        self.comments: list[Comment] = []
        self.notifications: list[Notification] = []
        
        self._load_data()
    
    def _load_data(self):
        """Load collaboration data."""
        # Load members
        members_file = self.data_dir / "members.json"
        if members_file.exists():
            try:
                with open(members_file, 'r') as f:
                    data = json.load(f)
                    for m in data:
                        member = TeamMember(
                            username=m['username'],
                            display_name=m['display_name'],
                            email=m.get('email', ''),
                            gchat_id=m.get('gchat_id', ''),
                            role=m.get('role', 'developer'),
                            notifications_enabled=m.get('notifications_enabled', True),
                            favorite_jobs=m.get('favorite_jobs', [])
                        )
                        self.members[member.username] = member
            except Exception as e:
                logger.error(f"Failed to load members: {e}")
        
        # Load comments
        comments_file = self.data_dir / "comments.json"
        if comments_file.exists():
            try:
                with open(comments_file, 'r') as f:
                    data = json.load(f)
                    for c in data:
                        self.comments.append(Comment(
                            id=c['id'],
                            build_job=c['build_job'],
                            build_number=c['build_number'],
                            author=c['author'],
                            content=c['content'],
                            timestamp=datetime.fromisoformat(c['timestamp']),
                            mentions=c.get('mentions', []),
                            reactions=c.get('reactions', {})
                        ))
            except Exception as e:
                logger.error(f"Failed to load comments: {e}")
    
    def _save_members(self):
        """Save members data."""
        try:
            data = [
                {
                    'username': m.username,
                    'display_name': m.display_name,
                    'email': m.email,
                    'gchat_id': m.gchat_id,
                    'role': m.role,
                    'notifications_enabled': m.notifications_enabled,
                    'favorite_jobs': m.favorite_jobs
                }
                for m in self.members.values()
            ]
            with open(self.data_dir / "members.json", 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save members: {e}")
    
    def _save_comments(self):
        """Save comments data."""
        try:
            data = [
                {
                    'id': c.id,
                    'build_job': c.build_job,
                    'build_number': c.build_number,
                    'author': c.author,
                    'content': c.content,
                    'timestamp': c.timestamp.isoformat(),
                    'mentions': c.mentions,
                    'reactions': c.reactions
                }
                for c in self.comments
            ]
            with open(self.data_dir / "comments.json", 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save comments: {e}")
    
    def add_member(
        self,
        username: str,
        display_name: str,
        email: str = "",
        role: str = "developer"
    ) -> TeamMember:
        """Add a team member."""
        member = TeamMember(
            username=username,
            display_name=display_name,
            email=email,
            role=role
        )
        self.members[username] = member
        self._save_members()
        return member
    
    def get_member(self, username: str) -> Optional[TeamMember]:
        """Get a team member."""
        return self.members.get(username)
    
    def list_members(self) -> list[TeamMember]:
        """List all team members."""
        return list(self.members.values())
    
    def extract_mentions(self, text: str) -> list[str]:
        """Extract @mentions from text."""
        pattern = r'@(\w+)'
        mentions = re.findall(pattern, text)
        # Filter to valid usernames
        return [m for m in mentions if m in self.members]
    
    def add_comment(
        self,
        build_job: str,
        build_number: int,
        author: str,
        content: str
    ) -> Comment:
        """Add a comment to a build."""
        import uuid
        
        mentions = self.extract_mentions(content)
        
        comment = Comment(
            id=str(uuid.uuid4())[:8],
            build_job=build_job,
            build_number=build_number,
            author=author,
            content=content,
            mentions=mentions
        )
        
        self.comments.append(comment)
        self._save_comments()
        
        # Notify mentioned users
        for username in mentions:
            self.create_notification(
                user=username,
                type=NotificationType.MENTION,
                title=f"You were mentioned by @{author}",
                message=content[:100],
                link=f"/build/{build_job}/{build_number}",
                data={'build_job': build_job, 'build_number': build_number}
            )
        
        return comment
    
    def get_build_comments(self, build_job: str, build_number: int) -> list[Comment]:
        """Get comments for a build."""
        return [
            c for c in self.comments
            if c.build_job == build_job and c.build_number == build_number
        ]
    
    def add_reaction(self, comment_id: str, user: str, reaction: str) -> bool:
        """Add a reaction to a comment."""
        for comment in self.comments:
            if comment.id == comment_id:
                if reaction not in comment.reactions:
                    comment.reactions[reaction] = []
                if user not in comment.reactions[reaction]:
                    comment.reactions[reaction].append(user)
                    self._save_comments()
                return True
        return False
    
    def create_notification(
        self,
        user: str,
        type: NotificationType,
        title: str,
        message: str,
        link: str = "",
        data: dict = None
    ) -> Notification:
        """Create a notification for a user."""
        import uuid
        
        notification = Notification(
            id=str(uuid.uuid4())[:8],
            user=user,
            type=type,
            title=title,
            message=message,
            link=link,
            data=data or {}
        )
        
        self.notifications.append(notification)
        
        # Keep only last 100 notifications per user
        user_notifs = [n for n in self.notifications if n.user == user]
        if len(user_notifs) > 100:
            oldest = min(user_notifs, key=lambda x: x.timestamp)
            self.notifications.remove(oldest)
        
        return notification
    
    def get_notifications(self, user: str, unread_only: bool = False) -> list[Notification]:
        """Get notifications for a user."""
        notifs = [n for n in self.notifications if n.user == user]
        if unread_only:
            notifs = [n for n in notifs if not n.read]
        return sorted(notifs, key=lambda x: x.timestamp, reverse=True)
    
    def mark_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        for n in self.notifications:
            if n.id == notification_id:
                n.read = True
                return True
        return False
    
    def notify_build_complete(
        self,
        job_name: str,
        build_number: int,
        status: str,
        triggered_by: str = ""
    ):
        """Notify relevant users about build completion."""
        # Notify the triggerer
        if triggered_by and triggered_by in self.members:
            self.create_notification(
                user=triggered_by,
                type=NotificationType.BUILD_COMPLETE if status == 'SUCCESS' else NotificationType.BUILD_FAILED,
                title=f"Build #{build_number} {status}",
                message=f"Your build of {job_name} has completed.",
                link=f"/build/{job_name}/{build_number}",
                data={'job_name': job_name, 'build_number': build_number, 'status': status}
            )
        
        # Notify users who favorited this job
        for member in self.members.values():
            if job_name in member.favorite_jobs and member.username != triggered_by:
                if member.notifications_enabled:
                    self.create_notification(
                        user=member.username,
                        type=NotificationType.BUILD_COMPLETE if status == 'SUCCESS' else NotificationType.BUILD_FAILED,
                        title=f"Build #{build_number} {status}",
                        message=f"Favorited job {job_name} has completed.",
                        link=f"/build/{job_name}/{build_number}",
                        data={'job_name': job_name, 'build_number': build_number, 'status': status}
                    )
    
    def format_message_with_mentions(self, text: str) -> str:
        """Format message with highlighted mentions."""
        def replace_mention(match):
            username = match.group(1)
            if username in self.members:
                display_name = self.members[username].display_name
                return f"**@{display_name}**"
            return match.group(0)
        
        return re.sub(r'@(\w+)', replace_mention, text)


# Global instance
collaboration = CollaborationManager()
