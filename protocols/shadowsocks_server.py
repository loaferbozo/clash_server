#!/usr/bin/env python3
"""
Shadowsocks服务器实现
支持多种加密算法，兼容Clash客户端
"""

import asyncio
import socket
import struct
import hashlib
import hmac
import os
import time
import logging
from typing import Optional, Tuple, Dict, Any
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
from cryptography.hazmat.backends import default_backend

class ShadowsocksError(Exception):
    """Shadowsocks错误"""
    pass

class ShadowsocksCrypto:
    """Shadowsocks加密解密器"""
    
    # 支持的加密方法
    SUPPORTED_METHODS = {
        'aes-128-gcm': (16, 16, 'aead'),
        'aes-192-gcm': (24, 16, 'aead'), 
        'aes-256-gcm': (32, 16, 'aead'),
        'chacha20-ietf-poly1305': (32, 32, 'aead'),
        'aes-128-cfb': (16, 16, 'stream'),
        'aes-192-cfb': (24, 16, 'stream'),
        'aes-256-cfb': (32, 16, 'stream'),
        'aes-128-ctr': (16, 16, 'stream'),
        'aes-192-ctr': (24, 16, 'stream'),
        'aes-256-ctr': (32, 16, 'stream'),
    }
    
    def __init__(self, method: str, password: str):
        if method not in self.SUPPORTED_METHODS:
            raise ShadowsocksError(f"不支持的加密方法: {method}")
        
        self.method = method
        self.password = password.encode() if isinstance(password, str) else password
        self.key_len, self.iv_len, self.crypto_type = self.SUPPORTED_METHODS[method]
        self.key = self._derive_key()
        
        self.logger = logging.getLogger(f"{__name__}.{method}")
    
    def _derive_key(self) -> bytes:
        """EVP_BytesToKey密钥派生"""
        key = b''
        i = 0
        while len(key) < self.key_len:
            md5 = hashlib.md5()
            data = self.password
            if i > 0:
                data = key[i-16:i] + self.password
            md5.update(data)
            key += md5.digest()
            i += 16
        return key[:self.key_len]
    
    def encrypt(self, plaintext: bytes, iv: bytes = None) -> Tuple[bytes, bytes]:
        """加密数据"""
        if iv is None:
            iv = os.urandom(self.iv_len)
        
        try:
            if self.crypto_type == 'aead':
                return self._encrypt_aead(plaintext, iv)
            else:
                return self._encrypt_stream(plaintext, iv)
        except Exception as e:
            raise ShadowsocksError(f"加密失败: {e}")
    
    def decrypt(self, ciphertext: bytes, iv: bytes) -> bytes:
        """解密数据"""
        try:
            if self.crypto_type == 'aead':
                return self._decrypt_aead(ciphertext, iv)
            else:
                return self._decrypt_stream(ciphertext, iv)
        except Exception as e:
            raise ShadowsocksError(f"解密失败: {e}")
    
    def _encrypt_aead(self, plaintext: bytes, iv: bytes) -> Tuple[bytes, bytes]:
        """AEAD加密"""
        if 'aes' in self.method:
            aead = AESGCM(self.key)
            ciphertext = aead.encrypt(iv, plaintext, None)
            return ciphertext, iv
        elif 'chacha20' in self.method:
            aead = ChaCha20Poly1305(self.key)
            # ChaCha20需要12字节nonce
            nonce = iv[:12] if len(iv) >= 12 else iv + b'\x00' * (12 - len(iv))
            ciphertext = aead.encrypt(nonce, plaintext, None)
            return ciphertext, iv
        else:
            raise ShadowsocksError(f"不支持的AEAD方法: {self.method}")
    
    def _decrypt_aead(self, ciphertext: bytes, iv: bytes) -> bytes:
        """AEAD解密"""
        if 'aes' in self.method:
            aead = AESGCM(self.key)
            return aead.decrypt(iv, ciphertext, None)
        elif 'chacha20' in self.method:
            aead = ChaCha20Poly1305(self.key)
            nonce = iv[:12] if len(iv) >= 12 else iv + b'\x00' * (12 - len(iv))
            return aead.decrypt(nonce, ciphertext, None)
        else:
            raise ShadowsocksError(f"不支持的AEAD方法: {self.method}")
    
    def _encrypt_stream(self, plaintext: bytes, iv: bytes) -> Tuple[bytes, bytes]:
        """流加密"""
        if 'cfb' in self.method:
            mode = modes.CFB(iv)
        elif 'ctr' in self.method:
            mode = modes.CTR(iv)
        else:
            raise ShadowsocksError(f"不支持的流加密模式: {self.method}")
        
        algorithm = algorithms.AES(self.key)
        cipher = Cipher(algorithm, mode, backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        
        return ciphertext, iv
    
    def _decrypt_stream(self, ciphertext: bytes, iv: bytes) -> bytes:
        """流解密"""
        if 'cfb' in self.method:
            mode = modes.CFB(iv)
        elif 'ctr' in self.method:
            mode = modes.CTR(iv)
        else:
            raise ShadowsocksError(f"不支持的流解密模式: {self.method}")
        
        algorithm = algorithms.AES(self.key)
        cipher = Cipher(algorithm, mode, backend=default_backend())
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()

class ShadowsocksConnection:
    """Shadowsocks连接处理器"""
    
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, 
                 crypto: ShadowsocksCrypto, stats: Any, timeout: int = 300):
        self.reader = reader
        self.writer = writer
        self.crypto = crypto
        self.stats = stats
        self.timeout = timeout
        self.client_addr = writer.get_extra_info('peername')
        self.target_addr = None
        self.start_time = time.time()
        
        self.logger = logging.getLogger(f"{__name__}.Connection")
        
        # 统计信息
        self.bytes_sent = 0
        self.bytes_received = 0
    
    async def handle(self):
        """处理Shadowsocks连接"""
        try:
            self.logger.info(f"新的Shadowsocks连接: {self.client_addr}")
            
            # 读取IV和加密的地址信息
            iv_data = await asyncio.wait_for(
                self.reader.read(self.crypto.iv_len), 
                timeout=10
            )
            
            if len(iv_data) != self.crypto.iv_len:
                raise ShadowsocksError("IV长度不正确")
            
            # 读取加密的地址数据
            encrypted_addr_data = await asyncio.wait_for(
                self.reader.read(1024),
                timeout=10
            )
            
            if not encrypted_addr_data:
                raise ShadowsocksError("未收到地址数据")
            
            # 解密地址信息
            addr_data = self.crypto.decrypt(encrypted_addr_data, iv_data)
            host, port = self._parse_address(addr_data)
            self.target_addr = (host, port)
            
            self.logger.info(f"目标地址: {host}:{port}")
            
            # 连接目标服务器
            try:
                target_reader, target_writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=10
                )
            except Exception as e:
                raise ShadowsocksError(f"连接目标服务器失败: {e}")
            
            # 更新统计信息
            if self.stats:
                self.stats.add_connection('shadowsocks', self.client_addr, self.target_addr)
            
            # 开始双向数据转发
            await asyncio.gather(
                self._forward_client_to_target(target_writer, iv_data),
                self._forward_target_to_client(target_reader, iv_data),
                return_exceptions=True
            )
            
        except asyncio.TimeoutError:
            self.logger.warning(f"连接超时: {self.client_addr}")
        except ShadowsocksError as e:
            self.logger.error(f"Shadowsocks错误: {e}")
        except Exception as e:
            self.logger.error(f"连接处理错误: {e}")
        finally:
            await self._cleanup()
    
    def _parse_address(self, data: bytes) -> Tuple[str, int]:
        """解析地址信息"""
        if len(data) < 7:
            raise ShadowsocksError("地址数据太短")
        
        addr_type = data[0]
        
        if addr_type == 1:  # IPv4
            if len(data) < 7:
                raise ShadowsocksError("IPv4地址数据不完整")
            host = socket.inet_ntoa(data[1:5])
            port = struct.unpack('>H', data[5:7])[0]
        elif addr_type == 3:  # 域名
            domain_len = data[1]
            if len(data) < 4 + domain_len:
                raise ShadowsocksError("域名地址数据不完整")
            host = data[2:2+domain_len].decode('utf-8')
            port = struct.unpack('>H', data[2+domain_len:4+domain_len])[0]
        elif addr_type == 4:  # IPv6
            if len(data) < 19:
                raise ShadowsocksError("IPv6地址数据不完整")
            host = socket.inet_ntop(socket.AF_INET6, data[1:17])
            port = struct.unpack('>H', data[17:19])[0]
        else:
            raise ShadowsocksError(f"不支持的地址类型: {addr_type}")
        
        return host, port
    
    async def _forward_client_to_target(self, target_writer: asyncio.StreamWriter, iv: bytes):
        """转发客户端数据到目标服务器"""
        try:
            while True:
                # 读取加密数据
                encrypted_data = await asyncio.wait_for(
                    self.reader.read(8192),
                    timeout=self.timeout
                )
                
                if not encrypted_data:
                    break
                
                # 解密数据
                try:
                    decrypted_data = self.crypto.decrypt(encrypted_data, iv)
                    
                    # 转发到目标服务器
                    target_writer.write(decrypted_data)
                    await target_writer.drain()
                    
                    # 更新统计
                    self.bytes_received += len(encrypted_data)
                    if self.stats:
                        self.stats.add_traffic('shadowsocks', len(encrypted_data), 0)
                        
                except Exception as e:
                    self.logger.debug(f"解密失败: {e}")
                    break
                    
        except asyncio.TimeoutError:
            self.logger.debug("客户端到目标转发超时")
        except Exception as e:
            self.logger.debug(f"客户端到目标转发错误: {e}")
        finally:
            try:
                target_writer.close()
                await target_writer.wait_closed()
            except:
                pass
    
    async def _forward_target_to_client(self, target_reader: asyncio.StreamReader, iv: bytes):
        """转发目标服务器数据到客户端"""
        try:
            while True:
                # 读取目标服务器数据
                data = await asyncio.wait_for(
                    target_reader.read(8192),
                    timeout=self.timeout
                )
                
                if not data:
                    break
                
                # 加密数据
                try:
                    encrypted_data, _ = self.crypto.encrypt(data, iv)
                    
                    # 发送给客户端
                    self.writer.write(encrypted_data)
                    await self.writer.drain()
                    
                    # 更新统计
                    self.bytes_sent += len(encrypted_data)
                    if self.stats:
                        self.stats.add_traffic('shadowsocks', 0, len(encrypted_data))
                        
                except Exception as e:
                    self.logger.debug(f"加密失败: {e}")
                    break
                    
        except asyncio.TimeoutError:
            self.logger.debug("目标到客户端转发超时")
        except Exception as e:
            self.logger.debug(f"目标到客户端转发错误: {e}")
        finally:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except:
                pass
    
    async def _cleanup(self):
        """清理连接"""
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except:
            pass
        
        # 更新统计信息
        if self.stats:
            duration = time.time() - self.start_time
            self.stats.remove_connection('shadowsocks', self.client_addr)
            
        self.logger.info(
            f"连接关闭: {self.client_addr} -> {self.target_addr}, "
            f"上传: {self.bytes_received}B, 下载: {self.bytes_sent}B, "
            f"时长: {time.time() - self.start_time:.1f}s"
        )

