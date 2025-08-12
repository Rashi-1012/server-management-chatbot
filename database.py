from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Server, User, AccessLog
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
import random

load_dotenv()

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./server_inventory.db")
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_sample_data():
    """Create sample data for Chennai server and VMs"""
    db = SessionLocal()
    
    # Check if data already exists
    if db.query(Server).first():
        print("Sample data already exists!")
        db.close()
        return
    
    # Create sample users
    users_data = [
        {"name": "Raja", "email": "raja@company.com", "role": "admin", "department": "DevOps"},
        {"name": "Rasheed", "email": "rasheed@company.com", "role": "user", "department": "Development"},
        {"name": "Arjun", "email": "arjun@company.com", "role": "user", "department": "QA"},
        {"name": "Meera", "email": "meera@company.com", "role": "user", "department": "Development"},
        {"name": "Karthik", "email": "karthik@company.com", "role": "admin", "department": "Infrastructure"},
    ]
    
    users = []
    for user_data in users_data:
        user = User(**user_data)
        db.add(user)
        users.append(user)
    
    db.commit()
    
    # Create Chennai main server
    chennai_server = Server(
        name="chennai-main-01",
        ip_address="10.10.1.1",
        fqdn="chennai-main-01.company.local",
        os="Ubuntu Server",
        os_version="22.04 LTS",
        environment="production",
        location="Chennai Data Center",
        cpu_cores=64,
        memory_gb=256,
        disk_gb=2000,
        owner_user_id=users[0].id,
        status="up",
        last_seen=datetime.utcnow(),
        tags=json.dumps(["hypervisor", "production", "critical"]),
        notes="Main hypervisor server hosting all Chennai VMs"
    )
    db.add(chennai_server)
    
    # Create sample VMs on Chennai server
    vm_templates = [
        {"name": "web", "os": "Ubuntu", "env": "production", "purpose": "Web Server"},
        {"name": "db", "os": "PostgreSQL", "env": "production", "purpose": "Database Server"},
        {"name": "api", "os": "Ubuntu", "env": "production", "purpose": "API Gateway"},
        {"name": "cache", "os": "Redis", "env": "production", "purpose": "Cache Server"},
        {"name": "monitoring", "os": "Ubuntu", "env": "production", "purpose": "Monitoring"},
        {"name": "backup", "os": "Ubuntu", "env": "production", "purpose": "Backup Server"},
        {"name": "test-web", "os": "Ubuntu", "env": "staging", "purpose": "Test Web Server"},
        {"name": "test-db", "os": "PostgreSQL", "env": "staging", "purpose": "Test Database"},
        {"name": "dev-env", "os": "Ubuntu", "env": "development", "purpose": "Development Environment"},
        {"name": "ci-cd", "os": "Ubuntu", "env": "production", "purpose": "CI/CD Pipeline"},
    ]
    
    servers = []
    for i, template in enumerate(vm_templates):
        # Random status with mostly up servers
        status_options = ["up", "up", "up", "up", "down", "maintenance"]
        status = random.choice(status_options)
        
        # Random last seen time
        if status == "up":
            last_seen = datetime.utcnow() - timedelta(minutes=random.randint(1, 30))
        elif status == "down":
            last_seen = datetime.utcnow() - timedelta(hours=random.randint(1, 24))
        else:
            last_seen = datetime.utcnow() - timedelta(minutes=random.randint(5, 120))
        
        server = Server(
            name=f"chennai-{template['name']}-{i+1:02d}",
            ip_address=f"10.10.2.{i+10}",
            fqdn=f"chennai-{template['name']}-{i+1:02d}.company.local",
            os=template['os'],
            os_version="22.04 LTS" if "Ubuntu" in template['os'] else "Latest",
            environment=template['env'],
            location="Chennai Data Center",
            cpu_cores=random.choice([2, 4, 8, 16]),
            memory_gb=random.choice([4, 8, 16, 32]),
            disk_gb=random.choice([50, 100, 200, 500]),
            owner_user_id=random.choice(users).id,
            status=status,
            last_seen=last_seen,
            tags=json.dumps([template['env'], template['purpose'].lower().replace(' ', '-'), "vm"]),
            notes=f"Virtual machine for {template['purpose']}"
        )
        db.add(server)
        servers.append(server)
    
    db.commit()
    
    # Create some sample access logs
    for _ in range(50):
        log = AccessLog(
            user_id=random.choice(users).id,
            server_id=random.choice(servers + [chennai_server]).id,
            action=random.choice(["query", "view", "connect", "status_check"]),
            timestamp=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
            details=json.dumps({"source": "chatbot", "success": True}),
            ip_address=f"192.168.1.{random.randint(100, 200)}"
        )
        db.add(log)
    
    db.commit()
    db.close()
    print("Sample data created successfully!")

if __name__ == "__main__":
    create_tables()
    seed_sample_data()
