#!/usr/bin/env python3
"""
HTTP代理服务器实现
兼容Clash客户端的HTTP代理协议
"""

import asyncio
import logging
import time
import base64
from typing import Optional, Dict, Any, Tuple
import re

class HTTPProxyServer:
    """HTTP代理服务器"""
    
    def __init__(self, host: str, port: int, username: str = None, 
                 password: str = None, timeout: int = 300, stats: Any = None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.stats = stats
        
        # 服务器状态
        self.server = None
        self.running = False
        self.connections: Dict[str, Any] = {}
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """启动HTTP代理服务器"""
        try:
            self.server = await asyncio.start_server(
                self._handle_client,
                self.host,
                self.port
            )
            
            self.running = True
            auth_info = "需要认证" if self.username else "无需认证"
            self.logger.info(f"🌐 HTTP代理服务器启动: {self.host}:{self.port} ({auth_info})")
            
            async with self.server:
                await self.server.serve_forever()
                
        except Exception as e:
            self.logger.error(f"HTTP代理服务器启动失败: {e}")
            raise
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """处理客户端连接"""
        client_addr = writer.get_extra_info('peername')
        connection_id = f"{client_addr[0]}:{client_addr[1]}"
        start_time = time.time()
        
        self.logger.info(f"新的HTTP代理连接: {client_addr}")
        
        try:
            # 读取HTTP请求
            request_data = await asyncio.wait_for(reader.read(4096), timeout=10)
            if not request_data:
                return
            
            request_text = request_data.decode('utf-8', errors='ignore')
            request_lines = request_text.split('\r\n')
            
            if not request_lines:
                return
            
            # 解析请求行
            first_line = request_lines[0]
            if not first_line:
                return
            
            # 检查认证
            if self.username and self.password:
                if not self._check_auth(request_lines):
                    await self._send_auth_required(writer)
                    return
            
            # 处理不同类型的请求
            if first_line.startswith('CONNECT'):
                # HTTPS代理请求
                await self._handle_connect_request(reader, writer, first_line, client_addr)
            else:
                # HTTP代理请求
                await self._handle_http_request(reader, writer, request_data, client_addr)
                
        except asyncio.TimeoutError:
            self.logger.warning(f"HTTP代理连接超时: {client_addr}")
        except Exception as e:
            self.logger.error(f"HTTP代理连接处理错误: {e}")
        finally:
            # 清理连接
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass
            
            if connection_id in self.connections:
                conn_info = self.connections[connection_id]
                duration = time.time() - conn_info['start_time']
                self.logger.info(f"HTTP代理连接关闭: {client_addr}, 时长: {duration:.1f}s")
                del self.connections[connection_id]
            
            if self.stats:
                self.stats.remove_connection('http', client_addr)
    
    def _check_auth(self, request_lines: list) -> bool:
        """检查HTTP代理认证"""
        for line in request_lines:
            if line.lower().startswith('proxy-authorization:'):
                auth_header = line.split(':', 1)[1].strip()
                if auth_header.lower().startswith('basic '):
                    try:
                        # 解码Basic认证
                        encoded_credentials = auth_header[6:]  # 去掉"Basic "
                        decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
                        username, password = decoded_credentials.split(':', 1)
                        
                        return username == self.username and password == self.password
                    except:
                        return False
        return False
    
    async def _send_auth_required(self, writer: asyncio.StreamWriter):
        """发送认证要求响应"""
        response = (
            "HTTP/1.1 407 Proxy Authentication Required\r\n"
            "Proxy-Authenticate: Basic realm=\"Proxy\"\r\n"
            "Content-Length: 0\r\n"
            "\r\n"
        )
        writer.write(response.encode())
        await writer.drain()
    
    async def _handle_connect_request(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, 
                                    first_line: str, client_addr: tuple):
        """处理CONNECT请求（HTTPS代理）"""
        try:
            # 解析CONNECT请求
            parts = first_line.split()
            if len(parts) < 2:
                return
            
            host_port = parts[1]
            if ':' in host_port:
                host, port = host_port.split(':', 1)
                port = int(port)
            else:
                host = host_port
                port = 443
            
            self.logger.info(f"HTTPS代理连接目标: {host}:{port}")
            
            # 连接目标服务器
            try:
                target_reader, target_writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=10
                )
                
                # 发送成功响应
                response = "HTTP/1.1 200 Connection Established\r\n\r\n"
                writer.write(response.encode())
                await writer.drain()
                
                # 记录连接
                connection_id = f"{client_addr[0]}:{client_addr[1]}"
                self.connections[connection_id] = {
                    'client_addr': client_addr,
                    'target_addr': (host, port),
                    'start_time': time.time()
                }
                
                if self.stats:
                    self.stats.add_connection('http', client_addr, (host, port))
                
                # 双向数据转发
                await asyncio.gather(
                    self._forward_data(reader, target_writer, "client->target"),
                    self._forward_data(target_reader, writer, "target->client"),
                    return_exceptions=True
                )
                
            except Exception as e:
                self.logger.error(f"连接目标服务器失败: {host}:{port} - {e}")
                response = "HTTP/1.1 502 Bad Gateway\r\n\r\n"
                writer.write(response.encode())
                await writer.drain()
                
        except Exception as e:
            self.logger.error(f"处理CONNECT请求错误: {e}")
    
    async def _handle_http_request(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                                 request_data: bytes, client_addr: tuple):
        """处理HTTP请求"""
        try:
            request_text = request_data.decode('utf-8', errors='ignore')
            request_lines = request_text.split('\r\n')
            
            # 解析请求行
            first_line = request_lines[0]
            method, url, version = first_line.split()
            
            # 解析URL
            if url.startswith('http://'):
                url = url[7:]  # 去掉http://
                if '/' in url:
                    host_port, path = url.split('/', 1)
                    path = '/' + path
                else:
                    host_port = url
                    path = '/'
            else:
                # 相对URL，从Host头获取主机
                host_port = None
                path = url
                for line in request_lines[1:]:
                    if line.lower().startswith('host:'):
                        host_port = line.split(':', 1)[1].strip()
                        break
                
                if not host_port:
                    response = "HTTP/1.1 400 Bad Request\r\n\r\n"
                    writer.write(response.encode())
                    await writer.drain()
                    return
            
            # 解析主机和端口
            if ':' in host_port:
                host, port = host_port.split(':', 1)
                port = int(port)
            else:
                host = host_port
                port = 80
            
            self.logger.info(f"HTTP代理请求: {method} {host}:{port}{path}")
            
            # 连接目标服务器
            try:
                target_reader, target_writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=10
                )
                
                # 重建HTTP请求
                new_request_lines = [f"{method} {path} {version}"]
                
                # 过滤和修改头部
                for line in request_lines[1:]:
                    if line.strip():
                        header_name = line.split(':', 1)[0].lower()
                        if header_name not in ['proxy-authorization', 'proxy-connection']:
                            if header_name == 'connection':
                                new_request_lines.append('Connection: close')
                            else:
                                new_request_lines.append(line)
                
                # 确保有Connection: close头部
                if not any('connection:' in line.lower() for line in new_request_lines):
                    new_request_lines.append('Connection: close')
                
                new_request_lines.append('')  # 空行
                new_request = '\r\n'.join(new_request_lines) + '\r\n'
                
                # 发送请求到目标服务器
                target_writer.write(new_request.encode())
                await target_writer.drain()
                
                # 记录连接
                connection_id = f"{client_addr[0]}:{client_addr[1]}"
                self.connections[connection_id] = {
                    'client_addr': client_addr,
                    'target_addr': (host, port),
                    'start_time': time.time()
                }
                
                if self.stats:
                    self.stats.add_connection('http', client_addr, (host, port))
                
                # 转发响应
                while True:
                    data = await asyncio.wait_for(target_reader.read(8192), timeout=self.timeout)
                    if not data:
                        break
                    
                    writer.write(data)
                    await writer.drain()
                    
                    # 更新统计
                    if self.stats:
                        self.stats.add_traffic('http', 0, len(data))
                
                target_writer.close()
                await target_writer.wait_closed()
                
            except Exception as e:
                self.logger.error(f"HTTP代理请求失败: {host}:{port} - {e}")
                response = "HTTP/1.1 502 Bad Gateway\r\n\r\n"
                writer.write(response.encode())
                await writer.drain()
                
        except Exception as e:
            self.logger.error(f"处理HTTP请求错误: {e}")
    
    async def _forward_data(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, direction: str):
        """转发数据"""
        try:
            while True:
                data = await asyncio.wait_for(reader.read(8192), timeout=self.timeout)
                if not data:
                    break
                
                writer.write(data)
                await writer.drain()
                
                # 更新统计
                if self.stats:
                    if "client" in direction:
                        self.stats.add_traffic('http', len(data), 0)
                    else:
                        self.stats.add_traffic('http', 0, len(data))
                        
        except asyncio.TimeoutError:
            self.logger.debug(f"HTTP代理数据转发超时: {direction}")
        except Exception as e:
            self.logger.debug(f"HTTP代理数据转发错误 {direction}: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass
    
    async def stop(self):
        """停止服务器"""
        self.running = False
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        self.connections.clear()
        self.logger.info("HTTP代理服务器已停止")
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        return {
            'protocol': 'http',
            'host': self.host,
            'port': self.port,
            'auth_required': bool(self.username),
            'running': self.running,
            'connections': len(self.connections),
            'total_traffic': getattr(self.stats, 'get_traffic', lambda: (0, 0))() if self.stats else (0, 0)
        }

# 测试函数
async def test_http_server():
    """测试HTTP代理服务器"""
    print("🧪 测试HTTP代理服务器...")
    
    # 创建服务器
    server = HTTPProxyServer(
        host='127.0.0.1',
        port=8080,
        username='test',
        password='pass'
    )
    
    print(f"✅ HTTP代理服务器创建成功")
    print(f"   监听地址: {server.host}:{server.port}")
    print(f"   认证: {server.username}:{server.password}")

if __name__ == "__main__":
    asyncio.run(test_http_server())