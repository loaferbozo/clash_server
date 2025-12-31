#!/usr/bin/env python3
"""
Clash兼容多协议代理服务器
支持Shadowsocks, VMess, Trojan, SOCKS5, HTTP等协议
"""

import asyncio
import logging
import signal
import sys
import yaml
import ssl
import json
import time
import uuid
import hashlib
import hmac
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import argparse

# 导入协议实现
from protocols.shadowsocks_server import ShadowsocksServer
from protocols.vmess_server import VMessServer
from protocols.trojan_server import TrojanServer
from protocols.socks5_server import SOCKS5Server
from protocols.http_server import HTTPProxyServer
from management.web_dashboard import WebDashboard
from utils.stats import StatsCollector

@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"
    log_level: str = "info"
    max_connections: int = 1000
    
    # 协议配置
    shadowsocks: Dict = None
    vmess: Dict = None
    trojan: Dict = None
    socks5: Dict = None
    http: Dict = None
    
    # 管理配置
    dashboard: Dict = None

class MultiProtocolServer:
    """多协议代理服务器"""
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.servers: Dict[str, Any] = {}
        self.stats = StatsCollector()
        self.running = False
        
        # 设置日志
        logging.basicConfig(
            level=getattr(logging, self.config.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('clash_server.log', encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def _load_config(self, config_path: str) -> ServerConfig:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            # 转换为ServerConfig对象
            server_config = config_data.get('server', {})
            config = ServerConfig(
                host=server_config.get('host', '0.0.0.0'),
                log_level=server_config.get('log_level', 'info'),
                max_connections=server_config.get('max_connections', 1000),
                shadowsocks=config_data.get('shadowsocks'),
                vmess=config_data.get('vmess'),
                trojan=config_data.get('trojan'),
                socks5=config_data.get('socks5'),
                http=config_data.get('http'),
                dashboard=config_data.get('dashboard', {'enabled': True, 'port': 9999})
            )
            
            self.logger.info(f"配置文件加载成功: {config_path}")
            return config
            
        except Exception as e:
            self.logger.error(f"配置文件加载失败: {e}")
            raise
    
    async def start_servers(self):
        """启动所有协议服务器"""
        self.logger.info("🚀 启动Clash兼容多协议代理服务器")
        self.logger.info("=" * 60)
        
        tasks = []
        
        # 启动Shadowsocks服务器
        if self.config.shadowsocks and self.config.shadowsocks.get('enabled', False):
            ss_server = ShadowsocksServer(
                host=self.config.host,
                port=self.config.shadowsocks['port'],
                method=self.config.shadowsocks['method'],
                password=self.config.shadowsocks['password'],
                timeout=self.config.shadowsocks.get('timeout', 300),
                stats=self.stats
            )
            self.servers['shadowsocks'] = ss_server
            tasks.append(ss_server.start())
            self.logger.info(f"🔒 Shadowsocks服务器: {self.config.host}:{self.config.shadowsocks['port']}")
        
        # 启动VMess服务器
        if self.config.vmess and self.config.vmess.get('enabled', False):
            vmess_server = VMessServer(
                host=self.config.host,
                port=self.config.vmess['port'],
                uuid=self.config.vmess['uuid'],
                alter_id=self.config.vmess.get('alter_id', 0),
                tls=self.config.vmess.get('tls', False),
                cert_file=self.config.vmess.get('cert_file'),
                key_file=self.config.vmess.get('key_file'),
                stats=self.stats
            )
            self.servers['vmess'] = vmess_server
            tasks.append(vmess_server.start())
            self.logger.info(f"⚡ VMess服务器: {self.config.host}:{self.config.vmess['port']}")
        
        # 启动Trojan服务器
        if self.config.trojan and self.config.trojan.get('enabled', False):
            trojan_server = TrojanServer(
                host=self.config.host,
                port=self.config.trojan['port'],
                password=self.config.trojan['password'],
                cert_file=self.config.trojan['cert_file'],
                key_file=self.config.trojan['key_file'],
                stats=self.stats
            )
            self.servers['trojan'] = trojan_server
            tasks.append(trojan_server.start())
            self.logger.info(f"🛡️ Trojan服务器: {self.config.host}:{self.config.trojan['port']}")
        
        # 启动SOCKS5服务器
        if self.config.socks5 and self.config.socks5.get('enabled', False):
            socks5_server = SOCKS5Server(
                host=self.config.host,
                port=self.config.socks5['port'],
                username=self.config.socks5.get('username'),
                password=self.config.socks5.get('password'),
                stats=self.stats
            )
            self.servers['socks5'] = socks5_server
            tasks.append(socks5_server.start())
            self.logger.info(f"🧦 SOCKS5服务器: {self.config.host}:{self.config.socks5['port']}")
        
        # 启动HTTP代理服务器
        if self.config.http and self.config.http.get('enabled', False):
            http_server = HTTPProxyServer(
                host=self.config.host,
                port=self.config.http['port'],
                username=self.config.http.get('username'),
                password=self.config.http.get('password'),
                stats=self.stats
            )
            self.servers['http'] = http_server
            tasks.append(http_server.start())
            self.logger.info(f"🌐 HTTP代理服务器: {self.config.host}:{self.config.http['port']}")
        
        # 启动Web管理界面
        if self.config.dashboard and self.config.dashboard.get('enabled', True):
            dashboard = WebDashboard(
                host=self.config.host,
                port=self.config.dashboard.get('port', 9999),
                stats=self.stats,
                servers=self.servers
            )
            tasks.append(dashboard.start())
            self.logger.info(f"📊 Web管理界面: http://{self.config.host}:{self.config.dashboard.get('port', 9999)}")
        
        self.logger.info("=" * 60)
        self.logger.info("✅ 所有服务器启动完成，等待客户端连接...")
        self.logger.info("📱 Clash客户端现在可以连接到以上服务器")
        
        # 设置信号处理
        def signal_handler(signum, frame):
            self.logger.info(f"\n收到信号 {signum}，正在关闭服务器...")
            self.running = False
            # 取消所有任务
            for task in tasks:
                if not task.done():
                    task.cancel()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        self.running = True
        
        try:
            # 等待所有服务器运行
            await asyncio.gather(*tasks, return_exceptions=True)
        except KeyboardInterrupt:
            self.logger.info("收到中断信号，正在关闭...")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """清理资源"""
        self.logger.info("正在清理资源...")
        
        # 停止所有服务器
        for name, server in self.servers.items():
            try:
                if hasattr(server, 'stop'):
                    await server.stop()
                self.logger.info(f"✅ {name}服务器已停止")
            except Exception as e:
                self.logger.error(f"❌ 停止{name}服务器失败: {e}")
        
        self.logger.info("👋 服务器已完全关闭")
    
    def generate_clash_config(self) -> str:
        """生成Clash客户端配置"""
        proxies = []
        
        # Shadowsocks配置
        if self.config.shadowsocks and self.config.shadowsocks.get('enabled'):
            ss_config = {
                'name': 'SS-Server',
                'type': 'ss',
                'server': 'your-server-ip',  # 用户需要替换
                'port': self.config.shadowsocks['port'],
                'cipher': self.config.shadowsocks['method'],
                'password': self.config.shadowsocks['password'],
                'udp': True
            }
            proxies.append(ss_config)
        
        # VMess配置
        if self.config.vmess and self.config.vmess.get('enabled'):
            vmess_config = {
                'name': 'VMess-Server',
                'type': 'vmess',
                'server': 'your-server-ip',
                'port': self.config.vmess['port'],
                'uuid': self.config.vmess['uuid'],
                'alterId': self.config.vmess.get('alter_id', 0),
                'cipher': 'auto',
                'tls': self.config.vmess.get('tls', False)
            }
            if self.config.vmess.get('tls'):
                vmess_config.update({
                    'network': 'ws',
                    'ws-opts': {
                        'path': '/vmess'
                    }
                })
            proxies.append(vmess_config)
        
        # Trojan配置
        if self.config.trojan and self.config.trojan.get('enabled'):
            trojan_config = {
                'name': 'Trojan-Server',
                'type': 'trojan',
                'server': 'your-server-ip',
                'port': self.config.trojan['port'],
                'password': self.config.trojan['password'],
                'sni': 'your-domain.com',  # 用户需要替换
                'udp': True
            }
            proxies.append(trojan_config)
        
        # SOCKS5配置
        if self.config.socks5 and self.config.socks5.get('enabled'):
            socks5_config = {
                'name': 'SOCKS5-Server',
                'type': 'socks5',
                'server': 'your-server-ip',
                'port': self.config.socks5['port']
            }
            if self.config.socks5.get('username'):
                socks5_config.update({
                    'username': self.config.socks5['username'],
                    'password': self.config.socks5['password']
                })
            proxies.append(socks5_config)
        
        # HTTP配置
        if self.config.http and self.config.http.get('enabled'):
            http_config = {
                'name': 'HTTP-Server',
                'type': 'http',
                'server': 'your-server-ip',
                'port': self.config.http['port']
            }
            if self.config.http.get('username'):
                http_config.update({
                    'username': self.config.http['username'],
                    'password': self.config.http['password']
                })
            proxies.append(http_config)
        
        # 生成完整配置
        clash_config = {
            'port': 7890,
            'socks-port': 7891,
            'allow-lan': True,
            'mode': 'rule',
            'log-level': 'info',
            'proxies': proxies,
            'proxy-groups': [
                {
                    'name': '🚀 节点选择',
                    'type': 'select',
                    'proxies': [proxy['name'] for proxy in proxies] + ['DIRECT']
                }
            ],
            'rules': [
                'GEOIP,CN,DIRECT',
                'MATCH,🚀 节点选择'
            ]
        }
        
        return yaml.dump(clash_config, default_flow_style=False, allow_unicode=True)
    
    def save_clash_config(self, filename: str = 'clash_client_config.yaml'):
        """保存Clash客户端配置到文件"""
        config_content = self.generate_clash_config()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(config_content)
        self.logger.info(f"✅ Clash客户端配置已保存到: {filename}")
        return filename

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Clash兼容多协议代理服务器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python server.py -c config.yaml                    # 启动服务器
  python server.py -c config.yaml --generate-config # 生成Clash客户端配置
  python server.py --test-config config.yaml        # 测试配置文件
        """
    )
    
    parser.add_argument(
        '-c', '--config',
        type=str,
        default='config.yaml',
        help='配置文件路径 (默认: config.yaml)'
    )
    
    parser.add_argument(
        '--generate-config',
        action='store_true',
        help='生成Clash客户端配置文件'
    )
    
    parser.add_argument(
        '--test-config',
        action='store_true',
        help='测试配置文件并退出'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Clash Server v1.0.0'
    )
    
    return parser.parse_args()

async def main():
    """主函数"""
    args = parse_arguments()
    
    # 检查配置文件
    if not Path(args.config).exists():
        print(f"❌ 配置文件不存在: {args.config}")
        sys.exit(1)
    
    try:
        # 创建服务器实例
        server = MultiProtocolServer(args.config)
        
        # 测试配置
        if args.test_config:
            print("✅ 配置文件测试通过")
            return
        
        # 生成客户端配置
        if args.generate_config:
            config_file = server.save_clash_config()
            print(f"✅ Clash客户端配置已生成: {config_file}")
            print("\n📝 请将配置文件中的 'your-server-ip' 替换为实际的服务器IP地址")
            return
        
        # 启动服务器
        await server.start_servers()
        
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        logging.exception("启动异常")
        sys.exit(1)

if __name__ == "__main__":
    # 设置事件循环策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    else:
        try:
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        except ImportError:
            pass
    
    # 运行主程序
    asyncio.run(main())