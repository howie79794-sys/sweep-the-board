# Node.js 安装指南

## 方法1：使用nvm安装（推荐，已完成）

nvm (Node Version Manager) 已经安装并配置完成。

### 使用nvm

```bash
# 加载nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# 查看已安装的Node.js版本
nvm list

# 使用特定版本
nvm use <version>

# 安装最新LTS版本
nvm install --lts

# 设置默认版本
nvm alias default <version>
```

### 永久配置（添加到 ~/.bashrc 或 ~/.zshrc）

```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
```

## 方法2：使用Homebrew安装

如果您有Homebrew，可以使用：

```bash
brew install node
```

## 方法3：从官网下载安装包

1. 访问 https://nodejs.org/
2. 下载macOS安装包（推荐LTS版本）
3. 运行安装程序
4. 按照提示完成安装

## 验证安装

```bash
node --version
npm --version
```

## 如果遇到问题

如果命令提示找不到node或npm，请：

1. 重新打开终端窗口
2. 或者运行：
   ```bash
   source ~/.bashrc  # 或 source ~/.zshrc
   ```
