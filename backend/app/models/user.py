"""
User model for authentication and authorization.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Base user model."""
    user_id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., description="Username")
    email: Optional[str] = Field(None, description="User email")
    department: Optional[str] = Field(None, description="User department")
    business_line: Optional[str] = Field(None, description="User business line")


class User(UserBase):
    """Full user model with all properties."""
    role: str = Field(default="employee", description="User role: employee, manager, executive")
    data_scope: str = Field(default="department", description="Data scope: department, business_line, company")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """User creation model."""
    user_id: str
    username: str
    email: Optional[str] = None
    department: Optional[str] = None
    business_line: Optional[str] = None
    role: str = "employee"


class UserRegister(BaseModel):
    """User registration model for self-registration."""
    login_id: str = Field(..., description="Login ID (account name)")
    username: str = Field(..., description="Display name")
    password: str = Field(..., description="User password")


class UserContext(BaseModel):
    """
    User context for request processing.
    Contains user info and permissions for data access.
    """
    user_id: str
    username: str
    role: str = "employee"
    data_scope: str = "department"
    department: Optional[str] = None
    business_line: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    filters: dict = Field(default_factory=dict)

    class Config:
        from_attributes = True


class UserInDB(User):
    """User model stored in database."""
    hashed_password: Optional[str] = None
    is_active: bool = True
    last_login: Optional[datetime] = None


class UserQuota(BaseModel):
    """User quota information."""
    daily_limit: int = Field(default=100, description="Daily credit limit, -1 means unlimited")
    current_balance: int = Field(default=100, description="Current credit balance")
    last_reset: datetime = Field(default_factory=datetime.now, description="Last quota reset time")


class CreditTransaction(BaseModel):
    """Credit transaction record."""
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: str
    session_id: Optional[str] = None
    query: str  # The user's question
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    credits_deducted: int = 0
    balance_after: int = 0


class UserAccount(BaseModel):
    """User account with quota and settings."""
    user_id: str
    login_id: str = ""
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    password: str  # In production, use hashed password
    role: str = "employee"
    department: Optional[str] = None
    business_line: Optional[str] = None
    auth_type: str = "local"  # local / cia
    is_active: bool = True
    quota: UserQuota = Field(default_factory=UserQuota)
    # User's accessible API IDs (empty list means all system APIs)
    user_apis: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True

    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == "admin"

    def has_unlimited_credits(self) -> bool:
        """Check if user has unlimited credits (admin)."""
        return self.role == "admin" or self.quota.daily_limit == -1