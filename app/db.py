from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Iterator

from sqlalchemy import DateTime, Index, String, create_engine, func, select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .config import BASE_DIR, get_settings
from .security import hash_password


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


# PostgreSQL / SQLite 都支持函数索引，保证用户名大小写不敏感地唯一。
Index("uq_users_username_lower", func.lower(User.username), unique=True)

_engine: Engine | None = None
_engine_url: str | None = None
_engine_lock = Lock()


def _build_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    connect_args: dict[str, Any] = {}

    if url.get_backend_name() == "sqlite":
        # SQLite 相对路径按后端目录解析，避免从不同 cwd 启动时建出多个库。
        if url.database and url.database != ":memory:":
            database_path = Path(url.database)
            if not database_path.is_absolute():
                database_path = BASE_DIR / database_path
            database_path.parent.mkdir(parents=True, exist_ok=True)
            url = url.set(database=database_path.as_posix())
        connect_args["check_same_thread"] = False

    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


def get_engine() -> Engine:
    """按当前 DATABASE_URL 懒加载引擎；配置变化时自动切换并释放旧连接池。"""
    global _engine, _engine_url
    database_url = get_settings().database_url
    with _engine_lock:
        if _engine is None or _engine_url != database_url:
            if _engine is not None:
                _engine.dispose()
            _engine = _build_engine(database_url)
            _engine_url = database_url
        return _engine


def dispose_engine() -> None:
    """测试或进程退出时释放连接池。"""
    global _engine, _engine_url
    with _engine_lock:
        if _engine is not None:
            _engine.dispose()
        _engine = None
        _engine_url = None


def get_db() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session


def init_db() -> None:
    Base.metadata.create_all(get_engine())
    seed_default_admin()


def seed_default_admin() -> None:
    """首次启动时创建演示账号；已有同名用户时不会覆盖密码。"""
    settings = get_settings()
    username = settings.admin_username.strip()
    if not username:
        raise RuntimeError("ADMIN_USERNAME 不能为空")

    with Session(get_engine()) as session:
        if get_user_by_username(session, username) is not None:
            return
        session.add(
            User(
                username=username,
                password_hash=hash_password(settings.admin_password),
                display_name=settings.admin_display_name,
            )
        )
        try:
            session.commit()
        except IntegrityError:
            # 多实例同时首次启动时，另一实例可能已经插入同名用户。
            session.rollback()


def get_user_by_username(session: Session, username: str) -> User | None:
    statement = select(User).where(func.lower(User.username) == username.lower())
    return session.scalar(statement)


def get_user_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)
