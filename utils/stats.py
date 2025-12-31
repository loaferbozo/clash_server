#!/usr/bin/env python3
"""
统计收集器
收集和管理代理服务器的统计信息
"""

import time
import threading
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
import json

@dataclass
class ConnectionInfo:
    """连接信息"""
    protocol: str
    client_addr: Tuple[str, int]
    target_addr: Tuple[str, int]
    start_time: float
    bytes_sent: int = 0
    bytes_received: int = 0

@dataclass
class TrafficStats:
    """流量统计"""
    protocol: str
    upload: int = 0      # 上传字节数
    download: int = 0    # 下载字节数
    connections: int = 0 # 连接数

class StatsCollector:
    """统计收集器"""
    
    def __init__(self):
        self.start_time = time.time()
        self.lock = threading.RLock()
        
        # 当前活动连接
        self.active_connections: Dict[str, ConnectionInfo] = {}
        
        # 协议统计
        self.protocol_stats: Dict[str, TrafficStats] = {}
        
        # 历史统计
        self.total_connections = 0
        self.total_upload = 0
        self.total_download = 0
        
        # 每小时统计（保留24小时）
        self.hourly_stats: List[Dict] = []
        self.last_hour_update = int(time.time() // 3600)
    
    def add_connection(self, protocol: str, client_addr: Tuple[str, int], target_addr: Tuple[str, int]):
        """添加新连接"""
        with self.lock:
            connection_id = f"{protocol}:{client_addr[0]}:{client_addr[1]}"
            
            conn_info = ConnectionInfo(
                protocol=protocol,
                client_addr=client_addr,
                target_addr=target_addr,
                start_time=time.time()
            )
            
            self.active_connections[connection_id] = conn_info
            
            # 更新协议统计
            if protocol not in self.protocol_stats:
                self.protocol_stats[protocol] = TrafficStats(protocol=protocol)
            
            self.protocol_stats[protocol].connections += 1
            self.total_connections += 1
    
    def remove_connection(self, protocol: str, client_addr: Tuple[str, int]):
        """移除连接"""
        with self.lock:
            connection_id = f"{protocol}:{client_addr[0]}:{client_addr[1]}"
            
            if connection_id in self.active_connections:
                conn_info = self.active_connections[connection_id]
                
                # 更新协议统计
                if protocol in self.protocol_stats:
                    self.protocol_stats[protocol].connections -= 1
                
                del self.active_connections[connection_id]
    
    def add_traffic(self, protocol: str, upload: int, download: int):
        """添加流量统计"""
        with self.lock:
            # 更新协议统计
            if protocol not in self.protocol_stats:
                self.protocol_stats[protocol] = TrafficStats(protocol=protocol)
            
            self.protocol_stats[protocol].upload += upload
            self.protocol_stats[protocol].download += download
            
            # 更新总统计
            self.total_upload += upload
            self.total_download += download
            
            # 更新小时统计
            self._update_hourly_stats()
    
    def _update_hourly_stats(self):
        """更新小时统计"""
        current_hour = int(time.time() // 3600)
        
        if current_hour > self.last_hour_update:
            # 新的小时，添加统计记录
            hour_stats = {
                'hour': current_hour,
                'timestamp': current_hour * 3600,
                'upload': self.total_upload,
                'download': self.total_download,
                'connections': self.total_connections,
                'protocols': {k: asdict(v) for k, v in self.protocol_stats.items()}
            }
            
            self.hourly_stats.append(hour_stats)
            
            # 只保留最近24小时的数据
            if len(self.hourly_stats) > 24:
                self.hourly_stats = self.hourly_stats[-24:]
            
            self.last_hour_update = current_hour
    
    def get_current_stats(self) -> Dict[str, Any]:
        """获取当前统计信息"""
        with self.lock:
            uptime = int(time.time() - self.start_time)
            
            return {
                'uptime': uptime,
                'start_time': self.start_time,
                'current_time': time.time(),
                'total_upload': self.total_upload,
                'total_download': self.total_download,
                'total_connections': self.total_connections,
                'active_connections': len(self.active_connections),
                'protocols': {k: asdict(v) for k, v in self.protocol_stats.items()},
                'connections_per_protocol': {
                    protocol: len([c for c in self.active_connections.values() if c.protocol == protocol])
                    for protocol in self.protocol_stats.keys()
                }
            }
    
    def get_active_connections(self) -> List[Dict[str, Any]]:
        """获取活动连接列表"""
        with self.lock:
            connections = []
            current_time = time.time()
            
            for conn_id, conn_info in self.active_connections.items():
                connections.append({
                    'id': conn_id,
                    'protocol': conn_info.protocol,
                    'client_addr': f"{conn_info.client_addr[0]}:{conn_info.client_addr[1]}",
                    'target_addr': f"{conn_info.target_addr[0]}:{conn_info.target_addr[1]}",
                    'duration': int(current_time - conn_info.start_time),
                    'bytes_sent': conn_info.bytes_sent,
                    'bytes_received': conn_info.bytes_received
                })
            
            return connections
    
    def get_hourly_stats(self) -> List[Dict[str, Any]]:
        """获取小时统计"""
        with self.lock:
            return self.hourly_stats.copy()
    
    def get_protocol_stats(self, protocol: str) -> Dict[str, Any]:
        """获取指定协议的统计信息"""
        with self.lock:
            if protocol in self.protocol_stats:
                stats = asdict(self.protocol_stats[protocol])
                stats['active_connections'] = len([
                    c for c in self.active_connections.values() 
                    if c.protocol == protocol
                ])
                return stats
            else:
                return {
                    'protocol': protocol,
                    'upload': 0,
                    'download': 0,
                    'connections': 0,
                    'active_connections': 0
                }
    
    def get_traffic(self) -> Tuple[int, int]:
        """获取总流量 (上传, 下载)"""
        with self.lock:
            return self.total_upload, self.total_download
    
    def reset_stats(self):
        """重置统计信息"""
        with self.lock:
            self.start_time = time.time()
            self.active_connections.clear()
            self.protocol_stats.clear()
            self.total_connections = 0
            self.total_upload = 0
            self.total_download = 0
            self.hourly_stats.clear()
            self.last_hour_update = int(time.time() // 3600)
    
    def export_stats(self) -> Dict[str, Any]:
        """导出所有统计信息"""
        with self.lock:
            return {
                'current_stats': self.get_current_stats(),
                'active_connections': self.get_active_connections(),
                'hourly_stats': self.get_hourly_stats(),
                'export_time': time.time()
            }
    
    def save_to_file(self, filename: str):
        """保存统计信息到文件"""
        try:
            stats_data = self.export_stats()
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存统计信息失败: {e}")
    
    def load_from_file(self, filename: str):
        """从文件加载统计信息"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                stats_data = json.load(f)
            
            # 恢复基础统计
            current_stats = stats_data.get('current_stats', {})
            self.total_upload = current_stats.get('total_upload', 0)
            self.total_download = current_stats.get('total_download', 0)
            self.total_connections = current_stats.get('total_connections', 0)
            
            # 恢复协议统计
            protocols = current_stats.get('protocols', {})
            for protocol, stats in protocols.items():
                self.protocol_stats[protocol] = TrafficStats(
                    protocol=protocol,
                    upload=stats.get('upload', 0),
                    download=stats.get('download', 0),
                    connections=stats.get('connections', 0)
                )
            
            # 恢复小时统计
            self.hourly_stats = stats_data.get('hourly_stats', [])
            
        except Exception as e:
            print(f"加载统计信息失败: {e}")

# 格式化工具函数
def format_bytes(bytes_count: int) -> str:
    """格式化字节数"""
    if bytes_count == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    while bytes_count >= 1024 and i < len(units) - 1:
        bytes_count /= 1024
        i += 1
    
    return f"{bytes_count:.2f} {units[i]}"

def format_duration(seconds: int) -> str:
    """格式化时长"""
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}分{seconds}秒"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}小时{minutes}分钟"

# 测试函数
def test_stats_collector():
    """测试统计收集器"""
    print("🧪 测试统计收集器...")
    
    stats = StatsCollector()
    
    # 添加连接
    stats.add_connection('shadowsocks', ('192.168.1.100', 12345), ('google.com', 443))
    stats.add_connection('socks5', ('192.168.1.101', 12346), ('github.com', 443))
    
    # 添加流量
    stats.add_traffic('shadowsocks', 1024, 2048)
    stats.add_traffic('socks5', 512, 1024)
    
    # 获取统计信息
    current_stats = stats.get_current_stats()
    print(f"✅ 当前统计: {current_stats}")
    
    active_connections = stats.get_active_connections()
    print(f"✅ 活动连接: {len(active_connections)}个")
    
    # 移除连接
    stats.remove_connection('shadowsocks', ('192.168.1.100', 12345))
    
    print("✅ 统计收集器测试通过")

if __name__ == "__main__":
    test_stats_collector()