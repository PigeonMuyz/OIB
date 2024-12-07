#!/bin/bash

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为 macOS
check_os() {
    if [ "$(uname)" != "Darwin" ]; then
        echo -e "${RED}错误: 此脚本仅支持 macOS${NC}"
        exit 1
    fi
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查并安装 Homebrew
check_brew() {
    if ! command_exists brew; then
        echo -e "${YELLOW}Homebrew 未安装，正在安装...${NC}"
        /bin/bash -c "$(curl -fsSL https://mirrors.ustc.edu.cn/brew.git/)"

        # 配置 Homebrew 环境变量
        if [ -f ~/.zshrc ]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
            echo 'export HOMEBREW_BOTTLE_DOMAIN="https://mirrors.ustc.edu.cn/homebrew-bottles"' >> ~/.zshrc
            echo 'export HOMEBREW_API_DOMAIN="https://mirrors.ustc.edu.cn/homebrew-bottles/api"' >> ~/.zshrc
            source ~/.zshrc
        elif [ -f ~/.bash_profile ]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.bash_profile
            echo 'export HOMEBREW_BOTTLE_DOMAIN="https://mirrors.ustc.edu.cn/homebrew-bottles"' >> ~/.bash_profile
            echo 'export HOMEBREW_API_DOMAIN="https://mirrors.ustc.edu.cn/homebrew-bottles/api"' >> ~/.bash_profile
            source ~/.bash_profile
        fi
    else
        echo -e "${GREEN}Homebrew 已安装${NC}"
    fi
}

# 检查并安装 Python 3.11
check_python() {
    if ! command_exists python3.11; then
        echo -e "${YELLOW}Python 3.11 未安装，正在安装...${NC}"
        brew install python@3.11

        # 设置 Python 3.11 为默认版本
        if [ -f ~/.zshrc ]; then
            echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.zshrc
            source ~/.zshrc
        elif [ -f ~/.bash_profile ]; then
            echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.bash_profile
            source ~/.bash_profile
        fi
    else
        echo -e "${GREEN}Python 3.11 已安装${NC}"
    fi
}

# 检查并安装 pip
check_pip() {
    if ! command_exists pip3; then
        echo -e "${YELLOW}pip3 未安装，正在安装...${NC}"
        python3.11 -m ensurepip --upgrade
    else
        echo -e "${GREEN}pip3 已安装${NC}"
    fi
}

# 安装 requirements.txt 中的依赖
install_requirements() {
    if [ ! -f "requirements.txt" ]; then
        echo -e "${RED}错误: requirements.txt 文件不存在${NC}"
        exit 1
    fi

    echo -e "${YELLOW}正在更新 pip...${NC}"
    python3.11 -m pip install --upgrade pip

    echo -e "${YELLOW}正在安装项目依赖...${NC}"
    # 首先尝试阿里云源
    python3.11 -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ || \
    # 如果失败，尝试官方源
    python3.11 -m pip install -r requirements.txt -i https://pypi.org/simple

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}依赖安装完成！${NC}"
    else
        echo -e "${RED}依赖安装失败，请检查错误信息${NC}"
        exit 1
    fi
}

# 主函数
main() {
    echo -e "${YELLOW}开始检查环境...${NC}"

    # 检查操作系统
    check_os

    # 检查并安装必要组件
    check_brew
    check_python
    check_pip

    # 安装项目依赖
    install_requirements

    echo -e "${GREEN}安装过程完成！${NC}"
    echo -e "${YELLOW}如果遇到权限问题，请尝试使用 sudo ./install.sh${NC}"
}

# 执行主函数
main
