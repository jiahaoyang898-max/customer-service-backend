# 电商小二 · Docker 一键启动指南

> 全栈服务（MySQL + 电商业务服务 + 主客服后端 + 前端页面）统一由 Docker Compose 编排，**双击一次即可启动全部服务和端口，并自动弹出登录页面**。

---

## 一、一键启动（推荐）

```
双击项目根目录的  start.bat
```

脚本会自动完成 4 件事：

1. **环境自检** —— 检查 Docker 是否运行、`.env` 是否存在
2. **构建镜像** —— 首次约 3~8 分钟（之后走缓存，几十秒）
3. **启动容器** —— 等待所有服务真正就绪（含数据库初始化）
4. **弹出浏览器** —— 自动打开登录页 `http://localhost:18080/login`

停止全部服务：`双击 stop.bat`（保留数据）　|　彻底清库重来：在项目目录执行 `docker compose down -v`

> 若双击 `start.bat` 没反应，请在项目目录右键 →「在终端中打开」，执行
> `powershell -ExecutionPolicy Bypass -File .\start.ps1`

---

## 二、服务与端口清单

| 服务 | 容器名 | 宿主端口 | 容器端口 | 访问地址 |
|------|--------|---------|---------|---------|
| MySQL 数据库 | `cs-mysql` | 13306 | 3306 | `127.0.0.1:13306` |
| 电商业务服务 | `cs-ecommerce-service` | 18081 | 18081 | http://localhost:18081/docs |
| 主客服后端 | `cs-backend` | 18082 | 18082 | http://localhost:18082/docs |
| **前端页面** | `cs-frontend` | **18080** | 80 | **http://localhost:18080/login** |

**浏览器统一入口是 18080**，前端由 nginx 托管，并把接口反向代理到后端，因此不存在跨域问题：

```
浏览器 ──►  :18080 (nginx)
             ├── /              → 前端静态页面
             ├── /login         → 登录 / 注册页（独立入口）
             ├── /api/…         → 主客服后端 cs-backend:18082
             ├── /commerce/…    → 电商业务服务 cs-ecommerce-service:18081
             └── /health        → 后端健康检查
```

数据库：首次启动会由 `external/docker/mysql/initdb/*.sql` 自动创建两个库并灌入演示数据

- `customer_service` —— 对话状态（`dialogue_states`）
- `commerce` —— 订单 / 商品 / 物流 / 退款（8 个订单、6 个商品、3 个用户）

---

## 三、登录 / 注册页

启动后浏览器会自动打开 **http://localhost:18080/login**

| 项目 | 说明 |
|------|------|
| 设计风格 | 浅色商务风，参考 Apple 设计语言（系统字体 / 大圆角控件 / 柔和光晕） |
| 页面布局 | **满屏通铺双栏**，铺满整个视口，无外边距、无卡片浮层 |
| 视觉规范 | 主色 `#0071e3`、正文 `#1d1d1f`、次要文字 `#6e6e73`，与工作台首页一致 |
| 登录方式 | 手机号 或 邮箱 + 密码 |
| 账号来源 | **由用户自行注册，系统不预置任何账号** |
| 注册 | 昵称 + 账号 + 密码（≥6 位且含字母和数字）+ 确认密码 + 同意协议 |
| 注册后 | 自动切回登录页并预填账号，可直接登录 |
| 登录成功 | 跳转到工作台首页 `/` |
| 退出登录 | 首页顶部右上角有 **「退出登录」按钮**（旁边显示当前登录昵称 / 账号） |
| 未登录访问 | 直接访问 `/` 会被自动拦截并跳回 `/login` |

### 3.1 首页「退出登录」按钮

登录后进入工作台首页，页面**顶部右上角**（「新对话」按钮右侧）即用户区：

```
┌──────────────────────────────────────────────────────────┐
│  电商客服系统                                              │
│  [小宝头像] 小宝·在线        [🔄 新对话]  (佳)佳总      [⏻ 退出登录] │
└──────────────────────────────────────────────────────────┘
```

- 左侧小圆牌显示当前登录用户的**昵称 + 账号**
- 点击 **「退出登录」** → 弹出二次确认 → 清除本地登录态 → 自动跳回登录页 `/login`
- 退出后若再手动访问 `http://localhost:18080/`，会被自动重定向到登录页，需重新登录

> **关于认证实现**：本次要求「保持原有代码不动」，而后端暂未提供用户认证接口，
> 因此登录 / 注册采用**浏览器本地存储**实现了一套真实可走通的闭环（注册后即可登录，不预置任何账号）。
> 后续后端若提供 `/api/auth/login` 等接口，只需替换
> `external/customer-service-frontend/src/pages/auth.js` 中的实现，页面无需改动。

