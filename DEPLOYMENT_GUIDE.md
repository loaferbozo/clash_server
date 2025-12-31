# 🚀 Clash兼容代理服务器部署指南

## 📋 概述

本指南将帮助你在VPS上部署一个完整的Clash兼容代理服务器，支持多种协议，让Clash客户端可以直接连接使用。

## 🎯 支持的协议

- **Shadowsocks** - 最流行和稳定的代理协议
- **SOCKS5** - 通用代理协议，兼容性好
- **HTTP代理** - 支持HTTP/HTTPS网站访问
- **VMess** - V2Ray核心协议（需要SSL证书）
- **Trojan** - 伪装HTTPS流量（需要SSL证书）

## 🛠️ 部署方式

### 方式1: 一键部署脚本（推荐）

```bash
# 下载部署脚本
wget https://raw.githubusercontent.com/your-repo/clash-server/main/deploy.sh

# 给予执行权限
chmod +x deploy.sh

# 运行一键部署
./deploy.sh install
```

### 方式2: 手动部署

#### 1. 系统要求

- **操作系统**: Ubuntu 18.04+, CentOS 7+, Debian 9+
- **内存**: 最少512MB，推荐1GB+
- **存储**: 最少1GB可用空间
- **网络**: 公网IP，开放相应端口

#### 2. 安装Python环境

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# CentOS/RHEL
sudo yum install -y python3 python3-pip
# 或者使用dnf (CentOS 8+)
sudo dnf install -y python3 python3-pip
```

#### 3. 下载项目代码

```bash
# 克隆项目
git clone https://github.com/your-repo/clash-server.git
cd clash-server

# 或者下载压缩包
wget https://github.com/your-repo/clash-server/archive/main.zip
unzip main.zip
cd clash-server-main
```

#### 4. 安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 5. 配置服务器

```bash
# 复制配置文件模板
cp config.yaml.example config.yaml

# 编辑配置文件
nano config.yaml
```

#### 6. 启动服务器

```bash
# 测试配置
python server.py --test-config config.yaml

# 启动服务器
python server.py -c config.yaml
```

## ⚙️ 配置详解

### 基础配置

```yaml
# 服务器基础设置
server:
  host: "0.0.0.0"          # 监听所有网络接口
  log_level: "info"        # 日志级别
  max_connections: 1000    # 最大连接数
```

### Shadowsocks配置

```yaml
shadowsocks:
  enabled: true            # 启用Shadowsocks
  port: 8388              # 监听端口
  method: "aes-256-gcm"   # 加密方法
  password: "your-strong-password"  # 密码
  timeout: 300            # 超时时间
```

**支持的加密方法**:
- `aes-128-gcm` (推荐)
- `aes-256-gcm` (推荐)
- `chacha20-ietf-poly1305` (推荐)
- `aes-128-cfb`
- `aes-256-cfb`

### SOCKS5配置

```yaml
socks5:
  enabled: true           # 启用SOCKS5
  port: 1080             # 监听端口
  username: "user"       # 用户名（可选）
  password: "pass"       # 密码（可选）
```

### HTTP代理配置

```yaml
http:
  enabled: true           # 启用HTTP代理
  port: 8080             # 监听端口
  username: "user"       # 用户名（可选）
  password: "pass"       # 密码（可选）
```

### VMess配置（高级）

```yaml
vmess:
  enabled: false          # 启用VMess
  port: 443              # 监听端口
  uuid: "12345678-1234-1234-1234-123456789abc"
  alter_id: 0            # 推荐设为0
  tls: true              # 启用TLS
  cert_file: "/path/to/cert.pem"
  key_file: "/path/to/key.pem"
```

### Trojan配置（高级）

```yaml
trojan:
  enabled: false          # 启用Trojan
  port: 443              # 监听端口
  password: "trojan-password"
  cert_file: "/path/to/cert.pem"
  key_file: "/path/to/key.pem"
```

## 🔒 SSL证书配置

VMess和Trojan协议需要SSL证书。推荐使用Let's Encrypt免费证书：

### 1. 安装Certbot

```bash
# Ubuntu/Debian
sudo apt install certbot

