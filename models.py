from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

Base = declarative_base()

class Server(Base):
    __tablename__ = "servers"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)
    ip_address = Column(String, nullable=False)
    fqdn = Column(String)
    os = Column(String)
    os_version = Column(String)
    environment = Column(String)  # prod/staging/dev
    location = Column(String)
    cpu_cores = Column(Integer)
    memory_gb = Column(Integer)
    disk_gb = Column(Integer)
    owner_user_id = Column(String, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    status = Column(String, default="unknown")  # up/down/maintenance/unknown
    last_seen = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    tags = Column(Text)  # JSON string of tags
    notes = Column(Text)
    
    # Relationships
    owner = relationship("User", back_populates="servers")
    access_logs = relationship("AccessLog", back_populates="server")

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    role = Column(String, default="user")  # admin/user/readonly
    department = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    servers = relationship("Server", back_populates="owner")
    access_logs = relationship("AccessLog", back_populates="user")

class AccessLog(Base):
    __tablename__ = "access_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    server_id = Column(String, ForeignKey("servers.id"))
    action = Column(String, nullable=False)  # query/view/connect/etc
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(Text)  # JSON string with additional info
    ip_address = Column(String)
    
    # Relationships
    user = relationship("User", back_populates="access_logs")
    server = relationship("Server", back_populates="access_logs")
