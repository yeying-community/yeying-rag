# YeYing-RAG

## 项目简介

YeYing-RAG 是一个基于LlamaIndex的通用rag系统。

## 工作流程

#### 1. 创建功能分支
```bash
# 从main分支创建新的开发分支
git checkout main
git pull origin main
git checkout -b dev-{你的昵称}-{今日日期}

# 示例
git checkout -b dev-lyz-20250609
```

#### 2. 开发和提交
```bash
# 开发完成后提交代码
git add .
git commit -m "feat: 添加新功能描述"
git push origin dev-{你的昵称}-{今日日期}
```

#### 3. 创建 Pull Request
- 在 GitHub 上创建 PR，目标分支为 `main`
- 在 PR 描述中关联相关 issue：`fix #issue编号`
- 等待 kobofare 审核