# CentOS/RHEL
sudo yum install certbot
```

### 2. 申请证书

```bash
# 使用standalone模式（需要停止其他Web服务）
sudo certbot certonly --standalone -d your-domain.com

# 证书文件位置
# 证书: /etc/letsencrypt/live/your-domain.com/fullchain.pem
# 私钥: /etc/letsencrypt/live/your-domain.com/privkey.pem
```

### 3. 配置自动续期

```bash
# 添加到crontab
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

## 🔥 防火墙配置

### UFW (Ubuntu/Debian)

```bash
# 允许SSH
sudo ufw allow 22/tcp

# 允许代理端口
sudo ufw allow 8388/tcp    # Shadowsocks
sudo ufw allow 1080/tcp    # SOCKS5
sudo ufw allow 8080/tcp    # HTTP代理
sudo ufw allow 443/tcp     # VMess/Trojan
sudo ufw allow 9999/tcp    # 管理界面

# 启用防火墙
sudo ufw enable
```

### FirewallD (CentOS/RHEL)

```bash
# 允许端口
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --permanent --add-port=8388/tcp
sudo firewall-cmd --permanent --add-port=1080/tcp
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --permanent --add-port=9999/tcp

# 重载配置
sudo firewall-cmd --reload
```

## 🔧 系统服务配置

### 创建systemd服务

```bash
# 创建服务文件
sudo tee /etc/systemd/system/clash-server.service > /dev/null << EOF
[Unit]
Description=Clash Compatible Proxy Server
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python server.py -c config.yaml
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 重载systemd
sudo systemctl daemon-reload

# 启用并启动服务
sudo systemctl enable clash-server
sudo systemctl start clash-server

# 查看状态
sudo systemctl status clash-server
```

### 管理命令

```bash
# 启动服务
sudo systemctl start clash-server

# 停止服务
sudo systemctl stop clash-server

# 重启服务
sudo systemctl restart clash-server

# 查看状态
sudo systemctl status clash-server

# 查看日志
sudo journalctl -u clash-server -f
```

## 📱 Clash客户端配置

### 自动生成配置

```bash
# 生成Clash客户端配置
python server.py -c config.yaml --generate-config

# 配置文件: clash_client_config.yaml
```

### 手动配置示例

```yaml
# Clash客户端配置
port: 7890
socks-port: 7891
allow-lan: true
mode: rule
log-level: info

proxies:
  # Shadowsocks节点
  - name: "我的SS服务器"
    type: ss
    server: your-server-ip
    port: 8388
    cipher: aes-256-gcm
    password: "your-password"
    udp: true

  # SOCKS5节点
  - name: "我的SOCKS5服务器"
    type: socks5
    server: your-server-ip
    port: 1080
    username: "user"
    password: "pass"

  # HTTP代理节点
  - name: "我的HTTP代理"
    type: http
    server: your-server-ip
    port: 8080
    username: "user"
    password: "pass"

proxy-groups:
  - name: "🚀 节点选择"
    type: select
    proxies:
      - "我的SS服务器"
      - "我的SOCKS5服务器"
      - "我的HTTP代理"
      - DIRECT

rules:
  - GEOIP,CN,DIRECT
  - MATCH,🚀 节点选择
```

## 📊 监控和管理

### Web管理界面

访问 `http://your-server-ip:9999` 查看：

- 实时流量统计
- 在线用户数量
- 协议使用情况
- 连接日志
- 服务器状态

### API接口

```bash
# 获取服务器状态
curl http://your-server-ip:9999/api/status

# 获取流量统计
curl http://your-server-ip:9999/api/traffic

# 获取活动连接
curl http://your-server-ip:9999/api/connections
```

## 🔍 故障排除

### 常见问题

#### 1. 端口被占用

```bash
# 查看端口占用
netstat -tlnp | grep :8388
lsof -i :8388

# 解决方案：更换端口或停止占用进程
```

#### 2. 防火墙阻止连接

```bash
# 检查防火墙状态
sudo ufw status
sudo firewall-cmd --list-all

# 确保开放了相应端口
```

