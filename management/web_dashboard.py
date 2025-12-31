#!/usr/bin/env python3
"""
Web管理界面
提供代理服务器的Web管理和监控功能
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any
from aiohttp import web, web_runner
import aiohttp_jinja2
import jinja2
from pathlib import Path

class WebDashboard:
    """Web管理界面"""
    
    def __init__(self, host: str, port: int, stats: Any, servers: Dict[str, Any]):
        self.host = host
        self.port = port
        self.stats = stats
        self.servers = servers
        
        self.app = None
        self.runner = None
        self.site = None
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """启动Web管理界面"""
        try:
            # 创建Web应用
            self.app = web.Application()
            
            # 设置模板引擎
            template_dir = Path(__file__).parent / 'templates'
            if template_dir.exists():
                aiohttp_jinja2.setup(
                    self.app,
                    loader=jinja2.FileSystemLoader(str(template_dir))
                )
            
            # 设置路由
            self._setup_routes()
            
            # 启动服务器
            self.runner = web_runner.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web_runner.TCPSite(self.runner, self.host, self.port)
            await self.site.start()
            
            self.logger.info(f"📊 Web管理界面启动: http://{self.host}:{self.port}")
            
            # 保持运行
            while True:
                await asyncio.sleep(3600)  # 每小时检查一次
                
        except Exception as e:
            self.logger.error(f"Web管理界面启动失败: {e}")
            raise
    
    def _setup_routes(self):
        """设置路由"""
        # 静态文件
        self.app.router.add_static('/', Path(__file__).parent / 'static', name='static')
        
        # API路由
        self.app.router.add_get('/', self._index)
        self.app.router.add_get('/api/status', self._api_status)
        self.app.router.add_get('/api/stats', self._api_stats)
        self.app.router.add_get('/api/connections', self._api_connections)
        self.app.router.add_get('/api/traffic', self._api_traffic)
        self.app.router.add_get('/api/servers', self._api_servers)
    
    async def _index(self, request):
        """主页"""
        html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clash兼容代理服务器管理</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; text-align: center; }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; }
        .header p { font-size: 1.1rem; opacity: 0.9; }
        .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: white; border-radius: 10px; padding: 25px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        .card h3 { color: #333; margin-bottom: 15px; font-size: 1.3rem; }
        .stats-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }
        .stat-item { text-align: center; padding: 15px; background: #f8f9ff; border-radius: 8px; }
        .stat-value { font-size: 1.8rem; font-weight: bold; color: #667eea; }
        .stat-label { font-size: 0.9rem; color: #666; margin-top: 5px; }
        .server-list { max-height: 300px; overflow-y: auto; }
        .server-item { display: flex; justify-content: space-between; align-items: center; padding: 12px; margin-bottom: 8px; background: #f8f9ff; border-radius: 8px; }
        .server-name { font-weight: 500; }
        .server-status { padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 500; }
        .status-running { background: #e8f5e8; color: #2e7d32; }
        .status-stopped { background: #ffebee; color: #c62828; }
        .refresh-btn { position: fixed; bottom: 30px; right: 30px; width: 60px; height: 60px; border-radius: 50%; background: #667eea; color: white; border: none; font-size: 1.5rem; cursor: pointer; box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        .refresh-btn:hover { background: #5a6fd8; transform: scale(1.1); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Clash兼容代理服务器</h1>
            <p>多协议代理服务器管理界面</p>
        </div>
        
        <div class="dashboard">
            <div class="card">
                <h3>📊 服务器统计</h3>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value" id="uptime">0s</div>
                        <div class="stat-label">运行时间</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="connections">0</div>
                        <div class="stat-label">活动连接</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="upload">0 B</div>
                        <div class="stat-label">上传流量</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="download">0 B</div>
                        <div class="stat-label">下载流量</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h3>🌐 协议服务器</h3>
                <div class="server-list" id="server-list">
                    <div style="text-align: center; color: #666; font-style: italic;">加载中...</div>
                </div>
            </div>
            
            <div class="card">
                <h3>🔗 活动连接</h3>
                <div class="server-list" id="connections-list">
                    <div style="text-align: center; color: #666; font-style: italic;">加载中...</div>
                </div>
            </div>
        </div>
    </div>
    
    <button class="refresh-btn" onclick="refreshAll()" title="刷新数据">🔄</button>
    
    <script>
        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        function formatTime(seconds) {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = seconds % 60;
            if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
            if (minutes > 0) return `${minutes}m ${secs}s`;
            return `${secs}s`;
        }
        
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                document.getElementById('uptime').textContent = formatTime(data.uptime || 0);
                document.getElementById('connections').textContent = data.active_connections || 0;
                document.getElementById('upload').textContent = formatBytes(data.total_upload || 0);
                document.getElementById('download').textContent = formatBytes(data.total_download || 0);
            } catch (error) {
                console.error('加载统计失败:', error);
            }
        }
        
        async function loadServers() {
            try {
                const response = await fetch('/api/servers');
                const data = await response.json();
                const serverList = document.getElementById('server-list');
                
                if (Object.keys(data.servers).length === 0) {
                    serverList.innerHTML = '<div style="text-align: center; color: #666;">暂无服务器</div>';
                    return;
                }
                
                let html = '';
                for (const [name, server] of Object.entries(data.servers)) {
                    const statusClass = server.running ? 'status-running' : 'status-stopped';
                    const statusText = server.running ? '运行中' : '已停止';
                    
                    html += `
                        <div class="server-item">
                            <div>
                                <div class="server-name">${server.protocol.toUpperCase()} - ${server.host}:${server.port}</div>
                                <small style="color: #666;">连接数: ${server.connections || 0}</small>
                            </div>
                            <div class="server-status ${statusClass}">${statusText}</div>
                        </div>
                    `;
                }
                
                serverList.innerHTML = html;
            } catch (error) {
                console.error('加载服务器失败:', error);
                document.getElementById('server-list').innerHTML = '<div style="text-align: center; color: #f44336;">加载失败</div>';
            }
        }
        
        async function loadConnections() {
            try {
                const response = await fetch('/api/connections');
                const data = await response.json();
                const connectionsList = document.getElementById('connections-list');
                
                if (data.connections.length === 0) {
                    connectionsList.innerHTML = '<div style="text-align: center; color: #666;">暂无活动连接</div>';
                    return;
                }
                
                let html = '';
                data.connections.slice(0, 10).forEach(conn => {
                    html += `
                        <div class="server-item">
                            <div>
                                <div class="server-name">${conn.protocol.toUpperCase()}</div>
                                <small style="color: #666;">${conn.client_addr} → ${conn.target_addr}</small>
                            </div>
                            <small style="color: #666;">${conn.duration}s</small>
                        </div>
                    `;
                });
                
                if (data.connections.length > 10) {
                    html += `<div style="text-align: center; color: #666; font-style: italic;">... 还有 ${data.connections.length - 10} 个连接</div>`;
                }
                
                connectionsList.innerHTML = html;
            } catch (error) {
                console.error('加载连接失败:', error);
                document.getElementById('connections-list').innerHTML = '<div style="text-align: center; color: #f44336;">加载失败</div>';
            }
        }
        
        function refreshAll() {
            loadStats();
            loadServers();
            loadConnections();
        }
        
        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', function() {
            refreshAll();
            
            // 每5秒自动刷新
            setInterval(refreshAll, 5000);
        });
    </script>
</body>
</html>
        """
        return web.Response(text=html_content, content_type='text/html')
    
    async def _api_status(self, request):
        """API: 服务器状态"""
        try:
            status = {
                'running': True,
                'timestamp': time.time(),
                'servers': len(self.servers),
                'protocols': list(self.servers.keys())
            }
            return web.json_response(status)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def _api_stats(self, request):
        """API: 统计信息"""
        try:
            if self.stats:
                stats = self.stats.get_current_stats()
            else:
                stats = {
                    'uptime': 0,
                    'total_upload': 0,
                    'total_download': 0,
                    'active_connections': 0
                }
            return web.json_response(stats)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def _api_connections(self, request):
        """API: 活动连接"""
        try:
            if self.stats:
                connections = self.stats.get_active_connections()
            else:
                connections = []
            
            return web.json_response({'connections': connections})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def _api_traffic(self, request):
        """API: 流量统计"""
        try:
            if self.stats:
                upload, download = self.stats.get_traffic()
                traffic = {
                    'upload': upload,
                    'download': download,
                    'total': upload + download
                }
            else:
                traffic = {'upload': 0, 'download': 0, 'total': 0}
            
            return web.json_response(traffic)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def _api_servers(self, request):
        """API: 服务器列表"""
        try:
            servers_info = {}
            for name, server in self.servers.items():
                if hasattr(server, 'get_status'):
                    servers_info[name] = server.get_status()
                else:
                    servers_info[name] = {
                        'protocol': name,
                        'running': getattr(server, 'running', False),
                        'connections': 0
                    }
            
            return web.json_response({'servers': servers_info})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def stop(self):
        """停止Web管理界面"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        
        self.logger.info("Web管理界面已停止")

# 测试函数
async def test_web_dashboard():
    """测试Web管理界面"""
    print("🧪 测试Web管理界面...")
    
    # 创建管理界面
    dashboard = WebDashboard(
        host='127.0.0.1',
        port=9999,
        stats=None,
        servers={}
    )
    
    print(f"✅ Web管理界面创建成功")
    print(f"   访问地址: http://{dashboard.host}:{dashboard.port}")

if __name__ == "__main__":
    asyncio.run(test_web_dashboard())