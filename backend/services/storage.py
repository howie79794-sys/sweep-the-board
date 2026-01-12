"""Supabase Storage 服务
专门负责将图片上传到 Supabase Storage
"""
import os
from typing import Optional, Any

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = Any  # 类型占位符
    create_client = None
    print("[存储服务] 警告: supabase 库未安装")

from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

# Supabase Storage bucket 名称
AVATARS_BUCKET = "avatars"

# 全局 Supabase 客户端（延迟初始化）
_supabase_client: Optional[Any] = None


def get_supabase_client() -> Any:
    """获取 Supabase 客户端（延迟初始化）"""
    global _supabase_client
    
    if not SUPABASE_AVAILABLE:
        raise ImportError("supabase 库未安装，请运行: pip install supabase")
    
    if _supabase_client is None:
        if not SUPABASE_URL:
            raise ValueError(
                "SUPABASE_URL 环境变量未设置。请在 Hugging Face Secrets 中配置 SUPABASE_URL。"
            )
        if not SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError(
                "SUPABASE_SERVICE_ROLE_KEY 环境变量未设置。请在 Hugging Face Secrets 中配置 SUPABASE_SERVICE_ROLE_KEY。"
            )
        
        if create_client is None:
            raise ImportError("supabase 库未正确安装")
        
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        print(f"[存储服务] Supabase 客户端初始化成功: {SUPABASE_URL}")
    
    return _supabase_client


def get_public_url(file_path: str) -> str:
    """
    获取文件的公网访问 URL
    
    Args:
        file_path: 文件在 Storage 中的路径（相对于 bucket）
        
    Returns:
        完整的公网访问 URL
    """
    if not SUPABASE_URL:
        raise ValueError("SUPABASE_URL 未配置")
    
    # Supabase Storage 公网 URL 格式
    # {SUPABASE_URL}/storage/v1/object/public/{bucket}/{file_path}
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{AVATARS_BUCKET}/{file_path}"
    return public_url


def upload_avatar(file_content: bytes, file_name: str) -> str:
    """
    上传头像到 Supabase Storage 的 avatars bucket
    
    Args:
        file_content: 文件内容（字节）
        file_name: 文件名（包含扩展名）
        
    Returns:
        文件的公网访问 URL
        
    Raises:
        ValueError: 如果 Supabase 配置未设置
        Exception: 如果上传失败
    """
    try:
        client = get_supabase_client()
        
        # 上传文件到 Supabase Storage
        # file_name 作为文件路径（相对于 bucket）
        # 使用 upsert=True 允许覆盖已存在的文件
        response = client.storage.from_(AVATARS_BUCKET).upload(
            path=file_name,
            file=file_content,
            file_options={
                "content-type": (
                    "image/jpeg" if file_name.endswith((".jpg", ".jpeg"))
                    else "image/png" if file_name.endswith(".png")
                    else "image/webp" if file_name.endswith(".webp")
                    else "application/octet-stream"
                ),
                "upsert": "true"  # 允许覆盖已存在的文件
            }
        )
        
        # Supabase Python 客户端在成功时返回数据，失败时抛出异常
        # 如果没有异常，说明上传成功
        
        # 获取公网 URL
        public_url = get_public_url(file_name)
        print(f"[存储服务] 头像上传成功: {file_name} -> {public_url}")
        
        return public_url
        
    except Exception as e:
        print(f"[存储服务] 上传头像失败: {type(e).__name__}: {str(e)}")
        raise


def delete_avatar(file_path: str) -> bool:
    """
    删除 Supabase Storage 中的头像文件
    
    Args:
        file_path: 文件路径（可以是完整 URL 或相对路径）
        
    Returns:
        是否删除成功
    """
    try:
        # 如果传入的是完整 URL，提取文件名
        if file_path.startswith("http"):
            # 从 URL 中提取文件名
            # 格式: {SUPABASE_URL}/storage/v1/object/public/avatars/{file_name}
            if "/avatars/" in file_path:
                file_path = file_path.split("/avatars/")[-1]
            else:
                print(f"[存储服务] 无法从 URL 中提取文件名: {file_path}")
                return False
        
        # 如果传入的是相对路径（如 /avatars/xxx.jpg），提取文件名
        if file_path.startswith("/avatars/"):
            file_path = file_path.replace("/avatars/", "")
        
        client = get_supabase_client()
        
        # 删除文件
        response = client.storage.from_(AVATARS_BUCKET).remove([file_path])
        
        # 检查删除是否成功
        if response.get("error"):
            error_msg = response.get("error", {}).get("message", "未知错误")
            print(f"[存储服务] 删除头像失败: {error_msg}")
            return False
        
        print(f"[存储服务] 头像删除成功: {file_path}")
        return True
        
    except Exception as e:
        print(f"[存储服务] 删除头像时出错: {type(e).__name__}: {str(e)}")
        return False


def ensure_bucket_exists() -> bool:
    """
    确保 avatars bucket 存在（如果不存在则尝试创建）
    
    Returns:
        是否成功（bucket 存在或创建成功）
    """
    try:
        client = get_supabase_client()
        
        # 尝试列出 bucket（如果 bucket 不存在会报错）
        buckets = client.storage.list_buckets()
        
        # 检查 avatars bucket 是否存在
        bucket_exists = any(bucket.name == AVATARS_BUCKET for bucket in buckets)
        
        if not bucket_exists:
            print(f"[存储服务] avatars bucket 不存在，尝试创建...")
            # 注意：创建 bucket 需要管理员权限，如果失败会抛出异常
            # 在实际使用中，bucket 应该通过 Supabase 控制台预先创建
            try:
                client.storage.create_bucket(
                    AVATARS_BUCKET,
                    options={"public": True}  # 设置为公开，允许公网访问
                )
                print(f"[存储服务] avatars bucket 创建成功")
                return True
            except Exception as e:
                print(f"[存储服务] 无法创建 bucket: {type(e).__name__}: {str(e)}")
                print(f"[存储服务] 请通过 Supabase 控制台手动创建名为 '{AVATARS_BUCKET}' 的公开 bucket")
                return False
        else:
            print(f"[存储服务] avatars bucket 已存在")
            return True
            
    except Exception as e:
        print(f"[存储服务] 检查 bucket 时出错: {type(e).__name__}: {str(e)}")
        return False
