from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db, create_tables, seed_sample_data
from models import Server, User, AccessLog
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime

app = FastAPI(title="Server Management API", version="1.0.0")

# Pydantic models for API responses
class ServerResponse(BaseModel):
    id: str
    name: str
    ip_address: str
    fqdn: Optional[str]
    os: Optional[str]
    os_version: Optional[str]
    environment: Optional[str]
    location: Optional[str]
    cpu_cores: Optional[int]
    memory_gb: Optional[int]
    disk_gb: Optional[int]
    status: str
    last_seen: datetime
    owner_name: Optional[str]
    tags: List[str]
    notes: Optional[str]

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    department: Optional[str]

    class Config:
        from_attributes = True

class ServerSummary(BaseModel):
    total_servers: int
    active_servers: int
    servers_up: int
    servers_down: int
    servers_maintenance: int
    environments: dict

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    seed_sample_data()

@app.get("/")
async def root():
    return {"message": "Server Management API is running!"}

@app.get("/api/servers", response_model=List[ServerResponse])
async def get_servers(
    environment: Optional[str] = Query(None, description="Filter by environment"),
    status: Optional[str] = Query(None, description="Filter by status"),
    location: Optional[str] = Query(None, description="Filter by location"),
    search: Optional[str] = Query(None, description="Search in name, IP, or notes"),
    db: Session = Depends(get_db)
):
    """Get all servers with optional filtering"""
    query = db.query(Server)
    
    if environment:
        query = query.filter(Server.environment == environment)
    if status:
        query = query.filter(Server.status == status)
    if location:
        query = query.filter(Server.location.contains(location))
    if search:
        query = query.filter(
            (Server.name.contains(search)) |
            (Server.ip_address.contains(search)) |
            (Server.notes.contains(search))
        )
    
    servers = query.all()
    
    # Format response
    result = []
    for server in servers:
        owner_name = None
        if server.owner:
            owner_name = server.owner.name
        
        tags = []
        if server.tags:
            try:
                tags = json.loads(server.tags)
            except:
                tags = []
        
        result.append(ServerResponse(
            id=server.id,
            name=server.name,
            ip_address=server.ip_address,
            fqdn=server.fqdn,
            os=server.os,
            os_version=server.os_version,
            environment=server.environment,
            location=server.location,
            cpu_cores=server.cpu_cores,
            memory_gb=server.memory_gb,
            disk_gb=server.disk_gb,
            status=server.status,
            last_seen=server.last_seen,
            owner_name=owner_name,
            tags=tags,
            notes=server.notes
        ))
    
    return result

@app.get("/api/servers/{server_id}", response_model=ServerResponse)
async def get_server(server_id: str, db: Session = Depends(get_db)):
    """Get a specific server by ID"""
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    owner_name = None
    if server.owner:
        owner_name = server.owner.name
    
    tags = []
    if server.tags:
        try:
            tags = json.loads(server.tags)
        except:
            tags = []
    
    return ServerResponse(
        id=server.id,
        name=server.name,
        ip_address=server.ip_address,
        fqdn=server.fqdn,
        os=server.os,
        os_version=server.os_version,
        environment=server.environment,
        location=server.location,
        cpu_cores=server.cpu_cores,
        memory_gb=server.memory_gb,
        disk_gb=server.disk_gb,
        status=server.status,
        last_seen=server.last_seen,
        owner_name=owner_name,
        tags=tags,
        notes=server.notes
    )

@app.get("/api/servers/name/{server_name}", response_model=ServerResponse)
async def get_server_by_name(server_name: str, db: Session = Depends(get_db)):
    """Get a specific server by name"""
    server = db.query(Server).filter(Server.name == server_name).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    owner_name = None
    if server.owner:
        owner_name = server.owner.name
    
    tags = []
    if server.tags:
        try:
            tags = json.loads(server.tags)
        except:
            tags = []
    
    return ServerResponse(
        id=server.id,
        name=server.name,
        ip_address=server.ip_address,
        fqdn=server.fqdn,
        os=server.os,
        os_version=server.os_version,
        environment=server.environment,
        location=server.location,
        cpu_cores=server.cpu_cores,
        memory_gb=server.memory_gb,
        disk_gb=server.disk_gb,
        status=server.status,
        last_seen=server.last_seen,
        owner_name=owner_name,
        tags=tags,
        notes=server.notes
    )

@app.get("/api/summary", response_model=ServerSummary)
async def get_summary(db: Session = Depends(get_db)):
    """Get server summary statistics"""
    total_servers = db.query(Server).count()
    active_servers = db.query(Server).filter(Server.is_active == True).count()
    servers_up = db.query(Server).filter(Server.status == "up").count()
    servers_down = db.query(Server).filter(Server.status == "down").count()
    servers_maintenance = db.query(Server).filter(Server.status == "maintenance").count()
    
    # Environment breakdown
    environments = {}
    env_counts = db.query(Server.environment, func.count(Server.id)).group_by(Server.environment).all()
    for env, count in env_counts:
        environments[env or "unknown"] = count
    
    return ServerSummary(
        total_servers=total_servers,
        active_servers=active_servers,
        servers_up=servers_up,
        servers_down=servers_down,
        servers_maintenance=servers_maintenance,
        environments=environments
    )

@app.get("/api/users", response_model=List[UserResponse])
async def get_users(db: Session = Depends(get_db)):
    """Get all users"""
    users = db.query(User).all()
    return [UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        department=user.department
    ) for user in users]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
