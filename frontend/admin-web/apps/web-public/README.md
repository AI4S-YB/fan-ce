# Web Public — 公开门户模板

这是 FAN-CE 的默认公开门户前端。基于 Element Plus + Vue 3，通过 `/api/v1/public/*` 接口获取数据。

## 快速开始（单站点）

大多数场景只需要一个公开门户，直接使用本模板即可：

```bash
# 1. 配置站点标识
echo "VITE_SITE_CODE=default" > .env

# 2. 开发
pnpm -F @fan-ce/web-public dev

# 3. 构建
pnpm -F @fan-ce/web-public build
# dist/ 部署到 nginx
```

## 创建新站点（多站点）

当需要多个外观不同的公开门户时（如水稻网、小麦网），从本模板复制一份，独立修改：

### 1. 复制模板

```bash
cp -r apps/web-public apps/web-public-<site_code>
```

例如创建水稻网站：

```bash
cp -r apps/web-public apps/web-public-rice
```

### 2. 修改站点标识

编辑 `apps/web-public-rice/.env`：

```env
VITE_SITE_CODE=rice
```

### 3. 注册到 pnpm workspace

在 `pnpm-workspace.yaml` 中不需要额外配置——`apps/*` 通配符已自动包含。

### 4. 在 Admin 后台创建站点

登录管理后台 → 平台管理 → 站点管理 → 新建：

- `site_code`: `rice`
- `site_name`: `水稻种质资源网`
- `domain`: `rice.example.com`
- `test_port`: `5679`

### 5. 自定义外观

每个站点可以独立修改：

| 层级 | 内容 | 难度 |
|---|---|---|
| 低 | `.env` 改标题、logo URL | 无需改代码 |
| 中 | `src/assets/` 换图片、`src/styles/` 改配色 | 改 CSS |
| 高 | `src/views/` 改布局、增删组件 | 改 Vue 组件 |
| 尽 | 从模板 fork，完全自由开发 | 独立项目 |

### 6. 构建部署

```bash
pnpm -F @fan-ce/web-public-rice build
# dist/ 部署到 nginx: server_name rice.example.com
```

## 站点间关系

```
web-public          ← 模板（默认站点，site_code=default）
web-public-rice     ← 水稻站（独立修改，不影响模板）
web-public-wheat    ← 小麦站（独立修改，不影响模板）
```

每个站点是**独立副本**，互不影响。共享的是 `packages/` 里的公共代码（API 客户端、i18n 等）。修改公共代码时所有站点同步受益。

## API 说明

公开门户使用无需认证的公开 API：

| 接口 | 说明 |
|---|---|
| `GET /api/v1/public/site/info` | 获取站点标题、logo、联系方式 |
| `GET /api/v1/public/datasets` | 获取当前站点可见的数据集列表 |
| `GET /api/v1/public/datasets/{id}` | 获取数据集详情 |

站点识别由后端通过 Host 头自动完成，前端无需传 site_code。
