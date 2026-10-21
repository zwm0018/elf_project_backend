# elf_project_backend

Elf Studio 的 FastAPI 后端。当前提供基于 JWT 的登录认证，后续可继续接入任务、资产与生成接口。

## 技术栈

- FastAPI + Uvicorn
- PostgreSQL（SQLAlchemy 2.x + `psycopg` 3）
- SQLite（仅用于本地零依赖测试，可选）
- PyJWT（HS256 访问令牌）
- scrypt（标准库密码哈希，带随机盐）

## 启动

环境：Python 3.10+。

```powershell
cd D:\elf_project\elf_project_backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d --wait db
uvicorn app.main:app --reload --port 8000
```

`compose.yaml` 会启动 PostgreSQL 16（开发账号见文件）。也可以使用已有 PostgreSQL，只需修改 `.env` 中的 `DATABASE_URL`：

```dotenv
DATABASE_URL=postgresql+psycopg://elf:elf_dev_password@127.0.0.1:5432/elf_studio
```

若使用已有 PostgreSQL，先创建账号与数据库：

```sql
CREATE USER elf WITH PASSWORD 'elf_dev_password';
CREATE DATABASE elf_studio OWNER elf;
```

首次启动会通过 SQLAlchemy 自动建表，并根据 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 创建演示账号。默认账号：`demo` / `demo1234`。

没有 PostgreSQL 时，可切换为 SQLite：

```dotenv
DATABASE_URL=sqlite:///data/elf_studio.db
```

- API 文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/health>

CORS 默认允许 `http://localhost` / `http://127.0.0.1` 的任意端口，便于 Vite 端口被占用时自动切换。

## 认证接口

所有业务接口使用 `Bearer` 令牌：

```http
POST /api/v1/auth/login
Content-Type: application/json

{"username":"demo","password":"demo1234"}
```

成功响应：

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {"id": 1, "username": "demo", "display_name": "研究员"}
}
```

```http
GET  /api/v1/auth/me       Authorization: Bearer <token>
POST /api/v1/auth/logout   Authorization: Bearer <token>
```

登录失败统一返回 `401 {"detail":"用户名或密码错误"}`。JWT 为无状态令牌，`logout` 由客户端删除令牌完成；如需服务端即时吊销，可增加令牌黑名单或改用短期令牌 + 刷新令牌。

## 测试

```powershell
pip install -r requirements-dev.txt
pytest -q
```

测试会为每个用例创建临时 SQLite 数据库，不需要启动 PostgreSQL。

## 生产注意事项

- 必须修改 `.env` 中的 `AUTH_SECRET_KEY` 和默认管理员密码，且不要提交 `.env`。
- 仅在 HTTPS 后暴露服务；JWT 存在浏览器存储中，XSS 可窃取。
- 当前使用 `Base.metadata.create_all()` 建表；字段变更上线前应引入 Alembic 迁移，不要依赖自动建表改结构。
- 生产环境使用独立 PostgreSQL 账号、强密码与连接池参数，并给登录接口加限流。
- 当前只有单用户表；需要注册、角色、多用户队列时，在 `users` 表基础上扩展即可。
