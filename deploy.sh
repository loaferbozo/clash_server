#!/bin/bash
# Clash兼容代理服务器一键部署脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 显示横幅
show_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                🚀 Clash兼容代理服务器部署脚本                  ║"
    echo "║                                                              ║"
    echo "║  支持协议: Shadowsocks, VMess, Trojan, SOCKS5, HTTP         ║"
    echo "║  完美兼容: Clash, ClashX, Clash for Windows                 ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查系统环境
check_system() {
    log_info "检查系统环境..."
    
    # 检查操作系统
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        log_success "操作系统: Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        log_success "操作系统: macOS"
    else
        log_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
    
    # 检查是否为root用户
    if [[ $EUID -eq 0 ]]; then
        log_warning "检测到root用户，建议使用普通用户运行"
    fi
}

# 检查并安装Python
install_python() {
    log_info "检查Python环境..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        log_success "Python版本: $PYTHON_VERSION"
        
        # 检查Python版本（需要3.7+）
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 7) else 1)"; then
            log_success "Python版本满足要求"
        else
            log_error "需要Python 3.7或更高版本"
            exit 1
        fi
    else
        log_info "Python3未安装，正在安装..."
        
        if [[ "$OS" == "linux" ]]; then
            # 检测Linux发行版
            if command -v apt-get &> /dev/null; then
                sudo apt-get update
                sudo apt-get install -y python3 python3-pip python3-venv
            elif command -v yum &> /dev/null; then
                sudo yum install -y python3 python3-pip
            elif command -v dnf &> /dev/null; then
                sudo dnf install -y python3 python3-pip
            else
                log_error "不支持的Linux发行版"
                exit 1
            fi
        elif [[ "$OS" == "macos" ]]; then
            if command -v brew &> /dev/null; then
                brew install python3
            else
                log_error "请先安装Homebrew: https://brew.sh/"
                exit 1
            fi
        fi
        
        log_success "Python3安装完成"
    fi
}

