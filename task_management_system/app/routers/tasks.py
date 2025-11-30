from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime, date, timedelta
import json
from app.database import get_db
from app.models import Task, User, Tag, TaskDependency, TaskHistory, TaskStatus
from app.schemas import (
    TaskCreate, TaskUpdate, TaskResponse, TaskDetailResponse,
    TaskBulkUpdate, TaskFilter, TaskDependencyCreate, TaskDependencyResponse,
    TaskHistoryResponse
)
from app.auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"])


def log_task_history(db: Session, task_id: int, user_id: int, action: str, field_name: str = None, old_value: str = None, new_value: str = None):
    """Helper function to log task changes"""
    history = TaskHistory(
        task_id=task_id,
        user_id=user_id,
        action=action,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value
    )
    db.add(history)


def get_or_create_tag(db: Session, tag_name: str) -> Tag:
    """Get existing tag or create new one"""
    tag = db.query(Tag).filter(Tag.name == tag_name.lower()).first()
    if not tag:
        tag = Tag(name=tag_name.lower())
        db.add(tag)
        db.flush()
    return tag


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new task"""
    # Validate parent task exists if specified
    if task.parent_task_id:
        parent = db.query(Task).filter(Task.id == task.parent_task_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent task not found")
    
    # Create task
    db_task = Task(
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        creator_id=current_user.id,
        parent_task_id=task.parent_task_id
    )
    
    # Add assignees
    if task.assignee_ids:
        assignees = db.query(User).filter(User.id.in_(task.assignee_ids)).all()
        if len(assignees) != len(task.assignee_ids):
            raise HTTPException(status_code=400, detail="One or more assignees not found")
        db_task.assignees = assignees
    
    # Add tags
    if task.tag_names:
        for tag_name in task.tag_names:
            tag = get_or_create_tag(db, tag_name)
            db_task.tags.append(tag)
    
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Log history with initial task details
    initial_state = {
        "title": db_task.title,
        "status": db_task.status.value,
        "priority": db_task.priority.value,
        "due_date": str(db_task.due_date) if db_task.due_date else None,
        "assignees": [u.username for u in db_task.assignees],
        "tags": [t.name for t in db_task.tags]
    }
    log_task_history(db, db_task.id, current_user.id, "created", 
                    "initial_state", None, json.dumps(initial_state))
    db.commit()
    
    # Add subtask count
    db_task.subtask_count = len(db_task.subtasks)
    return db_task


@router.get("/", response_model=List[TaskResponse])
def list_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all tasks with pagination"""
    tasks = db.query(Task).options(
        joinedload(Task.creator),
        joinedload(Task.assignees),
        joinedload(Task.tags)
    ).offset(skip).limit(limit).all()
    
    # Add subtask count to each task
    for task in tasks:
        task.subtask_count = len(task.subtasks)
    
    return tasks


