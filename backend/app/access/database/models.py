"""
SQLAlchemy ORM Models for AI Data Agent.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.access.database.connection import Base


class UserAccount(Base):
    """用户账号表"""
    __tablename__ = "user_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    login_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="employee")
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    business_line: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    quota: Mapped["UserQuota"] = relationship("UserQuota", back_populates="user", uselist=False)
    conversations: Mapped[List["Conversation"]] = relationship("Conversation", back_populates="user")


class UserQuota(Base):
    """用户配额表"""
    __tablename__ = "user_quotas"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_accounts.id"))
    daily_limit: Mapped[int] = mapped_column(Integer, default=100)
    current_balance: Mapped[int] = mapped_column(Integer, default=100)
    last_reset: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    user: Mapped["UserAccount"] = relationship("UserAccount", back_populates="quota")


class CreditLog(Base):
    """积分消耗日志"""
    __tablename__ = "credit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    credits_deducted: Mapped[int] = mapped_column(Integer, default=0)
    balance_after: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Conversation(Base):
    """对话历史"""
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("user_accounts.id"), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    user: Mapped[Optional["UserAccount"]] = relationship("UserAccount", back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """消息记录"""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # 关系
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")


class UserApiConfig(Base):
    """用户级API配置"""
    __tablename__ = "user_api_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    api_config_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    custom_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ==================== API Permission Models ====================

class APICategory(Base):
    """API 分类树模型 - 映射 api_categories 表"""
    __tablename__ = "api_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("api_categories.id"), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 自引用关系 - 父分类
    parent: Mapped[Optional["APICategory"]] = relationship(
        "APICategory", remote_side=[id], backref="children"
    )

    # 关联的 API 配置
    apis: Mapped[List["APIConfig"]] = relationship(
        "APIConfig", back_populates="category"
    )

    def get_path(self) -> str:
        """获取分类完整路径（如：根分类 > 子分类 > 当前分类）"""
        if self.parent:
            return f"{self.parent.get_path()} > {self.name}"
        return self.name


class APIConfig(Base):
    """API 配置模型 - 映射 api_configs 表"""
    __tablename__ = "api_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    auth_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    auth_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    endpoints: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timeout: Mapped[int] = mapped_column(Integer, default=30)
    retry_count: Mapped[int] = mapped_column(Integer, default=3)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("api_categories.id"), nullable=True)
    auth_fields: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    owner_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 关联分类
    category: Mapped[Optional["APICategory"]] = relationship(
        "APICategory", back_populates="apis"
    )

    # 关联权限记录
    permissions: Mapped[List["UserAPIPermission"]] = relationship(
        "UserAPIPermission", back_populates="api_config"
    )

    # 关联调用日志
    call_logs: Mapped[List["APICallLog"]] = relationship(
        "APICallLog", back_populates="api_config"
    )


class UserAPIPermission(Base):
    """用户 API 权限模型 - 映射 user_api_permissions 表"""
    __tablename__ = "user_api_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    api_config_id: Mapped[int] = mapped_column(Integer, ForeignKey("api_configs.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(20), default="admin")  # admin, self, etc.
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending, active, disabled
    auth_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    custom_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    disabled_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    disabled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    disabled_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    granted_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联 API 配置
    api_config: Mapped["APIConfig"] = relationship(
        "APIConfig", back_populates="permissions"
    )

    @property
    def is_active(self) -> bool:
        """检查权限是否有效"""
        return self.status == "active"


class APICallLog(Base):
    """API 调用日志模型 - 映射 api_call_logs 表"""
    __tablename__ = "api_call_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    api_config_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("api_configs.id"), nullable=True, index=True)
    permission_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    conversation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    called_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)

    # 关联 API 配置
    api_config: Mapped[Optional["APIConfig"]] = relationship(
        "APIConfig", back_populates="call_logs"
    )


# Backward compatibility alias
ApiConfig = APIConfig