class ShadowsocksServer:
    """Shadowsocks服务器"""
    
    def __init__(self, host: str, port: int, method: str, password: str, 
                 timeout: int = 300, stats: Any = None):
        self.host = host
        self.port = port
        self.method = method
        self.password = password
        self.timeout = timeout
        self.stats = stats
        
        # 创建加密器
        self.crypto = ShadowsocksCrypto(method, password)
        
        # 服务器状态
        self.server = None
        self.running = False
        self.connections: Dict[str, ShadowsocksConnection] = {}
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """启动Shadowsocks服务器"""
        try:
            self.server = await asyncio.start_server(
                self._handle_client,
                self.host,
                self.port
            )
            
            self.running = True
            self.logger.info(f"🔒 Shadowsocks服务器启动: {self.host}:{self.port}")
            self.logger.info(f"   加密方法: {self.method}")
            self.logger.info(f"   密码: {'*' * len(self.password)}")
            
            async with self.server:
                await self.server.serve_forever()
                
        except Exception as e:
            self.logger.error(f"Shadowsocks服务器启动失败: {e}")
            raise
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """处理客户端连接"""
        client_addr = writer.get_extra_info('peername')
        connection_id = f"{client_addr[0]}:{client_addr[1]}"
        
        try:
            # 创建连接处理器
            connection = ShadowsocksConnection(
                reader, writer, self.crypto, self.stats, self.timeout
            )
            
            self.connections[connection_id] = connection
            
            # 处理连接
            await connection.handle()
            
        except Exception as e:
            self.logger.error(f"处理客户端连接失败: {e}")
        finally:
            # 清理连接
            if connection_id in self.connections:
                del self.connections[connection_id]
    
    async def stop(self):
        """停止服务器"""
        self.running = False
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # 关闭所有连接
        for connection in list(self.connections.values()):
            try:
                await connection._cleanup()
            except:
                pass
        
        self.connections.clear()
        self.logger.info("Shadowsocks服务器已停止")
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        return {
            'protocol': 'shadowsocks',
            'host': self.host,
            'port': self.port,
            'method': self.method,
            'running': self.running,
            'connections': len(self.connections),
            'total_traffic': getattr(self.stats, 'get_traffic', lambda: (0, 0))() if self.stats else (0, 0)
        }

# 测试函数
async def test_shadowsocks_server():
    """测试Shadowsocks服务器"""
    print("🧪 测试Shadowsocks服务器...")
    
    # 创建服务器
    server = ShadowsocksServer(
        host='127.0.0.1',
        port=8388,
        method='aes-256-gcm',
        password='test-password'
    )
    
    # 启动服务器（这里只是测试创建，不实际启动）
    print(f"✅ Shadowsocks服务器创建成功")
    print(f"   监听地址: {server.host}:{server.port}")
    print(f"   加密方法: {server.method}")
    
    # 测试加密解密
    crypto = server.crypto
    original_data = b"Hello, Shadowsocks!"
    encrypted_data, iv = crypto.encrypt(original_data)
    decrypted_data = crypto.decrypt(encrypted_data, iv)
    
    assert original_data == decrypted_data
    print("✅ 加密解密测试通过")

if __name__ == "__main__":
    asyncio.run(test_shadowsocks_server())