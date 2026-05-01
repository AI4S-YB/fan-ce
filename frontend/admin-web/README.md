<div align="center">
  <h1>FAN-CE UI</h1>
  <p>FAN-CE 后台管理前端</p>
</div>

[English](./README.md) | [简体中文](./README.zh-CN.md)

## Introduction

FAN-CE UI 是 FAN-CE 平台的后台管理前端工作区，当前主要承载后台系统前端页面，并通过后台 API 完成数据管理、查询和展示。代码保留了原始 monorepo 能力，但本项目当前聚焦 `apps/web-antd` 这一套后台管理界面。

> 当前活跃应用：`apps/web-antd`
>
> 其他应用与包主要作为历史模板或共享能力保留，不是当前交付重点。

### 核心特点

- **现代技术栈**：基于 Vue 3 Composition API 和 TypeScript 构建
- **多 UI 框架支持**：同时支持 Ant Design Vue、Element Plus、Naive UI、Shadcn Vue、Radix Vue 等多个 UI 组件库
- **高效包管理**：使用 pnpm workspace 进行 monorepo 管理
- **快速构建**：采用 Vite 作为构建工具，提供极速的开发体验
- **完整工具链**：集成 Tailwind CSS、Pinia、VueUse 等现代前端工具
- **企业级架构**：提供完整的应用层、核心包系统、内部工具和文档体系

## Project Architecture

项目采用 monorepo 架构，包含多个应用和共享包，提供完整的前端开发生态系统：

### 应用层 (`/apps/`)

#### 🎨 **Web-Antd** (`/apps/web-antd/`)
基于 Ant Design Vue 的企业级管理系统：
- **Vue 3** + **TypeScript** 现代化开发
- **Ant Design Vue** UI 组件库
- **Vite** 快速构建工具
- **Pinia** 状态管理
- **Vue Router** 路由管理
- 完整的认证、权限、国际化和主题功能

#### 🚀 **Web-Element** (`/apps/web-ele/`) - 模板保留
基于 Element Plus 的管理后台模板：
- **Vue 3** + **TypeScript**
- **Element Plus** UI 框架
- 与其他应用共享核心功能

#### 💎 **Web-Naive** (`/apps/web-naive/`) - 模板保留
基于 Naive UI 的现代化界面模板：
- **Vue 3** + **TypeScript**
- **Naive UI** 组件库
- 统一的架构设计

#### 🔧 **Backend-Mock** (`/apps/backend-mock/`) - 模板保留
后端模拟服务：
- 开发环境 API 模拟
- 数据模拟功能
- 开发环境支持

### 核心包系统 (`/packages/`)

- **@core**: 核心功能和基础组件
- **effects**: 通用效果和工具（访问控制、布局、钩子、插件、请求）
- **hooks**: Vue 组合式函数包
- **icons**: 图标管理和组件
- **locales**: 国际化支持
- **stores**: 共享状态管理
- **types**: TypeScript 类型定义
- **utils**: 工具函数和助手

### 内部工具 (`/internal/`)

- **eslint-config**: ESLint 配置包
- **stylelint-config**: Stylelint 配置包
- **tailwind-config**: Tailwind CSS 配置包
- **tsconfig**: TypeScript 配置包
- **vite-config**: Vite 构建配置包

### 文档和开发环境

