import uuid
from typing import Optional

from rag.domain.memory.repository import MemoryRepository
from rag.domain.models import MemoryDO


class MemoryService:
    """内存管理应用服务"""
    
    def __init__(self, memory_repository: MemoryRepository):
        self.memory_repository = memory_repository
    
    def create_memory(self, domain: str) -> str:
        """
        创建记忆体
        
        Args:
            domain: 域名标识（如 "interviewer"）
            
        Returns:
            str: 生成的记忆体ID
        """
        # 生成唯一的记忆体ID
        memory_id = str(uuid.uuid4())
        
        # 创建记忆体记录
        memory_record = MemoryDO(
            domain=domain,
            memory_id=memory_id
        )
        
        # 保存到数据库
        self.memory_repository.save(memory_record)
        
        return memory_id
    
    def add_content(self, memory_id: str, url: str) -> None:
        """
        添加内容到记忆体
        
        Args:
            memory_id: 记忆体ID
            url: 要添加的内容URL
        """
        # 验证记忆体是否存在
        memory = self.memory_repository.get_by_memory_id(memory_id)
        if not memory:
            raise ValueError(f"Memory not found: {memory_id}")
        
        # TODO: 实现URL内容的处理和存储
        # 这里应该包含：
        # 1. 获取URL内容
        # 2. 内容处理和向量化
        # 3. 存储到向量数据库
        print(f"Adding content to memory {memory_id}: {url}")
    
    def delete_content(self, memory_id: str, url: str) -> None:
        """
        删除记忆体中的内容
        
        Args:
            memory_id: 记忆体ID
            url: 要删除的内容URL
        """
        # 验证记忆体是否存在
        memory = self.memory_repository.get_by_memory_id(memory_id)
        if not memory:
            raise ValueError(f"Memory not found: {memory_id}")
        
        # TODO: 实现URL内容的删除
        # 这里应该包含：
        # 1. 从向量数据库中删除对应的内容
        # 2. 清理相关的索引
        print(f"Deleting content from memory {memory_id}: {url}")
    
    def get_memory_by_id(self, memory_id: str) -> Optional[MemoryDO]:
        """
        根据记忆体ID获取记忆体
        
        Args:
            memory_id: 记忆体ID
            
        Returns:
            Optional[MemoryDO]: 记忆体对象，如果不存在则返回None
        """
        return self.memory_repository.get_by_memory_id(memory_id)