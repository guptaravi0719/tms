# Task Management System API


## Product Features (3 Chosen)

### 1. **Filtering Tasks by Multiple Criteria (Status, Priority, Assignee, Dates, Tags) using AND/OR Logic**

**Why this is important:**

**Core functionality** of any task management system

**Shows practical backend complexity:**
- Dynamic query building
- Handling combinational filters
- Validating input

**Demonstrates real-world product value:** Teams need advanced filtering to find tasks instantly

**What interviewers love about this:**
- Query optimization skills
- Clean API design
- Backend data modeling expertise

**This is a must-choose feature** - it separates basic CRUD from production-grade systems.

**Capabilities Implemented:**
- Filter by status, priority, assignee, creator, tags
- Date range filtering (due dates, created dates)
- Search in title and description
- Overdue tasks filtering
- Subtask filtering
- Combine filters with AND/OR logic for maximum flexibility

---

### 2. **Making Tasks Depend on Other Tasks (Task Blocking)**

**Why this is important:**
**Adds significant business value:**
- Teams can visualize work dependencies
- Prevent starting tasks before prerequisites complete

**From engineering perspective:**
- Graph relationships (DAG-like structure)
- Prevent cyclic dependencies
- Validation rules
- Extra status logic ("blocked", "unblocked")

**Shows you understand workflow management, not just CRUD.**

This feature displays **strong systems thinking** and understanding of real project management workflows.

**Capabilities Implemented:**
- Define which tasks block other tasks
- Prevent circular dependencies
- View all blocking and blocked relationships
- Automatic validation and error handling
- Track dependency changes in audit trail

---

### 3. **Timeline of Task Changes Relevant to a User in the Last N Days**

**Why this is important:**

**Shows event tracking, audit logs, user activity feed**

**Demonstrates engineering maturity:**
- Storing deltas (what changed, when, by whom)
- Efficient querying by user + date range
- Returning a chronological feed

**High-value "smart" feature** used in modern products like Jira, Linear, Asana

**What this proves:**
- Understanding of audit trail systems
- Efficient time-series querying
- User-centric data filtering
- Production-ready logging architecture

**Capabilities Implemented:**
- Track all task changes (create, update, status changes, assignments)
- Store old and new values for each change
- Query by user involvement (created by or assigned to)
- Filter by date range (last N days)
- Includes user information for each change

## 🚀 Setup Instructions

### Using Docker (Recommended)

#### Step 1: Navigate to project directory
```bash
cd /home/delhivery/Development/task_management_system
```

#### Step 2: Build and start services
```bash
docker compose up --build -d
```

The API will be running at `http://localhost:8000`

#### Step 3: View logs
```bash
docker compose logs -f
```

Press `Ctrl+C` to exit log view (containers keep running).

#### Step 4: Access API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

#### Step 5: Stop services
```bash
docker compose down
```

To remove all data (including database):
```bash
docker compose down -v
```

To restart services:
```bash
docker compose restart
```
