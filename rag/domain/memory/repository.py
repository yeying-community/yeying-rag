from typing import Optional, List

from rag.domain.models import MemoryDO


class MemoryRepository:
    """内存数据访问层"""
    
    def save(self, memory: MemoryDO) -> MemoryDO:
        """
        保存记忆体
        
        Args:
            memory: 记忆体对象
            
        Returns:
            MemoryDO: 保存后的记忆体对象
        """
        memory.save()
        return memory
    
    def get_by_id(self, memory_id: str) -> Optional[MemoryDO]:
        """
        根据主键ID获取记忆体
        
        Args:
            memory_id: 主键ID
            
        Returns:
            Optional[MemoryDO]: 记忆体对象，如果不存在则返回None
        """
        try:
            return MemoryDO.get(MemoryDO.id == memory_id)
        except MemoryDO.DoesNotExist:
            return None
    
    def get_by_memory_id(self, memory_id: str) -> Optional[MemoryDO]:
        """
        根据记忆体ID获取记忆体
        
        Args:
            memory_id: 记忆体ID
            
        Returns:
            Optional[MemoryDO]: 记忆体对象，如果不存在则返回None
        """
        try:
            return MemoryDO.get(MemoryDO.memory_id == memory_id)
        except MemoryDO.DoesNotExist:
            return None
    
    def get_by_domain(self, domain: str) -> List[MemoryDO]:
        """
        根据域名获取记忆体列表
        
        Args:
            domain: 域名标识
            
        Returns:
            List[MemoryDO]: 记忆体对象列表
        """
        return list(MemoryDO.select().where(MemoryDO.domain == domain))
    
    def delete_by_memory_id(self, memory_id: str) -> bool:
        """
        根据记忆体ID删除记忆体
        
        Args:
            memory_id: 记忆体ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            memory = MemoryDO.get(MemoryDO.memory_id == memory_id)
            memory.delete_instance()
            return True
        except MemoryDO.DoesNotExist:
            return False
    
    def update(self, memory: MemoryDO) -> MemoryDO:
        """
        更新记忆体
        
        Args:
            memory: 记忆体对象
            
        Returns:
            MemoryDO: 更新后的记忆体对象
        """
        memory.save()
        return memory