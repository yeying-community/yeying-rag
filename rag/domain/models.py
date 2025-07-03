# 导入必要的模块
from datetime import datetime
from peewee import CharField, DateTimeField
import uuid
from rag.infrastructure.database.instance import BaseModel


# =================数据库架构迁移模型=================
class SchemaMigrationDO(BaseModel):
    """数据库架构迁移跟踪表 - 记录数据库版本变更历史"""
    version = CharField(max_length=50, help_text="版本号")  # 数据库架构版本标识
    created_at = DateTimeField(default=datetime.now, help_text="创建时间")  # 迁移执行时间

    class Meta:
        table_name = 'schema_migrations'


# =================记忆数据模型=================
class MemoryDO(BaseModel):
    """记忆数据对象 - 存储RAG系统的记忆信息"""
    
    # 主键：使用CHAR(36)存储UUID
    id = CharField(max_length=36, primary_key=True, default=lambda: str(uuid.uuid4()), help_text="主键ID（UUID）")
    
    # 域名标识
    domain = CharField(max_length=32, default='interviewer', help_text="域名标识")
    
    # RAG返回的记忆ID（唯一约束）
    memory_id = CharField(max_length=128, unique=True, help_text="RAG返回的记忆ID")
    
    # 时间戳
    created_at = DateTimeField(default=datetime.now, help_text="创建时间")

    class Meta:
        table_name = 'memory'
        # 创建索引优化查询性能
        indexes = (
            # 按域名查询记忆（非唯一索引）
            (('domain',), False),
            # memory_id唯一索引
            (('memory_id',), True),
        )


# =================模型导出=================
# 导出当前已实现的模型供数据库迁移使用
ALL_MODELS = [
    SchemaMigrationDO,    # 架构迁移表（系统核心）
    MemoryDO,             # 记忆表（核心业务）
]