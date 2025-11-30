from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from app.models import UserRole, TaskStatus, TaskPriority


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.MEMBER


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None


# Tag Schemas
class TagBase(BaseModel):
    name: str


class TagCreate(TagBase):
    pass


class TagResponse(TagBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Task Schemas
class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[date] = None


class TaskCreate(TaskBase):
    assignee_ids: Optional[List[int]] = []
    tag_names: Optional[List[str]] = []
    parent_task_id: Optional[int] = None
    
    @field_validator('parent_task_id')
    @classmethod
    def validate_parent_task_id(cls, v):
        # Convert 0 to None (0 is not a valid ID)
        if v == 0:
            return None
        return v


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[date] = None
    assignee_ids: Optional[List[int]] = None
    tag_names: Optional[List[str]] = None


class TaskBulkUpdate(BaseModel):
    task_ids: List[int] = Field(..., min_items=1)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee_ids: Optional[List[int]] = None
    tag_names: Optional[List[str]] = None


class TaskResponse(TaskBase):
    id: int
    creator_id: int
    parent_task_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    creator: UserResponse
    assignees: List[UserResponse] = []
    tags: List[TagResponse] = []
    subtask_count: Optional[int] = 0

    class Config:
        from_attributes = True


class TaskDetailResponse(TaskResponse):
    subtasks: List['TaskResponse'] = []
    blocking_task_ids: List[int] = []
    blocked_by_task_ids: List[int] = []


# Task Dependency Schemas
class TaskDependencyCreate(BaseModel):
    blocking_task_id: int  # The task that must be completed first


class TaskDependencyResponse(BaseModel):
    id: int
    blocking_task_id: int
    blocked_task_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Task History Schemas
class TaskHistoryResponse(BaseModel):
    id: int
    task_id: int
    user_id: int
    action: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    timestamp: datetime
    user: UserResponse

    class Config:
        from_attributes = True


# Filter Schemas
class TaskFilter(BaseModel):
    status: Optional[List[TaskStatus]] = None
    priority: Optional[List[TaskPriority]] = None
    assignee_ids: Optional[List[int]] = None
    creator_ids: Optional[List[int]] = None
    tag_names: Optional[List[str]] = None
    due_date_from: Optional[date] = None
    due_date_to: Optional[date] = None
    created_from: Optional[date] = None
    created_to: Optional[date] = None
    search: Optional[str] = None  # Search in title and description
    is_overdue: Optional[bool] = None
    has_subtasks: Optional[bool] = None
    parent_task_id: Optional[int] = None
    logic_operator: str = "AND"  # AND or OR

    @field_validator('parent_task_id')
    @classmethod
    def validate_parent_task_id(cls, v):
        # Convert 0 to None (0 is not a valid ID)
        if v == 0:
            return None
        return v
    
    @field_validator('logic_operator')
    @classmethod
    def validate_operator(cls, v):
        if v not in ["AND", "OR"]:
            raise ValueError("logic_operator must be 'AND' or 'OR'")
        return v