- **docs/**: 项目文档（使用 VitePress）
- **playground/**: 开发测试和实验环境

## 技术优势

- **🏗️ Monorepo 架构**: 统一的代码库管理，共享包和多应用协同开发
- **🎯 多 UI 框架支持**: 支持 Ant Design Vue、Element Plus、Naive UI、Shadcn Vue、Radix Vue
- **⚡ 现代技术栈**: Vue 3 Composition API、Vite、TypeScript、Pinia、VueUse
- **🎨 统一设计系统**: 跨不同 UI 框架的一致性设计
- **🔧 完整工具链**: 全面的代码检查、格式化和构建配置
- **📦 高效包管理**: pnpm workspace 实现高效的依赖管理
- **🚀 性能优化**: 快速的开发和构建流程
- **🌐 国际化支持**: 内置 i18n 多语言支持
- **🔐 权限管理**: 基于角色的访问控制系统
- **📱 响应式设计**: 基于 Tailwind CSS 的移动优先设计
- **🛠️ 开发体验**: 集成 VitePress 文档、Playground 实验环境

## Environment Commands

This project provides various environment-specific commands for different development scenarios:

### Development Commands
- `pnpm dev` - Start all applications in development mode
- `pnpm dev:antd` - Start only the Ant Design Vue application
- `pnpm dev:ele` - Start only the Element Plus application
- `pnpm dev:naive` - Start only the Naive UI application
- `pnpm dev:docs` - Start the documentation site
- `pnpm dev:play` - Start the playground application

### Build Commands
- `pnpm build` - Build all applications for production
- `pnpm build:antd` - Build only the Ant Design Vue application
- `pnpm build:ele` - Build only the Element Plus application
- `pnpm build:naive` - Build only the Naive UI application
- `pnpm build:docs` - Build the documentation site
- `pnpm build:analyze` - Build with bundle analysis

### Other Commands
- `pnpm preview` - Preview built applications
- `pnpm clean` - Clean all build artifacts and dependencies
- `pnpm reinstall` - Clean and reinstall all dependencies
- `pnpm check` - Run all checks (circular dependencies, types, spelling)
- `pnpm lint` - Run linting
- `pnpm format` - Format code

## 环境要求

在开始使用本项目之前，请确保您的开发环境满足以下要求：

### 必需软件

| 软件 | 最低版本 | 推荐版本 | 说明 |
|------|----------|----------|------|
| **Node.js** | 20.10.0+ | 22.1.0 | JavaScript 运行环境 |
| **pnpm** | 9.12.0+ | 10.10.0 | 包管理器（比 npm 更快更高效） |
| **Git** | 2.0+ | 最新版本 | 版本控制工具 |

### 推荐开发工具

- **VS Code** - 推荐的代码编辑器
- **Chrome 80+** - 推荐的开发浏览器

### 检查环境

在开始之前，请在终端中运行以下命令检查您的环境：

```bash
# 检查 Node.js 版本
node --version
# 应该显示 v20.10.0 或更高版本

# 检查 Git 版本
git --version
# 应该显示 Git 版本信息

# 检查是否已安装 pnpm
pnpm --version
# 如果未安装，请参考下面的安装步骤
```

## 安装和使用

### 第一步：安装 pnpm 包管理器

如果您还没有安装 pnpm，请选择以下方式之一：

**方式一：使用 npm 安装（推荐）**
```bash
npm install -g pnpm
```

**方式二：使用 corepack（Node.js 16.13+ 内置）**
```bash
corepack enable
corepack prepare pnpm@latest --activate
```

**方式三：直接下载安装**
```bash
curl -fsSL https://get.pnpm.io/install.sh | sh -
```

### 第二步：获取项目代码

```bash
# 克隆项目到本地
git clone <repository-url>

# 进入项目目录
cd fan-ce-ui
```

### 第三步：安装项目依赖

```bash
# 安装所有依赖包（首次安装可能需要几分钟）
pnpm install
```

> **说明**：pnpm 会自动下载并安装项目所需的所有依赖包。由于项目采用 monorepo 架构，包含多个应用和共享包，首次安装可能需要一些时间。

### 第四步：启动开发服务器

**启动所有应用（适合全栈开发）：**
```bash
pnpm dev
```

**启动特定应用（推荐新手使用）：**
```bash
# 启动 Ant Design Vue 版本（企业级管理系统）
pnpm dev:antd
# 访问地址：http://localhost:5666

# 启动 Element Plus 版本
pnpm dev:ele
# 访问地址：http://localhost:5667

# 启动 Naive UI 版本
pnpm dev:naive
# 访问地址：http://localhost:5668

# 启动文档站点
pnpm dev:docs
# 访问地址：http://localhost:5173

# 启动实验环境
pnpm dev:play
# 访问地址：http://localhost:5555
```

### 第五步：在浏览器中查看

1. 打开您的浏览器（推荐使用 Chrome）
2. 访问对应的地址（如 http://localhost:5666）
3. 您应该能看到项目的登录页面或主界面

### 生产环境构建

当您需要部署到生产环境时：

```bash
# 构建所有应用
pnpm build

# 或构建特定应用
pnpm build:antd   # 构建 Ant Design Vue 版本
pnpm build:ele    # 构建 Element Plus 版本
pnpm build:naive  # 构建 Naive UI 版本
pnpm build:docs   # 构建文档站点
```

### 常见问题解决

**问题 1：端口被占用**
```bash
# 如果默认端口被占用，可以修改配置文件
# 编辑 apps/web-antd/.env.development
# 将 VITE_PORT=5666 改为其他端口号
```

**问题 2：依赖安装失败**
```bash
# 清理缓存并重新安装
pnpm clean
pnpm install
```

**问题 3：启动失败**
```bash
# 检查 Node.js 版本是否符合要求
node --version

# 重新安装依赖
pnpm reinstall
```

## Configuration

### Environment Variables

The project uses environment variables for configuration. Each application has its own set of configuration files:

#### Web-Antd Application Configuration

Configuration files are located in `/apps/web-antd/`:

- `.env` - Base configuration (shared across all environments)
- `.env.development` - Development environment specific settings
- `.env.production` - Production environment specific settings

#### Available Configuration Options

**Basic Settings (.env):**
```bash
# Application title displayed in browser tab and header
VITE_APP_TITLE=FAN

# Application namespace for cache and store isolation
VITE_APP_NAMESPACE=FanCE

# Encryption key for store persistence (change this in production!)
VITE_APP_STORE_SECURE_KEY=please-replace-me-with-your-own-key
```

**Development Settings (.env.development):**
```bash
# Development server port (change this to use a different port)
VITE_PORT=5666

# Base path for the application
VITE_BASE=/

# API endpoint URL
VITE_GLOB_API_URL=/api/v1

# Enable/disable Nitro Mock service
VITE_NITRO_MOCK=false

# Enable/disable Vue DevTools
VITE_DEVTOOLS=false

# Enable/disable global loading injection
VITE_INJECT_APP_LOADING=false
```

#### How to Change the Development Port

To run the application on a different port:

1. Open `/apps/web-antd/.env.development`
2. Modify the `VITE_PORT` value:
   ```bash
   # Change from default 5666 to your desired port
   VITE_PORT=3000
   ```
3. Restart the development server:
   ```bash
   pnpm dev:antd
   ```

The application will now be available at `http://localhost:3000` (or your chosen port).

#### Security Note

⚠️ **Important**: Always change the `VITE_APP_STORE_SECURE_KEY` in production environments to ensure data security.

## 项目结构

```
fan-ce-ui/
├── 根目录配置文件
│   ├── .editorconfig              # 编辑器配置
│   ├── .gitignore                 # Git 忽略文件配置
│   ├── .npmrc                     # npm 配置文件
│   ├── commitlint.config.js       # 提交信息规范配置
│   ├── lefthook.yml               # Git hooks 配置
│   ├── package.json               # 项目依赖和脚本配置
│   ├── pnpm-lock.yaml             # pnpm 锁定文件
│   ├── pnpm-workspace.yaml        # pnpm workspace 配置
│   ├── README.md                  # 项目说明文档
│   └── turbo.json                 # Turbo 构建配置
├── apps/                          # 应用层
│   ├── backend-mock/              # 后端模拟服务
│   ├── web-antd/                  # 基于 Ant Design Vue 的 Web 应用
│   ├── web-ele/                   # 基于 Element Plus 的 Web 应用
│   └── web-naive/                 # 基于 Naive UI 的 Web 应用
├── docs/                          # 文档
│   ├── .vitepress/                # VitePress 配置
│   ├── guide/                     # 使用指南
│   └── index.md                   # 文档首页
├── internal/                      # 内部工具
│   ├── eslint-config/             # ESLint 配置包
│   ├── stylelint-config/          # Stylelint 配置包
│   ├── tailwind-config/           # Tailwind CSS 配置包
│   ├── tsconfig/                  # TypeScript 配置包
│   └── vite-config/               # Vite 配置包
├── packages/                      # 核心包
│   ├── @core/                     # 核心功能包
│   ├── effects/                   # 效果和动画包
│   ├── hooks/                     # Vue 组合式函数包
│   ├── icons/                     # 图标包
│   ├── locales/                   # 国际化包
│   ├── stores/                    # 状态管理包
│   ├── types/                     # TypeScript 类型定义包
│   └── utils/                     # 工具函数包
└── playground/                    # 开发测试和实验环境
```

## Browser Support

The `Chrome 80+` browser is recommended for local development

Support modern browsers, not IE

| [<img src="https://raw.githubusercontent.com/alrra/browser-logos/master/src/edge/edge_48x48.png" alt="Edge" width="24px" height="24px" />](http://godban.github.io/browsers-support-badges/)</br>Edge | [<img src="https://raw.githubusercontent.com/alrra/browser-logos/master/src/firefox/firefox_48x48.png" alt="Firefox" width="24px" height="24px" />](http://godban.github.io/browsers-support-badges/)</br>Firefox | [<img src="https://raw.githubusercontent.com/alrra/browser-logos/master/src/chrome/chrome_48x48.png" alt="Chrome" width="24px" height="24px" />](http://godban.github.io/browsers-support-badges/)</br>Chrome | [<img src="https://raw.githubusercontent.com/alrra/browser-logos/master/src/safari/safari_48x48.png" alt="Safari" width="24px" height="24px" />](http://godban.github.io/browsers-support-badges/)</br>Safari |
| :-: | :-: | :-: | :-: |
| last 2 versions | last 2 versions | last 2 versions | last 2 versions |

## 技术栈

### 前端框架
- **Vue 3** - 渐进式 JavaScript 框架，采用 Composition API
- **TypeScript** - 类型安全的 JavaScript 超集
- **Vite** - 快速的前端构建工具
- **Pinia** - Vue 3 状态管理库
- **Vue Router** - Vue.js 官方路由管理器
- **VueUse** - Vue 组合式工具库
- **Tailwind CSS** - 实用优先的 CSS 框架

### UI 组件库
- **Ant Design Vue** - 企业级 UI 设计语言和组件库
- **Element Plus** - 基于 Vue 3 的桌面端组件库
- **Naive UI** - 现代化的 Vue 3 组件库
- **Shadcn Vue** - 现代化的组件库
- **Radix Vue** - 低级 UI 原语组件库

### 开发工具
- **pnpm** - 快速、节省磁盘空间的包管理器
- **Turbo** - 高性能构建系统
- **ESLint** - 代码质量检查工具
- **Prettier** - 代码格式化工具
- **Stylelint** - CSS 代码检查工具
- **Lefthook** - Git hooks 管理器
- **VitePress** - 基于 Vite 的静态站点生成器

## License

[MIT](./LICENSE)
