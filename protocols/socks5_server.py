#!/usr/bin/env python3
"""
SOCKS5服务器实现
兼容Clash客户端的SOCKS5代理协议
"""

import asyncio
import socket
import struct
import logging
import time
from typing import Optional, Tuple, Dict, Any
import base64

class SOCKS5Error(Exception):
    """SOCKS5错误"""
    pass

class SOCKS5Server:
    """SOCKS5代理服务器"""
    
    # SOCKS5常量
    SOCKS_VERSION = 0x05
    
    # 认证方法
    AUTH_NO_AUTH = 0x00
    AUTH_USERNAME_PASSWORD = 0x02
    AUTH_NO_ACCEPTABLE = 0xFF
    
    # 命令类型
    CMD_CONNECT = 0x01
    CMD_BIND = 0x02
    CMD_UDP_ASSOCIATE = 0x03
    
    # 地址类型
    ADDR_IPV4 = 0x01
    ADDR_DOMAIN = 0x03
    ADDR_IPV6 = 0x04
    
    # 响应代码
    REP_SUCCESS = 0x00
    REP_GENERAL_FAILURE = 0x01
    REP_CONNECTION_NOT_ALLOWED = 0x02
    REP_NETWORK_UNREACHABLE = 0x03
    REP_HOST_UNREACHABLE = 0x04
    REP_CONNECTION_REFUSED = 0x05
    REP_TTL_EXPIRED = 0x06
    REP_COMMAND_NOT_SUPPORTED = 0x07
    REP_ADDRESS_TYPE_NOT_SUPPORTED = 0x08
    
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
        """启动SOCKS5服务器"""
        try:
            self.server = await asyncio.start_server(
                self._handle_client,
                self.host,
                self.port
            )
            
            self.running = True
            auth_info = "需要认证" if self.username else "无需认证"
            self.logger.info(f"🧦 SOCKS5服务器启动: {self.host}:{self.port} ({auth_info})")
            
            async with self.server:
                await self.server.serve_forever()
                
        except Exception as e:
            self.logger.error(f"SOCKS5服务器启动失败: {e}")
            raise
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """处理客户端连接"""
        client_addr = writer.get_extra_info('peername')
        connection_id = f"{client_addr[0]}:{client_addr[1]}"
        start_time = time.time()
        
        self.logger.info(f"新的SOCKS5连接: {client_addr}")
        
        try:
            # SOCKS5握手
            if not await self._handle_handshake(reader, writer):
                return
            
            # 处理连接请求
            target_reader, target_writer, target_addr = await self._handle_connect_request(reader, writer)
            if not target_reader:
                return
            
            # 记录连接
            self.connections[connection_id] = {
                'client_addr': client_addr,
                'target_addr': target_addr,
                'start_time': start_time
            }
            
            if self.stats:
                self.stats.add_connection('socks5', client_addr, target_addr)
            
            # 双向数据转发
            await asyncio.gather(
                self._forward_data(reader, target_writer, "client->target"),
                self._forward_data(target_reader, writer, "target->client"),
                return_exceptions=True
            )
            
        except Exception as e:
            self.logger.error(f"SOCKS5连接处理错误: {e}")
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
                self.logger.info(f"SOCKS5连接关闭: {client_addr} -> {conn_info.get('target_addr')}, 时长: {duration:.1f}s")
                del self.connections[connection_id]
            
            if self.stats:
                self.stats.remove_connection('socks5', client_addr)
    
    async def _handle_handshake(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> bool:
        """处理SOCKS5握手"""
        try:
            # 读取客户端握手请求
            data = await asyncio.wait_for(reader.read(2), timeout=10)
            if len(data) != 2:
                return False
            
            version, nmethods = struct.unpack('!BB', data)
            if version != self.SOCKS_VERSION:
                self.logger.warning(f"不支持的SOCKS版本: {version}")
                return False
            
            # 读取认证方法列表
            methods = await asyncio.wait_for(reader.read(nmethods), timeout=10)
            if len(methods) != nmethods:
                return False
            
            # 选择认证方法
            if self.username and self.password:
                # 需要用户名密码认证
                if self.AUTH_USERNAME_PASSWORD in methods:
                    # 发送认证方法选择响应
                    writer.write(struct.pack('!BB', self.SOCKS_VERSION, self.AUTH_USERNAME_PASSWORD))
                    await writer.drain()
                    
                    # 处理用户名密码认证
                    return await self._handle_username_password_auth(reader, writer)
                else:
                    # 客户端不支持用户名密码认证
                    writer.write(struct.pack('!BB', self.SOCKS_VERSION, self.AUTH_NO_ACCEPTABLE))
                    await writer.drain()
                    return False
            else:
                # 无需认证
                if self.AUTH_NO_AUTH in methods:
                    writer.write(struct.pack('!BB', self.SOCKS_VERSION, self.AUTH_NO_AUTH))
                    await writer.drain()
                    return True
                else:
                    writer.write(struct.pack('!BB', self.SOCKS_VERSION, self.AUTH_NO_ACCEPTABLE))
                    await writer.drain()
                    return False
                    
        except asyncio.TimeoutError:
            self.logger.warning("SOCKS5握手超时")
            return False
        except Exception as e:
            self.logger.error(f"SOCKS5握手错误: {e}")
            return False
    
    async def _handle_username_password_auth(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> bool:
        """处理用户名密码认证"""
        try:
            # 读取认证请求
            data = await asyncio.wait_for(reader.read(2), timeout=10)
            if len(data) != 2:
                return False
            
            version, username_len = struct.unpack('!BB', data)
            if version != 0x01:  # 用户名密码认证版本
                return False
            
            # 读取用户名
            username = await asyncio.wait_for(reader.read(username_len), timeout=10)
            if len(username) != username_len:
                return False
            
            # 读取密码长度和密码
            password_len_data = await asyncio.wait_for(reader.read(1), timeout=10)
            if len(password_len_data) != 1:
                return False
            
            password_len = struct.unpack('!B', password_len_data)[0]
            password = await asyncio.wait_for(reader.read(password_len), timeout=10)
            if len(password) != password_len:
                return False
            
            # 验证用户名密码
            username_str = username.decode('utf-8')
            password_str = password.decode('utf-8')
            
            if username_str == self.username and password_str == self.password:
                # 认证成功
                writer.write(struct.pack('!BB', 0x01, 0x00))
                await writer.drain()
                return True
            else:
                # 认证失败
                writer.write(struct.pack('!BB', 0x01, 0x01))
                await writer.drain()
                self.logger.warning(f"SOCKS5认证失败: {username_str}")
                return False
                
        except Exception as e:
            self.logger.error(f"SOCKS5认证错误: {e}")
            return False
    
    async def _handle_connect_request(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> Tuple[Optional[asyncio.StreamReader], Optional[asyncio.StreamWriter], Optional[Tuple[str, int]]]:
        """处理连接请求"""
        try:
            # 读取连接请求
            data = await asyncio.wait_for(reader.read(4), timeout=10)
            if len(data) != 4:
                return None, None, None
            
            version, cmd, rsv, addr_type = struct.unpack('!BBBB', data)
            
            if version != self.SOCKS_VERSION:
                await self._send_connect_response(writer, self.REP_GENERAL_FAILURE)
                return None, None, None
            
            if cmd != self.CMD_CONNECT:
                await self._send_connect_response(writer, self.REP_COMMAND_NOT_SUPPORTED)
                return None, None, None
            
            # 解析目标地址
            host, port = await self._parse_target_address(reader, addr_type)
            if not host:
                await self._send_connect_response(writer, self.REP_ADDRESS_TYPE_NOT_SUPPORTED)
                return None, None, None
            
            self.logger.info(f"SOCKS5连接目标: {host}:{port}")
            
            # 连接目标服务器
            try:
                target_reader, target_writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=10
                )
                
                # 发送成功响应
                await self._send_connect_response(writer, self.REP_SUCCESS, host, port)
                
                return target_reader, target_writer, (host, port)
                
            except Exception as e:
                self.logger.error(f"连接目标服务器失败: {host}:{port} - {e}")
                await self._send_connect_response(writer, self.REP_CONNECTION_REFUSED)
                return None, None, None
                
        except asyncio.TimeoutError:
            self.logger.warning("SOCKS5连接请求超时")
            return None, None, None
        except Exception as e:
            self.logger.error(f"SOCKS5连接请求错误: {e}")
            return None, None, None
    
    async def _parse_target_address(self, reader: asyncio.StreamReader, addr_type: int) -> Tuple[Optional[str], Optional[int]]:
        """解析目标地址"""
        try:
            if addr_type == self.ADDR_IPV4:
                # IPv4地址
                addr_data = await asyncio.wait_for(reader.read(4), timeout=10)
                if len(addr_data) != 4:
                    return None, None
                host = socket.inet_ntoa(addr_data)
                
            elif addr_type == self.ADDR_DOMAIN:
                # 域名
                domain_len_data = await asyncio.wait_for(reader.read(1), timeout=10)
                if len(domain_len_data) != 1:
                    return None, None
                
                domain_len = struct.unpack('!B', domain_len_data)[0]
                domain_data = await asyncio.wait_for(reader.read(domain_len), timeout=10)
                if len(domain_data) != domain_len:
                    return None, None
                
                host = domain_data.decode('utf-8')
                
            elif addr_type == self.ADDR_IPV6:
                # IPv6地址
                addr_data = await asyncio.wait_for(reader.read(16), timeout=10)
                if len(addr_data) != 16:
                    return None, None
                host = socket.inet_ntop(socket.AF_INET6, addr_data)
                
            else:
                return None, None
            
            # 读取端口
            port_data = await asyncio.wait_for(reader.read(2), timeout=10)
            if len(port_data) != 2:
                return None, None
            
            port = struct.unpack('!H', port_data)[0]
            
            return host, port
            
        except Exception as e:
            self.logger.error(f"解析目标地址错误: {e}")
            return None, None
    
    async def _send_connect_response(self, writer: asyncio.StreamWriter, rep_code: int, 
                                   host: str = "0.0.0.0", port: int = 0):
        """发送连接响应"""
        try:
            # 构造响应
            response = struct.pack('!BBBB', self.SOCKS_VERSION, rep_code, 0x00, self.ADDR_IPV4)
            
            # 添加绑定地址和端口（通常使用0.0.0.0:0）
            response += socket.inet_aton("0.0.0.0")
            response += struct.pack('!H', 0)
            
            writer.write(response)
            await writer.drain()
            
        except Exception as e:
            self.logger.error(f"发送SOCKS5响应错误: {e}")
    
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
                        self.stats.add_traffic('socks5', len(data), 0)
                    else:
                        self.stats.add_traffic('socks5', 0, len(data))
                        
        except asyncio.TimeoutError:
            self.logger.debug(f"SOCKS5数据转发超时: {direction}")
        except Exception as e:
            self.logger.debug(f"SOCKS5数据转发错误 {direction}: {e}")
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
        self.logger.info("SOCKS5服务器已停止")
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        return {
            'protocol': 'socks5',
            'host': self.host,
            'port': self.port,
            'auth_required': bool(self.username),
            'running': self.running,
            'connections': len(self.connections),
            'total_traffic': getattr(self.stats, 'get_traffic', lambda: (0, 0))() if self.stats else (0, 0)
        }

# 测试函数
async def test_socks5_server():
    """测试SOCKS5服务器"""
    print("🧪 测试SOCKS5服务器...")
    
    # 创建服务器
    server = SOCKS5Server(
        host='127.0.0.1',
        port=1080,
        username='test',
        password='pass'
    )
    
    print(f"✅ SOCKS5服务器创建成功")
    print(f"   监听地址: {server.host}:{server.port}")
    print(f"   认证: {server.username}:{server.password}")

if __name__ == "__main__":
    asyncio.run(test_socks5_server())