import grpc
from concurrent import futures
import uuid
from datetime import datetime

from yeying.api.rag import memory_pb2_grpc, memory_pb2
from yeying.api.common import message_pb2


class MemoryServicer(memory_pb2_grpc.MemoryServicer):
    """Memory服务的gRPC实现"""

    def __init__(self, memory_service):
        self.memory_service = memory_service

    def Create(self, request, context):
        """创建记忆体"""
        try:
            # 从请求中获取domain
            domain = request.body.domain
            
            # 调用应用层服务创建记忆体
            memory_id = self.memory_service.create_memory(domain)
            
            # 构造响应
            response = memory_pb2.CreateMemoryResponse()
            response.header.request_id = request.header.request_id
            response.header.timestamp = int(datetime.now().timestamp())
            
            response.body.status.code = 0
            response.body.status.message = "success"
            response.body.memory_id = memory_id
            
            return response
            
        except Exception as e:
            # 错误处理
            response = memory_pb2.CreateMemoryResponse()
            response.header.request_id = request.header.request_id
            response.header.timestamp = int(datetime.now().timestamp())
            
            response.body.status.code = -1
            response.body.status.message = str(e)
            
            return response

    def Add(self, request, context):
        """添加内容到记忆体"""
        try:
            # 从请求中获取参数
            memory_id = request.body.memory_id
            url = request.body.url
            
            # 调用应用层服务添加内容
            self.memory_service.add_content(memory_id, url)
            
            # 构造响应
            response = memory_pb2.AddMemoryResponse()
            response.header.request_id = request.header.request_id
            response.header.timestamp = int(datetime.now().timestamp())
            
            response.body.status.code = 0
            response.body.status.message = "success"
            
            return response
            
        except Exception as e:
            # 错误处理
            response = memory_pb2.AddMemoryResponse()
            response.header.request_id = request.header.request_id
            response.header.timestamp = int(datetime.now().timestamp())
            
            response.body.status.code = -1
            response.body.status.message = str(e)
            
            return response

    def Delete(self, request, context):
        """删除记忆体中的内容"""
        try:
            # 从请求中获取参数
            memory_id = request.body.memory_id
            url = request.body.url
            
            # 调用应用层服务删除内容
            self.memory_service.delete_content(memory_id, url)
            
            # 构造响应
            response = memory_pb2.DeleteMemoryResponse()
            response.header.request_id = request.header.request_id
            response.header.timestamp = int(datetime.now().timestamp())
            
            response.body.status.code = 0
            response.body.status.message = "success"
            
            return response
            
        except Exception as e:
            # 错误处理
            response = memory_pb2.DeleteMemoryResponse()
            response.header.request_id = request.header.request_id
            response.header.timestamp = int(datetime.now().timestamp())
            
            response.body.status.code = -1
            response.body.status.message = str(e)
            
            return response