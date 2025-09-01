#!/bin/bash

# Phoenix系统 Ubuntu服务器自动部署脚本
# 使用方法: ./scripts/deploy_to_ubuntu.sh

set -e

echo "🚀 Phoenix系统 Ubuntu服务器部署脚本"
echo "=================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要使用root用户运行此脚本"
        exit 1
    fi
}

# 检查系统要求
check_system() {
    log_info "检查系统要求..."
    
    # 检查操作系统
    if [[ ! -f /etc/os-release ]]; then
        log_error "无法检测操作系统"
        exit 1
    fi
    
    source /etc/os-release
    if [[ "$ID" != "ubuntu" ]]; then
        log_warning "此脚本专为Ubuntu设计，当前系统: $ID"
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # 检查内存
    total_mem=$(free -m | awk 'NR==2{printf "%.0f", $2/1024}')
    if [[ $total_mem -lt 4 ]]; then
        log_warning "建议至少4GB内存，当前: ${total_mem}GB"
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # 检查磁盘空间
    available_space=$(df -BG / | awk 'NR==2{print $4}' | sed 's/G//')
    if [[ $available_space -lt 20 ]]; then
        log_warning "建议至少20GB可用空间，当前: ${available_space}GB"
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log_success "系统要求检查通过"
}

# 更新系统
update_system() {
    log_info "更新系统包..."
    sudo apt update && sudo apt upgrade -y
    log_success "系统更新完成"
}

# 安装基础工具
install_basic_tools() {
    log_info "安装基础工具..."
    sudo apt install -y curl wget git unzip software-properties-common \
        apt-transport-https ca-certificates gnupg lsb-release
    log_success "基础工具安装完成"
}

# 安装Docker
install_docker() {
    log_info "安装Docker..."
    
    # 检查Docker是否已安装
    if command -v docker &> /dev/null; then
        log_info "Docker已安装，跳过安装步骤"
        return
    fi
    
    # 添加Docker官方GPG密钥
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # 添加Docker仓库
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # 安装Docker
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # 配置Docker用户组
    sudo usermod -aG docker $USER
    
    # 启动Docker服务
    sudo systemctl start docker
    sudo systemctl enable docker
    
    log_success "Docker安装完成"
    log_warning "请重新登录或运行 'newgrp docker' 以应用用户组更改"
}

# 安装Docker Compose
install_docker_compose() {
    log_info "安装Docker Compose..."
    
    # 检查Docker Compose是否已安装
    if command -v docker-compose &> /dev/null; then
        log_info "Docker Compose已安装，跳过安装步骤"
        return
    fi
    
    # 下载Docker Compose
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    
    # 设置执行权限
    sudo chmod +x /usr/local/bin/docker-compose
    
    log_success "Docker Compose安装完成"
}

# 配置防火墙
configure_firewall() {
    log_info "配置防火墙..."
    
    # 安装UFW
    sudo apt install -y ufw
    
    # 配置防火墙规则
    sudo ufw allow ssh
    sudo ufw allow 8082  # Phoenix Airflow Web界面
    sudo ufw allow 5051  # Phoenix pgAdmin
    sudo ufw allow 5434  # Phoenix PostgreSQL（如果需要外部访问）
    
    # 启用防火墙
    echo "y" | sudo ufw enable
    
    log_success "防火墙配置完成"
}

# 部署Phoenix系统
deploy_phoenix() {
    log_info "部署Phoenix系统..."
    
    # 创建项目目录
    sudo mkdir -p /opt/phoenix
    sudo chown $USER:$USER /opt/phoenix
    
    # 检查是否已存在项目
    if [[ -d "/opt/phoenix/.git" ]]; then
        log_info "项目已存在，更新代码..."
        cd /opt/phoenix
        git pull origin main
    else
        log_info "克隆项目代码..."
        cd /opt/phoenix
        git clone https://github.com/frankliness/AInews.git .
    fi
    
    # 创建必要目录
    mkdir -p logs exports
    chmod 755 logs exports
    
    # 创建环境配置文件
    if [[ ! -f ".env" ]]; then
        log_info "创建环境配置文件..."
        cat > .env << 'EOF'
# Phoenix系统环境配置
POSTGRES_USER=phoenix_user
POSTGRES_PASSWORD=phoenix_pass
POSTGRES_DB=phoenix_db
PGADMIN_DEFAULT_EMAIL=phoenix@example.com
PGADMIN_DEFAULT_PASSWORD=phoenix123

# 时区设置
TZ=Asia/Shanghai
PGTZ=Asia/Shanghai

# API密钥配置（请替换为您的实际密钥）
EVENTREGISTRY_API_KEY=your_eventregistry_api_key_here
NEWSAPI_API_KEY=your_newsapi_key_here
OPENAI_API_KEY=your_openai_api_key_here
EOF
        log_warning "请编辑 .env 文件，配置您的API密钥"
    fi
    
    # 启动Phoenix系统
    log_info "启动Phoenix系统..."
    docker-compose -f docker-compose.phoenix.yml up -d
    
    log_success "Phoenix系统部署完成"
}

# 验证部署
verify_deployment() {
    log_info "验证部署..."
    
    # 等待服务启动
    sleep 30
    
    # 检查容器状态
    if docker-compose -f docker-compose.phoenix.yml ps | grep -q "Up"; then
        log_success "所有服务已启动"
    else
        log_error "部分服务启动失败"
        docker-compose -f docker-compose.phoenix.yml ps
        exit 1
    fi
    
    # 测试数据库连接
    if docker-compose -f docker-compose.phoenix.yml exec -T phoenix-webserver python -c "
from sqlalchemy import create_engine
engine = create_engine('postgresql+psycopg2://phoenix_user:phoenix_pass@postgres-phoenix:5432/phoenix_db')
print('数据库连接成功！')
" 2>/dev/null; then
        log_success "数据库连接正常"
    else
        log_warning "数据库连接测试失败，请检查日志"
    fi
    
    log_success "部署验证完成"
}

# 显示访问信息
show_access_info() {
    echo
    echo "🎉 Phoenix系统部署完成！"
    echo "========================"
    echo
    echo "📱 访问信息："
    echo "  Phoenix Airflow UI: http://$(hostname -I | awk '{print $1}'):8082"
    echo "    用户名: phoenix_admin"
    echo "    密码: phoenix123"
    echo
    echo "  Phoenix pgAdmin: http://$(hostname -I | awk '{print $1}'):5051"
    echo "    用户名: phoenix@example.com"
    echo "    密码: phoenix123"
    echo
    echo "🔧 管理命令："
    echo "  启动服务: docker-compose -f docker-compose.phoenix.yml up -d"
    echo "  停止服务: docker-compose -f docker-compose.phoenix.yml down"
    echo "  查看日志: docker-compose -f docker-compose.phoenix.yml logs"
    echo
    echo "⚠️  重要提醒："
    echo "  1. 请编辑 /opt/phoenix/.env 文件，配置您的API密钥"
    echo "  2. 建议配置Nginx反向代理以提高安全性"
    echo "  3. 定期备份数据库和配置文件"
    echo
}

# 主函数
main() {
    check_root
    check_system
    
    echo
    log_info "开始部署Phoenix系统..."
    echo
    
    update_system
    install_basic_tools
    install_docker
    install_docker_compose
    configure_firewall
    deploy_phoenix
    verify_deployment
    show_access_info
    
    log_success "部署完成！"
}

# 运行主函数
main "$@"
