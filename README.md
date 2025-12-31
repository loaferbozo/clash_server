# 🚀 Clash兼容代理服务器

## 📋 项目概述

这是一个专门为Clash客户端设计的多协议代理服务器，支持Clash客户端直接连接使用。

## 🎯 支持的协议

### ✅ 已实现协议
- **Shadowsocks** - 最流行的代理协议
- **SOCKS5** - 通用代理协议  
- **HTTP/HTTPS** - Web代理协议
- **Trojan** - 伪装HTTPS流量
- **VMess** - V2Ray核心协议

### 🌟 核心特性
- 🔒 **多重加密** - AES-256-GCM, ChaCha20-Poly1305等
- 🌐 **多端口监听** - 同时支持多种协议
- 📊 **流量统计** - 实时监控和日志
- 🛡️ **安全防护** - 防重放攻击，连接限制
- 🚀 **高性能** - 异步处理，支持高并发

## 🏗️ 服务器架构

```
┌─────────────────────────────────────────────────────────────┐
│                   Clash兼容代理服务器                        │
├─────────────────────────────────────────────────────────────┤
│  🌐 Protocol Listeners                                     │
│  ├── Shadowsocks Server    :8388                          │
│  ├── VMess Server          :443                           │
│  ├── Trojan Server         :443                           │
│  ├── SOCKS5 Server         :1080                          │
│  └── HTTP Proxy Server     :8080                          │
├─────────────────────────────────────────────────────────────┤
│  🔒 Encryption & Security                                  │
│  ├── AES-256-GCM                                          │
│  ├── ChaCha20-Poly1305                                    │
│  ├── TLS/SSL Support                                      │
│  └── Anti-Replay Protection                               │
├─────────────────────────────────────────────────────────────┤
│  🧠 Core Services                                          │
│  ├── Connection Manager                                   │
│  ├── Traffic Router                                       │
│  ├── User Authentication                                  │
│  └── Bandwidth Control                                    │
├─────────────────────────────────────────────────────────────┤
│  📊 Monitoring & Management                                │
│  ├── Web Dashboard                                        │
│  ├── API Interface                                        │
│  ├── Traffic Statistics                                   │
│  └── Connection Logs                                      │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速部署

### 方式1: Docker部署（推荐）
```bash
# 克隆项目
git clone <repo>
cd clash_server

# 一键部署
docker-compose up -d
```

### 方式2: 直接运行
```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务器
python server.py -c config.yaml
```

## 📱 Clash客户端配置

服务器启动后，Clash客户端可以使用以下配置连接：

### Shadowsocks配置
```yaml
proxies:
  - name: "我的SS服务器"
    type: ss
    server: your-server-ip
    port: 8388
    cipher: aes-256-gcm
    password: "your-password"
    udp: true
```

### VMess配置
```yaml
proxies:
  - name: "我的VMess服务器"
    type: vmess
    server: your-server-ip
    port: 443
    uuid: "your-uuid"
    alterId: 0
    cipher: auto
    tls: true
    network: ws
    ws-opts:
      path: "/vmess"
```

### Trojan配置
```yaml
proxies:
  - name: "我的Trojan服务器"
    type: trojan
    server: your-server-ip
    port: 443
    password: "your-trojan-password"
    sni: your-domain.com
    udp: true
```

## 🔧 服务器配置

### 基础配置 (config.yaml)
```yaml
# 服务器基础配置
server:
  host: "0.0.0.0"
  log_level: "info"
  max_connections: 1000

# Shadowsocks配置
shadowsocks:
  enabled: true
  port: 8388
  method: "aes-256-gcm"
  password: "your-strong-password"
  timeout: 300

# VMess配置
vmess:
  enabled: true
  port: 443
  uuid: "12345678-1234-1234-1234-123456789abc"
  alter_id: 0
  tls: true
  cert_file: "/path/to/cert.pem"
  key_file: "/path/to/key.pem"

# Trojan配置
trojan:
  enabled: true
  port: 443
  password: "your-trojan-password"
  cert_file: "/path/to/cert.pem"
  key_file: "/path/to/key.pem"

# SOCKS5配置
socks5:
  enabled: true
  port: 1080
  username: "user"
  password: "pass"

# HTTP代理配置
http:
  enabled: true
  port: 8080
  username: "user"
  password: "pass"
```

## 📊 管理界面

访问 `http://your-server:9999` 查看：
- 📈 实时流量统计
- 👥 在线用户列表
- 📋 连接日志
- ⚙️ 服务器配置

## 🛡️ 安全特性

- **加密传输** - 所有数据端到端加密
- **防重放攻击** - 时间戳验证
- **连接限制** - 防止滥用
- **IP白名单** - 访问控制
- **流量限制** - 带宽管理

## 🌍 部署建议

### 1. VPS选择
- **地理位置** - 选择目标地区的服务器
- **带宽** - 至少100Mbps
- **内存** - 推荐2GB以上
- **系统** - Ubuntu 20.04+ / CentOS 8+

### 2. 域名和证书
```bash
# 申请免费SSL证书
certbot --nginx -d your-domain.com

# 自动续期
echo "0 12 * * * /usr/bin/certbot renew --quiet" | crontab -
```

### 3. 防火墙配置
```bash
# 开放必要端口
ufw allow 22/tcp      # SSH
ufw allow 80/tcp      # HTTP
ufw allow 443/tcp     # HTTPS/VMess/Trojan
ufw allow 8388/tcp    # Shadowsocks
ufw allow 1080/tcp    # SOCKS5
ufw allow 8080/tcp    # HTTP Proxy
ufw enable
```

## 📈 性能优化

### 系统优化
```bash
# 增加文件描述符限制
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# 优化网络参数
echo "net.core.rmem_max = 67108864" >> /etc/sysctl.conf
echo "net.core.wmem_max = 67108864" >> /etc/sysctl.conf
sysctl -p
```

### 应用优化
- 使用uvloop加速事件循环
- 启用连接池复用
- 配置适当的超时时间
- 使用高效的加密算法

## 🔍 故障排除

### 常见问题

1. **连接失败**
   ```bash
   # 检查端口监听
   netstat -tlnp | grep :8388
   
   # 检查防火墙
   ufw status
   ```

2. **SSL证书问题**
   ```bash
   # 验证证书
   openssl x509 -in cert.pem -text -noout
   
   # 测试HTTPS
   curl -I https://your-domain.com
   ```

3. **性能问题**
   ```bash
   # 监控资源使用
   htop
   iotop
   
   # 检查连接数
   ss -s
   ```

## 📞 技术支持

- 📖 详细文档：查看各协议实现文档
- 🐛 问题报告：提供日志和配置信息
- 💬 社区支持：加入技术交流群

---

**让你的服务器完美支持Clash客户端！** 🎉