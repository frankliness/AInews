#!/bin/bash

set -e

echo "🔧 安装 Homebrew（如果未安装）"
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || true

echo "📦 配置 Homebrew 环境变量"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

echo "🐍 安装 pyenv 和 pyenv-virtualenv"
brew install pyenv pyenv-virtualenv

echo "🔄 写入 pyenv 初始化脚本"
echo 'eval "$(pyenv init --path)"' >> ~/.zprofile
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.zshrc
source ~/.zprofile
source ~/.zshrc

echo "🧪 安装 Python 3.11.8 并创建虚拟环境"
pyenv install 3.11.8 -s
pyenv virtualenv 3.11.8 ainews-env
pyenv activate ainews-env

echo "🌿 安装 direnv"
brew install direnv

echo "🔄 写入 direnv hook 到 .zshrc"
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc
source ~/.zshrc

echo "📁 创建示例 .envrc"
echo 'layout python' > .envrc
echo 'export OPENAI_API_KEY=sk-xxx-your-key' >> .envrc

echo "✅ 请在当前项目目录运行：direnv allow"

echo "✅ 初始化完成，请重新打开终端或 source ~/.zshrc 生效"
