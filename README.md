![Push图片](doc/img/open/ai-codereview-cartoon.png)

## 项目简介

本项目是一个基于大模型的自动化代码审查工具，帮助开发团队在代码合并或提交时，快速进行智能化的审查(Code Review)，提升代码质量和开发效率。

## 功能

- 🚀 多模型支持
  - 兼容 DeepSeek、ZhipuAI、OpenAI、通义千问 和 Ollama，想用哪个就用哪个。
- 📢 消息即时推送
  - 审查结果一键直达 钉钉、企业微信 或 飞书，代码问题无处可藏！
- 📅 自动化日报生成
  - 基于 GitLab & GitHub & Gitea & SVN Commit 记录，自动整理每日开发进展，谁在摸鱼、谁在卷，一目了然 😼。
- 📊 可视化 Dashboard
  - 集中展示所有 Code Review 记录，项目统计、开发者统计，数据说话，甩锅无门！
- 🎭 Review Style 任你选
  - 专业型 🤵：严谨细致，正式专业。 
  - 讽刺型 😈：毒舌吐槽，专治不服（"这代码是用脚写的吗？"） 
  - 绅士型 🌸：温柔建议，如沐春风（"或许这里可以再优化一下呢~"）
- ⚙️ **规则管理系统** 🆕
  - 通过Web界面动态管理AI审查规则，无需重启服务
  - 完整的历史记录追踪和差异对比
  - 规则修改立即生效，支持热更新
  - 数据库不可用时自动降级到YAML配置 
  - 幽默型 🤪：搞笑点评，快乐改码（"这段 if-else 比我的相亲经历还曲折！"）

**效果图:**

![MR图片](doc/img/open/mr.png)

![Note图片](doc/img/open/note.jpg)

![Dashboard图片](doc/img/open/dashboard.jpg)

## 原理

当用户在 GitLab/GitHub/Gitea 上提交代码（如 Merge Request 或 Push 操作）时，或当用户在 SVN 上提交代码时，系统将自动触发 webhook
事件，调用本系统的接口。系统随后通过第三方大模型对代码进行审查，并将审查结果直接反馈到对应的 Merge Request 或 Commit 的
Note 中（SVN通过日志记录），便于团队查看和处理。

![流程图](doc/img/open/process.png)

## 部署

### 方案一：Docker 部署

**1. 准备环境文件**

- 克隆项目仓库：
```aiignore
git clone https://github.com/shake1050/AI-Codereview-SVN.git
cd AI-Codereview-Gitlab
```

- 创建配置文件：
```aiignore
cp conf/.env.dist conf/.env
```

- 编辑 conf/.env 文件，配置以下关键参数：

```bash
#大模型供应商配置,支持 zhipuai , openai , deepseek 和 ollama
LLM_PROVIDER=deepseek

#DeepSeek
DEEPSEEK_API_KEY={YOUR_DEEPSEEK_API_KEY}

#支持review的文件类型(未配置的文件类型不会被审查)
SUPPORTED_EXTENSIONS=.java,.py,.php,.yml,.vue,.go,.c,.cpp,.h,.js,.css,.md,.sql

#钉钉消息推送: 0不发送钉钉消息,1发送钉钉消息
DINGTALK_ENABLED=0
DINGTALK_WEBHOOK_URL={YOUR_WDINGTALK_WEBHOOK_URL}

#Gitlab配置
GITLAB_ACCESS_TOKEN={YOUR_GITLAB_ACCESS_TOKEN}
```

**2. 启动服务**

```bash
docker-compose up -d
```

**3. 验证部署**

- 主服务验证：
  - 访问 http://your-server-ip:5001
  - 显示 "The code review server is running." 说明服务启动成功。
- Dashboard 验证：
  - 访问 http://your-server-ip:5002
  - 看到一个审查日志页面，说明 Dashboard 启动成功。

### 方案二：本地Python环境部署

**1. 获取源码**

```bash
git clone https://github.com/sunmh207/AI-Codereview-Gitlab.git
cd AI-Codereview-Gitlab
```

**2. 安装依赖**

使用 Python 环境（建议使用虚拟环境 venv）安装项目依赖(Python 版本：3.10+):

```bash
pip install -r requirements.txt
```

**3. 配置环境变量**

同 Docker 部署方案中的.env 文件配置。

**4. 初始化数据库（首次使用）**

```bash
python init_database.py
```

**5. 启动服务**

- 启动API服务：

```bash
python api.py
```

- 启动Dashboard服务：

```bash
python run.py
```

或指定端口：

```bash
python run.py --port 5002
```

### 配置 GitLab Webhook

#### 1. 创建Access Token

方法一：在 GitLab 个人设置中，创建一个 Personal Access Token。

方法二：在 GitLab 项目设置中，创建Project Access Token

#### 2. 配置 Webhook

在 GitLab 项目设置中，配置 Webhook：

- URL：http://your-server-ip:5001/review/webhook
- Trigger Events：勾选 Push Events 和 Merge Request Events (不要勾选其它Event)
- Secret Token：上面配置的 Access Token(可选)

**备注**

1. Token使用优先级
  - 系统优先使用 .env 文件中的 GITLAB_ACCESS_TOKEN。
  - 如果 .env 文件中没有配置 GITLAB_ACCESS_TOKEN，则使用 Webhook 传递的Secret Token。
