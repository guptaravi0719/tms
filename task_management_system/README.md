# Task management system

## 🚀 Setup Instructions

### Option 1: Using Docker (Recommended)

#### Step 1: Navigate to project directory
```bash
cd /home/delhivery/Development/task_management_system
```

#### Step 2: Build and run with Docker Compose
```bash
docker compose up --build -d
```

That's it! The API will be running in the background at `http://localhost:8000`

#### Step 3: View logs
```bash
docker compose logs -f
```

Press `Ctrl+C` to exit log view (containers keep running).

#### Step 4: Access the API Documentation
- Swagger UI: http://localhost:8000/docs

#### Step 5: Stop the services
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
