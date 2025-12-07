# 快速启动指南

## 🚀 3分钟快速上手

### 步骤1: 初始化数据库（首次使用）

```bash
python init_database.py
```

### 步骤2: 启动应用

```bash
python run.py
```

### 步骤3: 访问系统

1. 浏览器访问: `http://localhost:8501`
2. 登录（默认: admin/admin）
3. 访问规则管理: `http://localhost:8501/rule_management`

## 📝 基本操作

### 编辑规则

1. 选择规则（如 `code_review_prompt`）
2. 点击"编辑规则"
3. 修改内容并填写原因
4. 保存并确认

### 查看历史

展开"查看修改历史"区域，浏览历史记录和差异对比

## ⚠️ 注意事项

- 规则支持 Jinja2 模板语法（如 `{{ style }}`）
- User Prompt 中可使用占位符：`{diffs_text}` 和 `{commits_text}`
- 修改立即生效，影响后续所有审查

## 🔧 故障排查

### 常见问题

1. **数据库错误**: 运行 `python init_database.py`
2. **端口被占用**: 修改端口 `python run.py --port 8502`
3. **模块未找到**: 安装依赖 `pip install -r requirements.txt`
4. **规则未生效**: 检查日志 `log/app.log`

## 💡 使用提示

1. 修改前可先复制当前规则内容作为备份
2. 每次只修改一小部分，便于验证效果
3. 填写修改原因，方便后续追溯
4. 查看历史记录可以了解规则演变过程

## 📚 更多文档

- [规则管理详细说明](doc/rule_management.md)
- [完整部署指南](README.md)
