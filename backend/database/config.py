"""数据库配置模块
专门负责读取 DATABASE_URL 秘密环境变量，并配置 SQLAlchemy 连接池
包含 6543 端口和 sslmode 参数配置
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

# 数据库连接字符串（从环境变量读取，必须配置）
DATABASE_URL = os.getenv("DATABASE_URL")


def configure_database_url(url: str) -> str:
    """
    配置数据库连接URL，确保包含必要的参数
    
    Args:
        url: 原始数据库连接URL
        
    Returns:
        配置后的数据库连接URL
    """
    if not url:
        raise ValueError(
            "DATABASE_URL 环境变量未设置。请配置 Supabase 数据库连接字符串。"
        )
    
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    # 确保包含 sslmode 参数（Supabase 需要）
    if 'sslmode' not in query_params:
        query_params['sslmode'] = ['require']
    
    # 注意：不要修改端口，使用原始URL中的端口
    # Supabase 连接字符串已经包含正确的端口（5432 或 6543）
    
    # 重新构建查询字符串
    new_query = urlencode(query_params, doseq=True)
    configured_url = urlunparse(parsed._replace(query=new_query))
    
    return configured_url


# 延迟初始化引擎和会话工厂
_engine = None
_SessionLocal = None


def _get_configured_url():
    """获取配置后的数据库URL（延迟初始化）"""
    if not DATABASE_URL:
        raise ValueError(
            "DATABASE_URL 环境变量未设置。请配置 Supabase 数据库连接字符串。"
        )
    return configure_database_url(DATABASE_URL)


def _init_engine():
    """初始化数据库引擎（延迟初始化）"""
    global _engine
    if _engine is None:
        configured_url = _get_configured_url()
        _engine = create_engine(
            configured_url,
            echo=False,
            pool_size=10,  # 连接池大小（增加以应对并发）
            max_overflow=20,  # 最大溢出连接数（增加以应对峰值）
            pool_pre_ping=True,  # 连接前检查连接是否有效（防止 stale 连接）
            pool_recycle=1800,  # 连接回收时间（秒，30分钟，防止连接超时）
            connect_args={
                "connect_timeout": 10,  # 连接超时（秒）
                "options": "-c statement_timeout=30000"  # 查询超时（30秒，毫秒单位）
            }
        )
    return _engine


def _init_session_local():
    """初始化会话工厂（延迟初始化）"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_init_engine())
    return _SessionLocal


# 为了向后兼容，提供 engine 和 SessionLocal
# 使用类来模拟属性访问
class _EngineProxy:
    def __getattr__(self, name):
        return getattr(_init_engine(), name)
    
    def __call__(self, *args, **kwargs):
        return _init_engine()


class _SessionLocalProxy:
    def __call__(self, *args, **kwargs):
        return _init_session_local()(*args, **kwargs)


engine = _EngineProxy()
SessionLocal = _SessionLocalProxy()

# 创建声明式基类
Base = declarative_base()


def get_db():
    """获取数据库会话"""
    db = _init_session_local()()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库表结构"""
    from database.models import User, Asset, MarketData, Ranking  # noqa: F401
    Base.metadata.create_all(bind=_init_engine())
