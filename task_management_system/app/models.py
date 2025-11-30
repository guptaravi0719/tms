from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, Enum, Table, Boolean, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Association table for task assignees (many-to-many)
task_assignees = Table(
    'task_assignees',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id', ondelete='CASCADE')),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE')),
    Index('idx_task_assignees_task', 'task_id'),
    Index('idx_task_assignees_user', 'user_id')
)


# Association table for task tags
task_tags = Table(
    'task_tags',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id', ondelete='CASCADE')),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'))
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255))
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.MEMBER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    created_tasks = relationship("Task", back_populates="creator", foreign_keys="Task.creator_id")
    assigned_tasks = relationship("Task", secondary=task_assignees, back_populates="assignees")
    task_history = relationship("TaskHistory", back_populates="user")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text)
    status = Column(Enum(TaskStatus), default=TaskStatus.TODO, nullable=False, index=True)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False, index=True)
    due_date = Column(Date, nullable=True, index=True)
    
    # Foreign keys
    creator_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    parent_task_id = Column(Integer, ForeignKey('tasks.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    creator = relationship("User", back_populates="created_tasks", foreign_keys=[creator_id])
    assignees = relationship("User", secondary=task_assignees, back_populates="assigned_tasks")
    parent_task = relationship("Task", remote_side=[id], backref="subtasks")
    tags = relationship("Tag", secondary=task_tags, back_populates="tasks")
    
    # Task dependencies
    blocking_tasks = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.blocked_task_id",
        back_populates="blocked_task",
        cascade="all, delete-orphan"
    )
    blocked_by_tasks = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.blocking_task_id",
        back_populates="blocking_task",
        cascade="all, delete-orphan"
    )
    
    # History
    history = relationship("TaskHistory", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_task_status_priority', 'status', 'priority'),
        Index('idx_task_creator_status', 'creator_id', 'status'),
    )


class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    id = Column(Integer, primary_key=True, index=True)
    blocking_task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False)
    blocked_task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    blocking_task = relationship("Task", foreign_keys=[blocking_task_id], back_populates="blocked_by_tasks")
    blocked_task = relationship("Task", foreign_keys=[blocked_task_id], back_populates="blocking_tasks")

    __table_args__ = (
        Index('idx_blocking_task', 'blocking_task_id'),
        Index('idx_blocked_task', 'blocked_task_id'),
    )


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    tasks = relationship("Task", secondary=task_tags, back_populates="tags")


class TaskHistory(Base):
    __tablename__ = "task_history"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String(100), nullable=False)  # created, updated, status_changed, assigned, etc.
    field_name = Column(String(100))  # Which field changed
    old_value = Column(Text)
    new_value = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    task = relationship("Task", back_populates="history")
    user = relationship("User", back_populates="task_history")

    __table_args__ = (
        Index('idx_task_history_task_time', 'task_id', 'timestamp'),
        Index('idx_task_history_user_time', 'user_id', 'timestamp'),
    )