# 安装系统依赖
install_system_deps() {
    log_info "安装系统依赖..."
    
    if [[ "$OS" == "linux" ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y build-essential libssl-dev libffi-dev curl wget
        elif command -v yum &> /dev/null; then
            sudo yum groupinstall -y "Development Tools"
            sudo yum install -y openssl-devel libffi-devel curl wget
        elif command -v dnf &> /dev/null; then
            sudo dnf groupinstall -y "Development Tools"
            sudo dnf install -y openssl-devel libffi-devel curl wget
        fi
    elif [[ "$OS" == "macos" ]]; then
        # macOS通常已有必要的开发工具
        if ! command -v gcc &> /dev/null; then
            log_info "请安装Xcode Command Line Tools: xcode-select --install"
        fi
    fi
    
    log_success "系统依赖安装完成"
}

# 创建虚拟环境并安装Python依赖
setup_python_env() {
    log_info "设置Python环境..."
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        log_info "创建Python虚拟环境..."
        python3 -m venv venv
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装依赖
    if [ -f "requirements.txt" ]; then
        log_info "安装Python依赖包..."
        pip install -r requirements.txt
    else
        log_info "安装基础依赖包..."
        pip install asyncio aiohttp pyyaml cryptography
    fi
    
    log_success "Python环境设置完成"
}

# 生成配置文件
generate_config() {
    log_info "生成服务器配置..."
    
    # 获取服务器IP
    SERVER_IP=$(curl -s ifconfig.me || curl -s ipinfo.io/ip || echo "YOUR_SERVER_IP")
    
    # 生成随机密码
    SS_PASSWORD=$(openssl rand -base64 16)
    TROJAN_PASSWORD=$(openssl rand -base64 16)
    
    # 生成UUID（用于VMess）
    VMESS_UUID=$(python3 -c "import uuid; print(str(uuid.uuid4()))")
    
    # 创建配置文件
    cat > config.yaml << EOF
# Clash兼容代理服务器配置
server:
  host: "0.0.0.0"
  log_level: "info"
  max_connections: 1000

# Shadowsocks配置（推荐）
shadowsocks:
  enabled: true
  port: 8388
  method: "aes-256-gcm"
  password: "$SS_PASSWORD"
  timeout: 300

# SOCKS5配置
socks5:
  enabled: true
  port: 1080
  username: ""
  password: ""
  timeout: 300

# HTTP代理配置
http:
  enabled: true
  port: 8080
  username: ""
  password: ""
  timeout: 300

# VMess配置（需要SSL证书）
vmess:
  enabled: false
  port: 443
  uuid: "$VMESS_UUID"
  alter_id: 0
  tls: false

# Trojan配置（需要SSL证书）
trojan:
  enabled: false
  port: 443
  password: "$TROJAN_PASSWORD"

# Web管理界面
dashboard:
  enabled: true
  port: 9999
  username: "admin"
  password: "admin123"

# 安全配置
security:
  allowed_ips: []
  max_connections_per_ip: 10
  bandwidth_limit: 0
  replay_protection: true
EOF
    
    log_success "配置文件生成完成: config.yaml"
    
    # 生成Clash客户端配置
    cat > clash_client_config.yaml << EOF
# Clash客户端配置文件
port: 7890
socks-port: 7891
allow-lan: true
mode: rule
log-level: info

proxies:
  - name: "SS-${SERVER_IP}"
    type: ss
    server: ${SERVER_IP}
    port: 8388
    cipher: aes-256-gcm
    password: "${SS_PASSWORD}"
    udp: true

  - name: "SOCKS5-${SERVER_IP}"
    type: socks5
    server: ${SERVER_IP}
    port: 1080

  - name: "HTTP-${SERVER_IP}"
    type: http
    server: ${SERVER_IP}
    port: 8080

proxy-groups:
  - name: "🚀 节点选择"
    type: select
    proxies:
      - "SS-${SERVER_IP}"
      - "SOCKS5-${SERVER_IP}"
      - "HTTP-${SERVER_IP}"
      - DIRECT

rules:
  - GEOIP,CN,DIRECT
  - MATCH,🚀 节点选择
EOF
    
    log_success "Clash客户端配置生成完成: clash_client_config.yaml"
    
    # 显示配置信息
    echo
    log_info "服务器配置信息:"
    echo "  服务器IP: $SERVER_IP"
    echo "  Shadowsocks端口: 8388"
    echo "  Shadowsocks密码: $SS_PASSWORD"
    echo "  SOCKS5端口: 1080"
    echo "  HTTP代理端口: 8080"
    echo "  管理界面: http://$SERVER_IP:9999"
    echo
}

# 配置防火墙
setup_firewall() {
    log_info "配置防火墙..."
    
    # 检查防火墙类型
    if command -v ufw &> /dev/null; then
        # Ubuntu/Debian UFW
        sudo ufw allow 22/tcp      # SSH
        sudo ufw allow 8388/tcp    # Shadowsocks
        sudo ufw allow 1080/tcp    # SOCKS5
        sudo ufw allow 8080/tcp    # HTTP Proxy
        sudo ufw allow 9999/tcp    # Dashboard
        
        # 启用防火墙（如果未启用）
        sudo ufw --force enable
        
        log_success "UFW防火墙配置完成"
        
    elif command -v firewall-cmd &> /dev/null; then
        # CentOS/RHEL FirewallD
        sudo firewall-cmd --permanent --add-port=22/tcp
        sudo firewall-cmd --permanent --add-port=8388/tcp
        sudo firewall-cmd --permanent --add-port=1080/tcp
        sudo firewall-cmd --permanent --add-port=8080/tcp
        sudo firewall-cmd --permanent --add-port=9999/tcp
        sudo firewall-cmd --reload
        
        log_success "FirewallD防火墙配置完成"
        
    elif command -v iptables &> /dev/null; then
        # 传统iptables
        sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
        sudo iptables -A INPUT -p tcp --dport 8388 -j ACCEPT
        sudo iptables -A INPUT -p tcp --dport 1080 -j ACCEPT
        sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
        sudo iptables -A INPUT -p tcp --dport 9999 -j ACCEPT
        
        # 保存规则
        if command -v iptables-save &> /dev/null; then
            sudo iptables-save > /etc/iptables/rules.v4 2>/dev/null || true
        fi
        
        log_success "iptables防火墙配置完成"
    else
        log_warning "未检测到防火墙，请手动开放端口: 8388, 1080, 8080, 9999"
    fi
}

# 创建systemd服务
create_service() {
    log_info "创建系统服务..."
    
    CURRENT_DIR=$(pwd)
    CURRENT_USER=$(whoami)
    
    # 创建服务文件
    sudo tee /etc/systemd/system/clash-server.service > /dev/null << EOF
[Unit]
Description=Clash Compatible Proxy Server
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
Environment=PATH=$CURRENT_DIR/venv/bin
ExecStart=$CURRENT_DIR/venv/bin/python server.py -c config.yaml
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
    
    # 重载systemd并启用服务
    sudo systemctl daemon-reload
    sudo systemctl enable clash-server
    
    log_success "系统服务创建完成"
}

# 启动服务
start_service() {
    log_info "启动代理服务器..."
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 检查配置文件
    if python server.py --test-config config.yaml; then
        log_success "配置文件验证通过"
    else
        log_error "配置文件验证失败"
        exit 1
    fi
    
    # 启动systemd服务
    if command -v systemctl &> /dev/null; then
        sudo systemctl start clash-server
        sudo systemctl status clash-server --no-pager
        log_success "服务已启动，使用systemctl管理"
    else
        # 直接启动
        log_info "直接启动服务器..."
        nohup python server.py -c config.yaml > server.log 2>&1 &
        echo $! > server.pid
        log_success "服务器已在后台启动，PID: $(cat server.pid)"
    fi
}

# 显示部署结果
show_result() {
    SERVER_IP=$(curl -s ifconfig.me || curl -s ipinfo.io/ip || echo "YOUR_SERVER_IP")
    
    echo
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    🎉 部署完成！                              ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${BLUE}📊 服务器信息:${NC}"
    echo "  🌐 服务器IP: $SERVER_IP"
    echo "  🔒 Shadowsocks: $SERVER_IP:8388"
    echo "  🧦 SOCKS5: $SERVER_IP:1080"
    echo "  🌍 HTTP代理: $SERVER_IP:8080"
    echo "  📱 管理界面: http://$SERVER_IP:9999"
    echo
    echo -e "${BLUE}📱 Clash客户端配置:${NC}"
    echo "  📄 配置文件: clash_client_config.yaml"
    echo "  📋 复制配置文件内容到Clash客户端即可使用"
    echo
    echo -e "${BLUE}🛠️ 管理命令:${NC}"
    echo "  启动服务: sudo systemctl start clash-server"
    echo "  停止服务: sudo systemctl stop clash-server"
    echo "  重启服务: sudo systemctl restart clash-server"
    echo "  查看状态: sudo systemctl status clash-server"
    echo "  查看日志: sudo journalctl -u clash-server -f"
    echo
    echo -e "${BLUE}🔧 配置文件:${NC}"
    echo "  服务器配置: config.yaml"
    echo "  客户端配置: clash_client_config.yaml"
    echo
    echo -e "${YELLOW}⚠️  安全提醒:${NC}"
    echo "  1. 请及时修改默认密码"
    echo "  2. 建议启用防火墙和访问控制"
    echo "  3. 定期更新系统和软件"
    echo
}

# 主函数
main() {
    show_banner
    
    # 检查参数
    case "${1:-install}" in
        "install")
            check_system
            install_python
            install_system_deps
            setup_python_env
            generate_config
            setup_firewall
            create_service
            start_service
            show_result
            ;;
        "start")
            log_info "启动服务..."
            sudo systemctl start clash-server
            ;;
        "stop")
            log_info "停止服务..."
            sudo systemctl stop clash-server
            ;;
        "restart")
            log_info "重启服务..."
            sudo systemctl restart clash-server
            ;;
        "status")
            sudo systemctl status clash-server
            ;;
        "uninstall")
            log_info "卸载服务..."
            sudo systemctl stop clash-server 2>/dev/null || true
            sudo systemctl disable clash-server 2>/dev/null || true
            sudo rm -f /etc/systemd/system/clash-server.service
            sudo systemctl daemon-reload
            log_success "服务已卸载"
            ;;
        *)
            echo "用法: $0 {install|start|stop|restart|status|uninstall}"
            echo
            echo "  install   - 完整安装和配置"
            echo "  start     - 启动服务"
            echo "  stop      - 停止服务"
            echo "  restart   - 重启服务"
            echo "  status    - 查看状态"
            echo "  uninstall - 卸载服务"
            exit 1
            ;;
    esac
}

# 错误处理
trap 'log_error "部署过程中发生错误"; exit 1' ERR

# 执行主函数
main "$@"