#### 3. SSL证书问题

```bash
# 检查证书有效性
openssl x509 -in /etc/letsencrypt/live/your-domain.com/fullchain.pem -text -noout

# 检查证书到期时间
openssl x509 -in /etc/letsencrypt/live/your-domain.com/fullchain.pem -noout -dates
```

#### 4. 服务启动失败

```bash
# 查看详细日志
sudo journalctl -u clash-server -n 50

# 检查配置文件
python server.py --test-config config.yaml

# 检查Python环境
source venv/bin/activate
python --version
pip list
```

### 性能优化

#### 1. 系统参数优化

```bash
# 增加文件描述符限制
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# 优化网络参数
sudo tee -a /etc/sysctl.conf << EOF
net.core.rmem_max = 67108864
net.core.wmem_max = 67108864
net.core.netdev_max_backlog = 250000
net.core.somaxconn = 4096
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 1200
net.ipv4.ip_local_port_range = 10000 65000
net.ipv4.tcp_max_syn_backlog = 8192
net.ipv4.tcp_max_tw_buckets = 5000
EOF

# 应用配置
sudo sysctl -p
```

#### 2. 应用配置优化

```yaml
# config.yaml 性能配置
performance:
  workers: 0                    # 0表示自动检测CPU核心数
  connection_pool_size: 100     # 连接池大小
  buffer_size: 8192            # 缓冲区大小
  tcp_nodelay: true            # 禁用Nagle算法
  tcp_keepalive: true          # 启用TCP保活

advanced:
  timeouts:
    connect: 10                # 连接超时
    read: 300                 # 读取超时
    write: 300                # 写入超时
```

## 🔐 安全建议

### 1. 密码安全

```bash
# 生成强密码
openssl rand -base64 32

# 生成UUID
python3 -c "import uuid; print(str(uuid.uuid4()))"
```

### 2. 访问控制

```yaml
# config.yaml 安全配置
security:
  # IP白名单
  allowed_ips:
    - "192.168.1.0/24"
    - "10.0.0.0/8"
  
  # 连接限制
  max_connections_per_ip: 10
  
  # 流量限制 (MB/s)
  bandwidth_limit: 100
  
  # 防重放攻击
  replay_protection: true
```

### 3. 定期维护

```bash
# 定期更新系统
sudo apt update && sudo apt upgrade -y

# 定期备份配置
cp config.yaml config.yaml.backup.$(date +%Y%m%d)

# 定期查看日志
sudo journalctl -u clash-server --since "1 day ago"
```

## 📈 监控脚本

创建监控脚本 `monitor.sh`：

```bash
#!/bin/bash
# 服务器监控脚本

SERVICE_NAME="clash-server"
LOG_FILE="/var/log/clash-server-monitor.log"

# 检查服务状态
if ! systemctl is-active --quiet $SERVICE_NAME; then
    echo "$(date): 服务 $SERVICE_NAME 未运行，正在重启..." >> $LOG_FILE
    systemctl restart $SERVICE_NAME
fi

# 检查端口监听
if ! netstat -tlnp | grep -q ":8388"; then
    echo "$(date): 端口8388未监听，服务可能异常" >> $LOG_FILE
fi

# 检查内存使用
MEMORY_USAGE=$(ps -o pid,ppid,cmd,%mem,%cpu --sort=-%mem -C python3 | grep server.py | awk '{print $4}')
if (( $(echo "$MEMORY_USAGE > 80" | bc -l) )); then
    echo "$(date): 内存使用率过高: $MEMORY_USAGE%" >> $LOG_FILE
fi
```

添加到crontab：

```bash
# 每5分钟检查一次
echo "*/5 * * * * /path/to/monitor.sh" | crontab -
```

## 🎉 部署完成

恭喜！你已经成功部署了Clash兼容代理服务器。现在可以：

1. 使用生成的配置文件连接Clash客户端
2. 访问Web管理界面监控服务器状态
3. 根据需要调整配置和优化性能

如有问题，请查看故障排除部分或查看服务日志。