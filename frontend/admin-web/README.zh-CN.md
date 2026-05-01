<div align="center">
  <h1>FAN-CE UI</h1>
  <p>FAN-CE 后台管理前端工作区</p>
</div>

[English](./README.md) | [简体中文](./README.zh-CN.md)

## 简介

FAN-CE UI 是 FAN-CE 平台的后台管理前端代码库，当前主要用于承载后台页面，并通过后台 API 完成组学数据的管理、检索与展示。代码结构沿用了 monorepo 组织方式，但当前实际开发重点是 `apps/web-antd`。

> 当前活跃应用：`apps/web-antd`
>
> 其余应用和部分共享包主要作为模板能力保留，不是当前交付重点。

## 项目架构

本项目遵循 monorepo 结构，包含多个应用和共享包：

### 应用 (`/apps/`)

#### 🎨 **Web-Antd** (`/apps/web-antd/`)
基于以下技术构建的企业级管理系统：
- **Vue 3** + **TypeScript** 用于现代开发
- **Ant Design Vue** 作为 UI 组件库
- **Vite** 用于快速开发和构建
- **Pinia** 用于状态管理
- **Vue Router** 用于路由
- 丰富的功能，包括认证、权限、国际化和主题化

#### 🚀 **Web-Element** (`/apps/web-ele/`) - 模板保留
使用以下技术实现的管理后台模板：
- **Vue 3** + **TypeScript**
- **Element Plus** 作为 UI 框架
- 与其他应用共享核心功能

#### 💎 **Web-Naive** (`/apps/web-naive/`) - 模板保留
具有以下特点的现代管理界面模板：
- **Vue 3** + **TypeScript**
- **Naive UI** 作为组件库
- 所有应用架构一致

#### 🔧 **Backend-Mock** (`/apps/backend-mock/`) - 模板保留
提供以下功能的模拟后端服务：
- 用于开发的 API 模拟
- 数据模拟功能
- 开发环境支持

### 共享包 (`/packages/`)

- **@core**: 核心功能和基础组件
- **constants**: 共享常量和配置
- **effects**: 通用效果和实用程序（访问、布局、钩子、插件、请求）
- **icons**: 图标管理和组件
- **locales**: 国际化支持
- **preferences**: 用户偏好和设置
- **stores**: 共享状态管理
- **styles**: 通用样式和主题
- **types**: TypeScript 类型定义
- **utils**: 实用函数和助手

### 开发工具 (`/internal/`)

- **lint-configs**: ESLint、Prettier、Stylelint 配置
- **node-utils**: Node.js 实用程序
- **tailwind-config**: Tailwind CSS 配置
- **tsconfig**: TypeScript 配置
- **vite-config**: Vite 构建配置

## 主要特性

- **🏗️ Monorepo 架构**: 组织良好的代码库，包含共享包和多个应用
- **🎯 多框架支持**: 展示了跨 Ant Design Vue、Element Plus 和 Naive UI 的实现
- **⚡ 现代技术栈**: Vue 3、Vite、TypeScript、Pinia、Vue Router
- **🎨 一致的设计**: 跨不同 UI 框架的统一设计系统
- **🔧 开发工具**: 全面的 linting、格式化和构建配置
- **📦 包管理**: 使用 PNPM 工作区进行高效的依赖管理
- **🚀 性能优化**: 快速的开发和构建过程
- **🌐 国际化**: 内置 i18n 支持
- **🔐 认证与权限**: 基于角色的访问控制
- **📱 响应式设计**: 采用 Tailwind CSS 的移动优先方法

## 环境命令

本项目为不同的开发场景提供了各种特定于环境的命令：

### 开发命令
- `pnpm dev` - 在开发模式下启动所有应用
- `pnpm dev:antd` - 仅启动 Ant Design Vue 应用
- `pnpm dev:ele` - 仅启动 Element Plus 应用
- `pnpm dev:naive` - 仅启动 Naive UI 应用
- `pnpm dev:docs` - 启动文档网站
- `pnpm dev:play` - 启动 playground 应用

### 构建命令
- `pnpm build` - 为生产环境构建所有应用
- `pnpm build:antd` - 仅构建 Ant Design Vue 应用
- `pnpm build:ele` - 仅构建 Element Plus 应用
- `pnpm build:naive` - 仅构建 Naive UI 应用
- `pnpm build:docs` - 构建文档网站
- `pnpm build:analyze` - 使用包分析进行构建

### 其他命令
- `pnpm preview` - 预览构建的应用
- `pnpm clean` - 清理所有构建产物和依赖项
- `pnpm reinstall` - 清理并重新安装所有依赖项
- `pnpm check` - 运行所有检查（循环依赖、类型、拼写）
- `pnpm lint` - 运行 linting
- `pnpm format` - 格式化代码

## 安装和使用

1. 获取项目代码

```bash
git clone <repository-url>
cd fan-ce-ui
```

2. 安装依赖

```bash
# 启用 corepack 以使用 pnpm
npm i -g corepack

# 安装所有依赖
pnpm install
```

3. 开发

```bash
# 启动所有应用
pnpm dev

# 或启动特定应用
pnpm dev:antd    # Ant Design Vue 应用
pnpm dev:ele     # Element Plus 应用
pnpm dev:naive   # Naive UI 应用
```

4. 生产构建

```bash
# 构建所有应用
pnpm build

# 或构建特定应用
pnpm build:antd  # Ant Design Vue 应用
pnpm build:ele   # Element Plus 应用
pnpm build:naive # Naive UI 应用
```

## 配置

### 环境变量

项目使用环境变量进行配置。每个应用都有自己的一套配置文件：

#### Web-Antd 应用配置

配置文件位于 `/apps/web-antd/`：

- `.env` - 基础配置（所有环境共享）
- `.env.development` - 开发环境特定设置
- `.env.production` - 生产环境特定设置

#### 可用配置选项

**基础设置 (.env):**
```bash
# 在浏览器标签页和页眉中显示的应用标题
VITE_APP_TITLE=FAN

# 用于缓存和存储隔离的应用命名空间
VITE_APP_NAMESPACE=FanCE

# 用于存储持久化的加密密钥（请在生产环境中更改！）
VITE_APP_STORE_SECURE_KEY=please-replace-me-with-your-own-key
```

**开发设置 (.env.development):**
```bash
# 开发服务器端口（更改此项以使用不同端口）
VITE_PORT=5666

# 应用的基础路径
VITE_BASE=/

# API 端点 URL
VITE_GLOB_API_URL=/api/v1

# 启用/禁用 Nitro Mock 服务
VITE_NITRO_MOCK=false

# 启用/禁用 Vue DevTools
VITE_DEVTOOLS=false

# 启用/禁用全局加载注入
VITE_INJECT_APP_LOADING=false
```
