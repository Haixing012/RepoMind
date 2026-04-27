# github_helper

`github_helper` 是一个面向开源项目阅读的 Web 应用。用户输入任意 GitHub 仓库地址后，系统会自动克隆仓库、分析源码、生成结构化中文报告，并支持基于源码的交互式问答。

项目目标很直接：把一个陌生仓库讲清楚，降低第一次读源码的门槛。

## 功能概览

- 自动克隆公开 GitHub 仓库并缓存到本地
- 异步分析项目结构、关键文件和技术栈
- 生成中文 Markdown 报告
- 实时推送分析进度
- 已分析仓库缓存复用，避免重复计算
- 基于源码工具的 Agent 问答
- 前端支持 Markdown 渲染与代码高亮

## 技术栈

### 后端

- FastAPI
- SQLAlchemy
- MySQL
- LangChain
- DeepSeek OpenAI-compatible API

### 前端

- Vue 3
- Vite
- Pinia
- markdown-it
- highlight.js

## 项目结构

```text
github_helper/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── tests/
│   ├── .env
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── stores/
│   │   ├── App.vue
│   │   └── main.js
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## 后端能力说明

### 1. 仓库分析

后端会完成以下步骤：

1. 规范化 GitHub URL
2. 克隆或刷新仓库
3. 扫描目录树与关键清单文件
4. 挑选重要源码文件
5. 调用大模型总结文件职责
6. 汇总生成完整 Markdown 报告

### 2. 进度推送

分析过程通过 SSE 推送到前端，便于展示：

- 准备分析
- 扫描目录
- 解读核心文件
- 生成报告
- 完成 / 失败

### 3. 源码问答

问答 Agent 拥有三类基础工具：

- `list_tree`: 查看目录树
- `search_code`: 搜索关键字
- `read_file`: 读取指定文件和行范围

这使它不是只靠缓存报告回答，而是可以继续自主查代码。

## 前端界面说明

页面分为三列：

- 左侧：仓库输入、分析进度、最近缓存
- 中间：项目快照与分析报告
- 右侧：源码问答

报告区域使用 Markdown 渲染，代码块高亮显示。

## 环境要求

- Windows PowerShell
- Conda
- `ollma` Conda 环境
- Node.js / npm
- 可访问 MySQL
- 可访问 DeepSeek API

## 配置

后端使用 [backend/.env](H:/Agent/github_helper/backend/.env)：

```env
APP_NAME=github_helper
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
FRONTEND_ORIGIN=http://127.0.0.1:5173
STORAGE_ROOT=storage

MYSQL_HOST=47.119.20.247
MYSQL_PORT=3308
MYSQL_USER=github_helper
MYSQL_PASSWORD=***
MYSQL_DATABASE=github_helper

DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=***
DEEPSEEK_MODEL=deepseek-chat
```

## 安装依赖

### 后端

```powershell
cd H:\Agent\github_helper\backend
cmd /c "D:\DevTools\Anaconda\condabin\conda.bat activate ollma && python -m pip install -r requirements.txt"
```

### 前端

```powershell
cd H:\Agent\github_helper\frontend
npm.cmd install
```

## 启动方式

### 启动后端

```powershell
cmd /c "D:\DevTools\Anaconda\condabin\conda.bat activate ollma && cd /d H:\Agent\github_helper\backend && set PYTHONPATH=H:\Agent\github_helper\backend&& uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
```

### 启动前端

```powershell
cd H:\Agent\github_helper\frontend
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

## 访问地址

- 前端：[http://127.0.0.1:5173](http://127.0.0.1:5173)
- 后端健康检查：[http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

## API 概览

- `POST /api/repos/analyze`
  - 创建或复用仓库分析任务
- `GET /api/repos`
  - 获取最近分析记录
- `GET /api/repos/{repository_id}`
  - 获取单仓库详情
- `GET /api/repos/{repository_id}/events`
  - 订阅分析进度事件
- `POST /api/repos/{repository_id}/chat`
  - 基于源码发起问答

## 测试与验证

后端测试：

```powershell
cd H:\Agent\github_helper\backend
cmd /c "D:\DevTools\Anaconda\condabin\conda.bat activate ollma && set PYTHONPATH=H:\Agent\github_helper\backend&& python -m unittest discover -s tests -v"
```

前端构建验证：

```powershell
cd H:\Agent\github_helper\frontend
npm.cmd run build
```

## 当前实现边界

- 当前支持公开仓库，未接入 GitHub Token 的私有仓库授权流程
- 报告生成依赖大模型质量，复杂仓库可能需要多轮优化
- 问答工具目前是基础版，尚未加入跨文件邻域读取与 AST 级分析
