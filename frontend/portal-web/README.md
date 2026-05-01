# Portal Web

当前目录已补齐一版最小可运行的前台站点骨架，用于承接公开 dataset 展示页。

设计约束：

- 前台不单独建设后端
- 前台统一调用后台后端提供的公开 API
- 当前最小接入接口是 `/api/v1/public/dataset/list`

开发启动：

```bash
cd /path/to/fan-ce/frontend/portal-web
corepack pnpm install
corepack pnpm dev
```

默认地址：

- `http://127.0.0.1:5677`