@router.post("/filter", response_model=List[TaskResponse])
def filter_tasks(
    filters: TaskFilter,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Filter tasks with multiple criteria using AND/OR logic.
    Supports filtering by status, priority, assignee, creator, tags, dates, and more.
    """
    query = db.query(Task).options(
        joinedload(Task.creator),
        joinedload(Task.assignees),
        joinedload(Task.tags)
    )
    
    conditions = []
    
    # Status filter
    if filters.status:
        conditions.append(Task.status.in_(filters.status))
    
    # Priority filter
    if filters.priority:
        conditions.append(Task.priority.in_(filters.priority))
    
    # Creator filter
    if filters.creator_ids:
        conditions.append(Task.creator_id.in_(filters.creator_ids))
    
    # Assignee filter
    if filters.assignee_ids:
        conditions.append(Task.assignees.any(User.id.in_(filters.assignee_ids)))
    
    # Tag filter
    if filters.tag_names:
        tag_names_lower = [t.lower() for t in filters.tag_names]
        conditions.append(Task.tags.any(Tag.name.in_(tag_names_lower)))
    
    # Due date filter
    if filters.due_date_from:
        conditions.append(Task.due_date >= filters.due_date_from)
    if filters.due_date_to:
        conditions.append(Task.due_date <= filters.due_date_to)
    
    # Created date filter (convert date to datetime for comparison)
    if filters.created_from:
        created_from_dt = datetime.combine(filters.created_from, datetime.min.time())
        conditions.append(Task.created_at >= created_from_dt)
    if filters.created_to:
        created_to_dt = datetime.combine(filters.created_to, datetime.max.time())
        conditions.append(Task.created_at <= created_to_dt)
    
    # Search in title and description
    if filters.search:
        search_pattern = f"%{filters.search}%"
        conditions.append(
            or_(
                Task.title.ilike(search_pattern),
                Task.description.ilike(search_pattern)
            )
        )
    
    # Overdue filter
    if filters.is_overdue:
        today = date.today()
        conditions.append(
            and_(
                Task.due_date < today,
                Task.status != TaskStatus.COMPLETED
            )
        )
    
    # Has subtasks filter
    if filters.has_subtasks is not None:
        if filters.has_subtasks:
            subquery = db.query(Task.id).filter(Task.parent_task_id.isnot(None)).subquery()
            conditions.append(Task.id.in_(subquery))
        else:
            conditions.append(Task.parent_task_id.is_(None))
    
    # Parent task filter
    if filters.parent_task_id is not None:
        conditions.append(Task.parent_task_id == filters.parent_task_id)
    
    # Apply filters with AND or OR logic
    if conditions:
        if filters.logic_operator == "AND":
            query = query.filter(and_(*conditions))
        else:  # OR
            query = query.filter(or_(*conditions))
    
    tasks = query.offset(skip).limit(limit).all()
    
    # Add subtask count
    for task in tasks:
        task.subtask_count = len(task.subtasks)
    
    return tasks


@router.get("/{task_id}", response_model=TaskDetailResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific task with full details including subtasks and dependencies"""
    task = db.query(Task).options(
        joinedload(Task.creator),
        joinedload(Task.assignees),
        joinedload(Task.tags),
        joinedload(Task.subtasks)
    ).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Add subtask count
    task.subtask_count = len(task.subtasks)
    
    # Get blocking and blocked by task IDs
    blocking_task_ids = [dep.blocked_task_id for dep in task.blocked_by_tasks]
    blocked_by_task_ids = [dep.blocking_task_id for dep in task.blocking_tasks]
    
    # Create response
    response = TaskDetailResponse.model_validate(task)
    response.blocking_task_ids = blocking_task_ids
    response.blocked_by_task_ids = blocked_by_task_ids
    
    return response


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a task"""
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Update fields and log changes
    update_data = task_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if field == "assignee_ids":
            if value is not None:
                old_assignees = [str(u.id) for u in db_task.assignees]
                assignees = db.query(User).filter(User.id.in_(value)).all()
                if len(assignees) != len(value):
                    raise HTTPException(status_code=400, detail="One or more assignees not found")
                db_task.assignees = assignees
                new_assignees = [str(u.id) for u in assignees]
                log_task_history(db, task_id, current_user.id, "updated", "assignees", 
                               ",".join(old_assignees), ",".join(new_assignees))
        elif field == "tag_names":
            if value is not None:
                old_tags = [t.name for t in db_task.tags]
                db_task.tags.clear()
                for tag_name in value:
                    tag = get_or_create_tag(db, tag_name)
                    db_task.tags.append(tag)
                new_tags = [t.name for t in db_task.tags]
                log_task_history(db, task_id, current_user.id, "updated", "tags",
                               ",".join(old_tags), ",".join(new_tags))
        else:
            old_value = getattr(db_task, field, None)
            if old_value != value:
                setattr(db_task, field, value)
                log_task_history(db, task_id, current_user.id, "updated", field,
                               str(old_value) if old_value else None,
                               str(value) if value else None)
                
                # Update completed_at if status changed to completed
                if field == "status" and value == TaskStatus.COMPLETED:
                    db_task.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_task)
    
    # Add subtask count
    db_task.subtask_count = len(db_task.subtasks)
    return db_task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a task"""
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check permissions (only creator or admin can delete)
    if db_task.creator_id != current_user.id and current_user.role.value not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this task")
    
    db.delete(db_task)
    db.commit()
    return None


@router.post("/bulk-update", response_model=dict)
def bulk_update_tasks(
    bulk_update: TaskBulkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update multiple tasks at once.
    Supports updating status, priority, assignees, and tags for multiple tasks.
    """
    tasks = db.query(Task).filter(Task.id.in_(bulk_update.task_ids)).all()
    
    if len(tasks) != len(bulk_update.task_ids):
        raise HTTPException(status_code=400, detail="One or more tasks not found")
    
    updated_count = 0
    update_data = bulk_update.model_dump(exclude={"task_ids"}, exclude_unset=True)
    
    for task in tasks:
        for field, value in update_data.items():
            if field == "assignee_ids":
                if value is not None:
                    assignees = db.query(User).filter(User.id.in_(value)).all()
                    task.assignees = assignees
                    log_task_history(db, task.id, current_user.id, "bulk_updated", "assignees")
            elif field == "tag_names":
                if value is not None:
                    task.tags.clear()
                    for tag_name in value:
                        tag = get_or_create_tag(db, tag_name)
                        task.tags.append(tag)
                    log_task_history(db, task.id, current_user.id, "bulk_updated", "tags")
            else:
                old_value = getattr(task, field, None)
                if old_value != value and value is not None:
                    setattr(task, field, value)
                    log_task_history(db, task.id, current_user.id, "bulk_updated", field,
                                   str(old_value), str(value))
                    
                    # Update completed_at if status changed to completed
                    if field == "status" and value == TaskStatus.COMPLETED:
                        task.completed_at = datetime.utcnow()
        
        updated_count += 1
    
    db.commit()
    
    return {
        "message": f"Successfully updated {updated_count} tasks",
        "updated_task_ids": bulk_update.task_ids
    }


@router.post("/{task_id}/dependencies", response_model=TaskDependencyResponse, status_code=status.HTTP_201_CREATED)
def create_task_dependency(
    task_id: int,  # The blocked task (from URL path)
    dependency: TaskDependencyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a task dependency where task_id (in URL) is blocked by blocking_task_id (in body).
    
    Example: POST /api/v1/tasks/3/dependencies with body {"blocking_task_id": 1}
    Means: Task 3 is blocked by Task 1 (Task 1 must complete before Task 3 can proceed)
    """
    # Validate tasks exist
    blocking_task = db.query(Task).filter(Task.id == dependency.blocking_task_id).first()
    blocked_task = db.query(Task).filter(Task.id == task_id).first()
    
    if not blocking_task or not blocked_task:
        raise HTTPException(status_code=404, detail="One or both tasks not found")
    
    # Prevent self-dependency
    if dependency.blocking_task_id == task_id:
        raise HTTPException(status_code=400, detail="A task cannot depend on itself")
    
    # Check if dependency already exists
    existing = db.query(TaskDependency).filter(
        TaskDependency.blocking_task_id == dependency.blocking_task_id,
        TaskDependency.blocked_task_id == task_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Dependency already exists")
    
    # Create dependency
    db_dependency = TaskDependency(
        blocking_task_id=dependency.blocking_task_id,
        blocked_task_id=task_id  # Use task_id from path parameter
    )
    db.add(db_dependency)
    
    # Log history
    log_task_history(db, task_id, current_user.id, "dependency_added",
                    "blocking_task", None, str(dependency.blocking_task_id))
    
    db.commit()
    db.refresh(db_dependency)
    return db_dependency


@router.delete("/dependencies/{dependency_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task_dependency(
    dependency_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a task dependency"""
    dependency = db.query(TaskDependency).filter(TaskDependency.id == dependency_id).first()
    if not dependency:
        raise HTTPException(status_code=404, detail="Dependency not found")
    
    # Log history
    log_task_history(db, dependency.blocked_task_id, current_user.id, "dependency_removed",
                    "blocking_task", str(dependency.blocking_task_id), None)
    
    db.delete(dependency)
    db.commit()
    return None



