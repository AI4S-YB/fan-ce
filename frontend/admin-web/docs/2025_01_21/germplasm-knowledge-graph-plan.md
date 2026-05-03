# 种质资源知识图谱可视化方案

## 文档信息
- 创建时间: 2025-01-21
- 项目: fan-ui-poc 
- 模块: germplasm（种质资源管理）

## 1. 需求背景

### 1.1 当前问题
- 现有种质资源管理采用表格形式展示，无法直观体现种质间的血缘关系
- 用户需要手动选择两个节点才能查看关系，交互效率低
- 缺乏整体网络结构的可视化展示

### 1.2 目标需求
- 以图谱形式直观展示种质资源间的父子、母子关系
- 支持交互式操作，方便用户探索种质血缘网络
- 基于现有技术栈实现，减少学习成本

## 2. 技术现状分析

### 2.1 后端数据架构
- **当前主数据源**: PostgreSQL breeding 表
- **核心表**:
  - `brd_germplasm`
  - `brd_germplasm_lineage`
  - `brd_germplasm_import_batch`
- **关系类型**:
  - `father`
  - `mother`
- **说明**:
  - 早期 Excel + PKL 图谱方案已经退场
  - 当前图谱查询统一从 breeding PG 数据派生

### 2.2 前端技术栈
- **框架**: Vue 3 + TypeScript + Ant Design Vue
- **图表库**: 已集成ECharts，但缺少Graph组件
- **当前展示**: 基于VXE表格的列表展示
- **交互限制**: 最多选择两个节点查看关系

### 2.3 现有API接口
- `/breeding/germplasm/list`: 获取种质列表
- `/breeding/germplasm/info`: 获取单个种质详情
- `/breeding/germplasm/relationship`: 查询两个节点间的关系
- `/breeding/germplasm/relationships/batch`: 获取选中节点图谱
- `/breeding/germplasm/statistics`: 获取图统计信息

## 3. 方案设计

### 3.1 方案一：基于现有数据的简单版本（当前实施）

#### 3.1.1 技术选型
- **可视化库**: D3.js
- **数据来源**: `/breeding/germplasm/relationships/batch` 和 `/breeding/germplasm/list`
- **实现策略**: 直接消费 PG 派生图谱，不再从 neighbors 反推边关系

#### 3.1.2 数据结构设计

```typescript
// 图谱节点结构
interface KnowledgeGraphNode {
  id: string;                       // 节点唯一标识
  label: string;                    // 显示标签
  degree: number;                   // 连接度数
  size?: number;                    // 节点大小（基于degree计算）
  color?: string;                   // 节点颜色
  attributes: Record<string, any>;  // 详细属性
}

// 图谱边结构  
interface KnowledgeGraphEdge {
  id: string;                       // 边唯一标识
  source: string;                   // 源节点ID
  target: string;                   // 目标节点ID
  relationshipType?: 'unknown';     // 关系类型（当前版本未知）
}

// 完整图谱数据
interface KnowledgeGraphData {
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
  metadata: {
    totalNodes: number;
    totalEdges: number;
    maxDegree: number;
    minDegree: number;
  };
}
```

#### 3.1.3 交互功能设计

**基础交互**:
- 拖拽节点调整布局
- 缩放和平移画布
- 节点悬停显示详情
- 节点点击高亮相关连接

**高级交互**:
- 搜索节点并高亮
- 根据连接度过滤显示
- 子图提取（显示选定节点的邻居）
- 布局算法切换（力导向、圆形等）

#### 3.1.4 实现计划

1. **创建D3图谱组件**: `KnowledgeGraph.vue`
2. **数据转换逻辑**: 将list数据转换为图数据
3. **集成到germplasm模块**: 新增图谱视图页面
4. **基础交互实现**: 拖拽、缩放、悬停等

#### 3.1.5 局限性
- 无法区分关系类型（父子vs杂交）
- 基于neighbors构建的边可能不准确
- 缺少关系的详细信息（权重、时间等）

### 3.2 方案二：完整图数据接口方案（备选）

#### 3.2.1 新增后端接口
```python
@germplasm_router.post("/graph")
async def get_germplasm_graph_data(
    file_path: str,
    limit: int = 100
) -> GraphDataResponse:
    """获取完整图数据，包含节点和边信息"""
```

#### 3.2.2 完整数据结构
```typescript
interface GraphEdge {
  source: string;
  target: string;
  relationshipType: 'parent-offspring' | 'crossing';
  weight: number;
  createdAt?: string;
}
```

#### 3.2.3 优势
- 精确的关系类型信息
- 支持关系过滤和分类显示
- 更丰富的可视化效果
- 支持时间维度分析

## 4. 实施步骤

### 阶段1：简单版本实现（当前）
1. 创建KnowledgeGraph组件
2. 实现基础D3可视化
3. 集成到germplasm模块
4. 测试和优化

### 阶段2：功能增强（基于效果评估）
- 如果简单版本效果不佳，实施方案二
- 如果效果良好，基于现有版本继续优化
- 增加高级交互功能
- 性能优化和大数据支持

## 5. 技术风险与对策

### 5.1 风险点
- D3.js学习成本相对较高
- 大数据量下的性能问题
- 布局算法选择和参数调优
- 浏览器兼容性问题

### 5.2 对策
- 采用渐进式实现策略
- 实施数据分页和虚拟化
- 提供多种布局算法选项
- 充分测试主流浏览器

## 6. 预期效果

### 6.1 用户体验提升
- 直观的血缘关系可视化
- 流畅的交互操作体验
- 快速的信息查找和定位

### 6.2 功能价值
- 提高种质资源管理效率
- 支持复杂血缘关系分析
- 为育种决策提供可视化支持

## 7. 后续扩展

- 支持时间维度的动态图谱
- 集成AI推荐相似种质
- 导出图谱为图片或PDF
- 支持多数据源图谱合并
- 添加图谱分析算法（聚类、路径分析等）