2. 网络访问要求
  - 请确保 GitLab 能够访问本系统。
  - 若内网环境受限，建议将系统部署在外网服务器上。

### 配置 Gitea Webhook

#### 1. 创建 Access Token
- 在 Gitea 个人设置中创建 Access Token，并确保具备 `repo` 权限。

#### 2. 配置 Webhook
- 打开仓库 `Settings -> Webhooks -> Add Webhook`
- URL：`http://your-server-ip:5001/review/webhook`
- Header：`X-Gitea-Token` 设置为 `.env` 中的 `GITEA_ACCESS_TOKEN`（可选）
- 触发事件：勾选 `Push events` 与 `Pull Request events`
- Content Type：`application/json`

### 配置 SVN Webhook

SVN通过post-commit hook触发代码审查。详细配置说明请参考：[SVN Webhook 接入说明](doc/svn_webhook_setup.md)

#### 快速配置步骤：

1. **配置环境变量**：在 `conf/.env` 中添加：
   ```bash
   PUSH_REVIEW_ENABLED=1  # 启用提交审查
   SVN_REPO_URL=svn://your-svn-server.com/repo  # SVN仓库URL（可选）
   SVN_USERNAME=your_username  # SVN认证用户名（如果需要）
   SVN_PASSWORD=your_password  # SVN认证密码（如果需要）
   ```

2. **创建post-commit hook**：在SVN仓库的 `hooks` 目录下创建 `post-commit` 脚本，发送webhook到审查系统。

3. **测试提交**：提交代码验证webhook是否正常工作。

更多详细信息、示例脚本和常见问题，请查看 [SVN Webhook 接入说明文档](doc/svn_webhook_setup.md)。

#### VisualSVN Server 快速接入：

1. **配置部署参数**：
   - 编辑 `tools\hooks_svn\deploy_config.bat`
   - 设置仓库路径、API地址和SVN服务器地址
   - 首次部署设置 `SKIP_EXISTING=1`

2. **自动部署**（推荐）：
   ```batch
   # 以管理员身份运行
   cd tools\hooks_svn
   deploy_hooks_to_all_repos.bat
   ```
   
   脚本会自动：
   - 扫描所有SVN仓库
   - 部署hook文件到每个仓库
   - **自动配置API地址和仓库URL**
   - 验证部署结果

3. **更新配置**：
   - 修改 `deploy_config.bat` 中的配置
   - 设置 `SKIP_EXISTING=0`（允许覆盖）
   - 重新运行部署脚本

4. **手动配置**（不推荐）：
   - 将 `tools\hooks_svn\post-commit.bat` 和 `svn_post_commit_hook.py` 复制到仓库的 `hooks` 目录
   - 编辑 `svn_post_commit_hook.py`，配置 `REVIEW_API_URL` 和 `REPO_URL`

详细配置说明请参考：[SVN Hook 部署说明](tools/hooks_svn/部署说明.md)

### 配置消息推送

#### 1.配置钉钉推送

- 在钉钉群中添加一个自定义机器人，获取 Webhook URL。
- 更新 .env 中的配置：
  ```
  #钉钉配置
  DINGTALK_ENABLED=1  #0不发送钉钉消息，1发送钉钉消息
  DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx #替换为你的Webhook URL
  ```

企业微信和飞书推送配置类似，具体参见 [常见问题](doc/faq.md)

## 规则管理系统 🆕

### 快速启动

```bash
# 1. 初始化数据库（首次使用）
python init_database.py

# 2. 启动应用
python run.py

# 3. 访问系统
# 主页面: http://localhost:8501
# 规则管理: http://localhost:8501/rule_management
```

### 主要功能

- **规则查看**: 查看当前生效的审查规则
- **规则编辑**: 通过Web界面修改规则，支持Jinja2模板语法
- **历史记录**: 完整的变更历史和差异对比
- **热更新**: 修改立即生效，无需重启服务
- **自动降级**: 数据库不可用时自动使用YAML配置

### 注意事项

⚠️ **重要提示:**
- 默认账号: admin/admin，请及时修改密码
- 规则修改会立即影响后续所有代码审查
- 详细文档: [规则管理使用指南](doc/rule_management.md)

## 其它

**1.如何对整个代码库进行Review?**

可以通过命令行工具对整个代码库进行审查。当前功能仍在不断完善中，欢迎试用并反馈宝贵意见！具体操作如下：

```bash
python -m biz.cmd.review
```

运行后，请按照命令行中的提示进行操作即可。

**2.其它问题**

参见 [常见问题](doc/faq.md)

## 交流

若本项目对您有帮助，欢迎 Star ⭐️ 或 Fork。 有任何问题或建议，欢迎提交 Issue 或 PR。

也欢迎加微信/微信群，一起交流学习。

<p float="left">
  <img src="doc/img/open/wechat.jpg" width="400" />
  <img src="doc/img/open/wechat_group.jpg" width="400" /> 
</p>

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=sunmh207/AI-Codereview-Gitlab&type=Timeline)](https://www.star-history.com/#sunmh207/AI-Codereview-Gitlab&Timeline)