---

## 四、常用命令

```bash
cd D:\customer-service-backend

# 启动 / 重建
docker compose up -d --build      # 构建并后台启动
docker compose build              # 只构建
docker compose up -d              # 只启动

# 查看
docker compose ps                 # 容器状态
docker compose logs -f            # 全部日志（Ctrl+C 退出）
docker compose logs -f cs-backend # 只看后端日志

# 重启 / 停止
docker compose restart cs-backend # 重启单个服务
docker compose stop               # 暂停全部
docker compose down               # 停止并删除容器（保留数据）
docker compose down -v            # 同时删除数据卷（数据库会重新初始化）
```

接口自测：

```bash
curl http://localhost:18080/health                  # 后端健康检查
curl "http://localhost:18081/users/u1001/orders"   # 订单列表
curl -X POST http://localhost:18082/api/chat \
     -H "Content-Type: application/json" \
     -d "{\"sender_id\":\"u1001\",\"text\":\"我要退款\"}"
```

---

## 五、本次新增 / 修改的文件

**新增（不影响原有代码）：**

| 文件 | 作用 |
|------|------|
| `docker-compose.yml` | 一键编排 4 个服务 |
| `Dockerfile` | 主客服后端镜像（python:3.12-slim + uv） |
| `.dockerignore` | 排除 `.venv`、`main.zip`(63MB)、`.env` 等 |
| `start.bat` / `start.ps1` / `stop.bat` | 一键启动 / 停止脚本 |
| `external/ecommerce-service-backend/Dockerfile`、`.dockerignore` | 电商服务镜像 |
| `external/customer-service-frontend/Dockerfile`、`.dockerignore` | 前端多阶段构建（Node 构建 → nginx 托管） |
| `external/customer-service-frontend/nginx.conf` | 静态托管 + 接口反向代理 |
| `external/customer-service-frontend/login.html` | 登录页入口 |
| `external/customer-service-frontend/src/pages/LoginApp.vue` | 登录 / 注册页面组件 |
| `external/customer-service-frontend/src/pages/login-main.js` | 登录页挂载入口 |
| `external/customer-service-frontend/src/pages/auth.js` | 账号本地存储与校验逻辑 |

**修改（仅构建配置，业务代码零改动）：**

| 文件 | 改动 |
|------|------|
| `external/customer-service-frontend/vite.config.js` | 追加 `build.rollupOptions.input`，新增 `login.html` 多页面入口 |

> 原有 `main.py`、`api/`、`service/`、`engine/` 等后端业务代码，以及
> `App.vue`、`index.html` 前端业务代码**均未改动**。

---

## 六、常见问题

**1. 启动时报端口被占用（`port is already allocated`）**

```bash
netstat -ano | findstr ":13306 :18080 :18081 :18082"
# 记下最后一列的 PID，结束占用进程：
taskkill /PID <PID> /F
```
若本机已装 MySQL，可把 `docker-compose.yml` 中 `mysql` 的 `"3306:3306"` 改为 `"13306:3306"`（宿主机端口不影响容器间通信）。

**2. 数据库初始化没生效 / 表不存在**

初始化 SQL 只在数据卷为空时执行一次。彻底重来：

```bash
docker compose down -v
docker compose up -d
```

**3. 前端页面打开了但是旧的样式**

改了 `src/` 下的代码后需要重新构建前端镜像：

```bash
docker compose build frontend && docker compose up -d frontend
```

**4. 发送消息报 LLM 相关错误**

主客服后端的模型配置来自项目根目录 `.env`（`LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`），
由 compose 在启动时注入容器。请确认 `.env` 存在且 Key 有效、容器能访问外网：

```bash
docker compose exec cs-backend env | findstr LLM
```

**5. 首次启动很慢**

首次需要拉取镜像（python:3.12-slim / node:22-alpine / nginx / mysql:8.4）、
`uv sync` 安装 Python 依赖、`npm ci` 安装前端依赖、MySQL 初始化。之后启动只需十几秒。

**6. 想看服务到底起没起来**

```bash
docker compose ps          # 期望全部为 running / healthy
docker compose logs --tail=100 cs-backend
```

---

## 七、不用 Docker 时的本地启动（原有方式）

```powershell
# 1. 数据库（可用 external/docker 下的 compose 单独起 MySQL）
# 2. 电商业务服务
cd external/ecommerce-service-backend; uv sync; uv run uvicorn app.main:app --reload --port 18081
# 3. 主客服后端
python main.py
# 4. 前端
cd external/customer-service-frontend; npm install; npm run dev   # http://127.0.0.1:5173
```

本地开发时前端 dev server（5173）的 `/api`、`/commerce` 代理规则与 nginx 一致，见 `vite.config.js`。
