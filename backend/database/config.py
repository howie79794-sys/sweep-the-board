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
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL 环境变量未设置。请配置 Supabase 数据库连接字符串。"
    )


def configure_database_url(url: str) -> str:
    """
    配置数据库连接URL，确保包含必要的参数
    
    Args:
        url: 原始数据库连接URL
        
    Returns:
        配置后的数据库连接URL
    """
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    # 确保包含 sslmode 参数（Supabase 需要）
    if 'sslmode' not in query_params:
        query_params['sslmode'] = ['require']
    
    # 如果 URL 中没有端口，且是 Supabase 连接，添加 6543 端口
    # 注意：Supabase 连接池端口是 6543，直接连接端口是 5432
    if not parsed.port:
        # 检查是否是 Supabase 连接
        if 'supabase.co' in parsed.hostname or 'supabase' in parsed.hostname.lower():
            # 使用连接池端口 6543
            parsed = parsed._replace(netloc=f"{parsed.hostname}:6543")
    
    # 重新构建查询字符串
    new_query = urlencode(query_params, doseq=True)
    configured_url = urlunparse(parsed._replace(query=new_query))
    
    return configured_url


# 配置数据库连接URL
CONFIGURED_DATABASE_URL = configure_database_url(DATABASE_URL)

# 创建数据库引擎
# 配置连接池参数以优化性能
engine = create_engine(
    CONFIGURED_DATABASE_URL,
    echo=False,
    pool_size=5,  # 连接池大小
    max_overflow=10,  # 最大溢出连接数
    pool_pre_ping=True,  # 连接前检查连接是否有效
    pool_recycle=3600,  # 连接回收时间（秒）
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建声明式基类
Base = declarative_base()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库表结构"""
    from database.models import User, Asset, MarketData, Ranking  # noqa: F401
    Base.metadata.create_all(bind=engine)
