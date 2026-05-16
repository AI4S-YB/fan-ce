## FAN-CE
FAN-CE is a comprehensive API platform designed for managing and analyzing biological data. This system provides:

- Efficient storage and retrieval of multi-omics data
- User management with role-based access control (RBAC)
- Powerful search capabilities across genomic and expression datasets
- RESTful API endpoints for bioinformatics analysis
- Integration with common bioinformatics tools and workflows

Built with FastAPI and Python 3.10, FAN-CE aims to streamline bioinformatics research by providing a centralized platform for data management, analysis, and collaboration. The system supports various data types including genomic sequences, expression data, and biological project metadata.

## 运行条件
> 列出运行该项目所必须的条件和相关依赖  
* 条件一
* 条件二
* 条件三



## 运行说明
> 说明如何运行和使用你的项目，建议给出具体的步骤说明
* 操作一
* 操作二
* 操作三  



## 测试说明
> 如果有测试相关内容需要说明，请填写在这里  



## 技术架构
> 使用的技术框架或系统架构图等相关说明，请填写在这里  


## 协作者
> 高效的协作会激发无尽的创造力，将他们的名字记录在这里吧


### Install FastAPI 

#### using conda to create virtual env
```
conda create -n fance python=3.10
conda activate fance
pip install -r requirements.txt
```

#### using venv 

```
python -m venv fapi
source fapi/bin/activate
pip install -r requirements.txt
```


### Run the FAN-CE API app

```
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```


### 目录定义 
- config: 项目配置信息
- db: 数据库相关配置信息
- app1: 应用程序
   - model: API的模型
   - schema: 数据库表中关于映射的ORM模型
   - api: API路由接口
- service: 数据查询逻辑
- utils: 其它


- models
   - c_user.py
   - c_bioproject.py
   - genome.py
- api
   - c_user.py
   - c_bioproject.py
   - d_genome.py
   - d_expression.py
   - a_breeding_function1.py
   - a_breeding_function2.py
   



1. 多种数据支持的，将组学数据存储，查询，浏览
   （数据盘配置）
2. 用户管理权限
   （RBAC用户角色和权限绑定）
   （菜单路由）
   （用户的依赖）
3. 

2. 异常处理和日志（整体）