#!/usr/bin/env python3
"""
Clash兼容代理服务器测试脚本
"""

import asyncio
import aiohttp
import time
import sys
import json
from pathlib import Path

class ServerTester:
    def __init__(self):
        self.base_url = "http://localhost:9999"
        self.ss_proxy = "http://localhost:8388"
        self.socks5_proxy = "socks5://localhost:1080"
        self.http_proxy = "http://localhost:8080"
        
    async def test_api_endpoints(self):
        """测试API端点"""
        print("🧪 测试API端点...")
        
        endpoints = [
            "/api/status",
            "/api/stats", 
            "/api/connections",
            "/api/traffic",
            "/api/servers"
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                try:
                    async with session.get(f"{self.base_url}{endpoint}") as response:
                        if response.status == 200:
                            data = await response.json()
                            print(f"✅ {endpoint}: {response.status}")
                        else:
                            print(f"❌ {endpoint}: {response.status}")
                except Exception as e:
                    print(f"❌ {endpoint}: 连接失败 - {e}")
    
    async def test_shadowsocks_proxy(self):
        """测试Shadowsocks代理"""
        print("🧪 测试Shadowsocks代理...")
        
        # 注意：这里需要实际的Shadowsocks客户端库来测试
        # 简化为检查端口监听
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('localhost', 8388))
            sock.close()
            
            if result == 0:
                print("✅ Shadowsocks端口监听正常")
            else:
                print("❌ Shadowsocks端口未监听")
        except Exception as e:
            print(f"❌ Shadowsocks测试失败: {e}")
    
    async def test_socks5_proxy(self):
        """测试SOCKS5代理"""
        print("🧪 测试SOCKS5代理...")
        
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('localhost', 1080))
            sock.close()
            
            if result == 0:
                print("✅ SOCKS5端口监听正常")
            else:
                print("❌ SOCKS5端口未监听")
        except Exception as e:
            print(f"❌ SOCKS5测试失败: {e}")
    
    async def test_http_proxy(self):
        """测试HTTP代理"""
        print("🧪 测试HTTP代理...")
        
        test_urls = [
            "http://httpbin.org/ip",
            "https://httpbin.org/ip"
        ]
        
        connector = aiohttp.TCPConnector()
        async with aiohttp.ClientSession(connector=connector) as session:
            for url in test_urls:
                try:
                    async with session.get(
                        url, 
                        proxy=self.http_proxy,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            print(f"✅ HTTP代理 {url}: {result.get('origin', 'N/A')}")
                        else:
                            print(f"❌ HTTP代理 {url}: {response.status}")
                except Exception as e:
                    print(f"❌ HTTP代理 {url}: {e}")
    
    async def test_web_interface(self):
        """测试Web界面"""
        print("🧪 测试Web界面...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/") as response:
                    if response.status == 200:
                        content = await response.text()
                        if "Clash兼容代理服务器" in content:
                            print("✅ Web界面可访问")
                        else:
                            print("❌ Web界面内容异常")
                    else:
                        print(f"❌ Web界面: {response.status}")
        except Exception as e:
            print(f"❌ Web界面: {e}")
    
    async def test_config_generation(self):
        """测试配置生成"""
        print("🧪 测试配置生成...")
        
        try:
            # 检查是否可以生成Clash配置
            import subprocess
            result = subprocess.run([
                sys.executable, 'server.py', 
                '--generate-config', '-c', 'config.yaml'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("✅ Clash配置生成成功")
                if Path('clash_client_config.yaml').exists():
                    print("✅ 配置文件已保存")
                else:
                    print("❌ 配置文件未找到")
            else:
                print(f"❌ 配置生成失败: {result.stderr}")
        except Exception as e:
            print(f"❌ 配置生成测试失败: {e}")
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始Clash兼容代理服务器测试")
        print("=" * 50)
        
        # 等待服务启动
        print("⏳ 等待服务启动...")
        await asyncio.sleep(3)
        
        # 运行测试
        await self.test_web_interface()
        await self.test_api_endpoints()
        await self.test_shadowsocks_proxy()
        await self.test_socks5_proxy()
        await self.test_http_proxy()
        await self.test_config_generation()
        
        print("=" * 50)
        print("✅ 测试完成")

def create_test_config():
    """创建测试配置文件"""
    config_content = """
# 测试配置文件
server:
  host: "0.0.0.0"
  log_level: "info"
  max_connections: 100

shadowsocks:
  enabled: true
  port: 8388
  method: "aes-256-gcm"
  password: "test-password-123"
  timeout: 300

socks5:
  enabled: true
  port: 1080
  username: ""
  password: ""
  timeout: 300

http:
  enabled: true
  port: 8080
  username: ""
  password: ""
  timeout: 300

vmess:
  enabled: false
  port: 443
  uuid: "12345678-1234-1234-1234-123456789abc"
  alter_id: 0
  tls: false

trojan:
  enabled: false
  port: 443
  password: "trojan-test-password"

dashboard:
  enabled: true
  port: 9999
  username: ""
  password: ""

security:
  allowed_ips: []
  max_connections_per_ip: 10
  bandwidth_limit: 0
  replay_protection: true
"""
    
    with open("test_config.yaml", "w", encoding="utf-8") as f:
        f.write(config_content)
    
    print("✅ 测试配置文件已创建: test_config.yaml")

async def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--create-config":
        create_test_config()
        return
    
    # 检查配置文件
    if not Path("config.yaml").exists() and not Path("test_config.yaml").exists():
        print("❌ 未找到配置文件，请先创建配置文件")
        print("提示: python test_server.py --create-config")
        return
    
    # 运行测试
    tester = ServerTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())