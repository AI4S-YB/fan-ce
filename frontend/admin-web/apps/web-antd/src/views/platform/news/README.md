# 消息管理功能

## 功能说明
消息管理功能支持团队内部的信息发布和管理，包括新闻、会议、链接等类型的消息。

## 主要特性
- ✅ 完整的增删改查功能
- ✅ 富文本编辑器支持（超链接、格式化等）
- ✅ 三种消息类型：News（新闻）、Meeting（会议）、Links（链接）
- ✅ 权限控制集成
- ✅ 团队隔离（team_id）
- ✅ 公开/私有设置

## 页面结构
- `index.vue` - 主列表页面
- `Modal.vue` - 新增/编辑弹窗
- `data.ts` - 数据配置和API调用逻辑

## 系统配置要求

### 1. 字典数据配置
需要在系统字典中添加 `message_type` 字典，包含以下选项：

```sql
-- 字典类型
INSERT INTO dict (name, key, remark) VALUES ('消息类型', 'message_type', '消息管理中的类型分类');

-- 字典选项
INSERT INTO dict_field (dict_id, label, value, sort) VALUES 
(LAST_INSERT_ID(), '新闻', 'News', 1),
(LAST_INSERT_ID(), '会议', 'Meeting', 2),
(LAST_INSERT_ID(), '链接', 'Links', 3);
```

### 2. 权限配置
需要配置以下权限：
- `platform:news:list` - 列表查看
- `platform:news:add` - 新增消息  
- `platform:news:update` - 编辑消息
- `platform:news:delete` - 删除消息

### 3. 路由配置
路由已自动配置在 `/platform/news`

## API接口
所有API接口已对应后端：
- `POST /platform/list` - 获取消息列表
- `POST /platform/info` - 获取消息详情
- `POST /platform/add` - 新增消息
- `POST /platform/update` - 更新消息
- `POST /platform/delete` - 删除消息

## 使用说明
1. 访问 `/platform/news` 页面
2. 点击"新增"按钮创建消息
3. 在富文本编辑器中可以添加超链接和格式化内容
4. 支持按类型和标题搜索
5. 支持批量删除和单条操作

## 技术实现
- Vue 3 + TypeScript
- VxeGrid 表格组件
- Tinymce 富文本编辑器
- VbenForm 表单组件
- Pinia 状态管理
