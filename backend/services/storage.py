"""Supabase Storage 服务
专门负责将图片上传到 Supabase Storage
"""
import os
import socket
from urllib.parse import urlparse
from typing import Optional, Any

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = Any  # 类型占位符
    create_client = None
    print("[存储服务] 警告: supabase 库未安装")

# 检查是否有异步客户端
try:
    from supabase import acreate_client, AsyncClient
    ASYNC_SUPABASE_AVAILABLE = True
except ImportError:
    ASYNC_SUPABASE_AVAILABLE = False
    AsyncClient = Any
    acreate_client = None

from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

# Supabase Storage bucket 名称
AVATARS_BUCKET = "avatars"

# 默认占位图 URL（用于旧路径兼容）
DEFAULT_AVATAR_URL = "https://via.placeholder.com/150?text=Avatar"

# 全局 Supabase 客户端（延迟初始化）
_supabase_client: Optional[Any] = None


def get_supabase_client() -> Any:
    """获取 Supabase 客户端（延迟初始化）"""
    global _supabase_client
    
    if not SUPABASE_AVAILABLE:
        raise ImportError("supabase 库未安装，请运行: pip install supabase")
    
    if _supabase_client is None:
        try:
            # ========== 诊断：打印环境变量详情 ==========
            print(f"[存储服务] ========== Supabase 配置诊断 ==========")
            print(f"[存储服务] SUPABASE_URL 原始值 (repr): {repr(SUPABASE_URL)}")
            print(f"[存储服务] SUPABASE_URL 长度: {len(SUPABASE_URL) if SUPABASE_URL else 0}")
            if SUPABASE_URL:
                has_newline = '\n' in SUPABASE_URL
                has_carriage = '\r' in SUPABASE_URL
                print(f"[存储服务] SUPABASE_URL 包含 \\n: {has_newline}")
                print(f"[存储服务] SUPABASE_URL 包含 \\r: {has_carriage}")
                url_len = len(SUPABASE_URL)
                if url_len >= 5:
                    print(f"[存储服务] SUPABASE_URL 首尾空白: {repr(SUPABASE_URL[:5])} ... {repr(SUPABASE_URL[-5:])}")
                else:
                    print(f"[存储服务] SUPABASE_URL 首尾空白: {repr(SUPABASE_URL)}")
            
            # ========== 二次清理 URL：彻底去除所有空白字符和换行符 ==========
            if SUPABASE_URL:
                supabase_url = SUPABASE_URL.strip().replace('\n', '').replace('\r', '').rstrip('/')
            else:
                supabase_url = None
            
            supabase_key = SUPABASE_SERVICE_ROLE_KEY.strip().replace('\n', '').replace('\r', '') if SUPABASE_SERVICE_ROLE_KEY else None
        except Exception as diag_error:
            # 诊断代码本身出错，不影响主流程
            print(f"[存储服务] ⚠️ 诊断代码执行出错: {type(diag_error).__name__}: {str(diag_error)}")
            import traceback
            traceback.print_exc()
            # 使用简单的清理方式
            try:
                supabase_url = SUPABASE_URL.strip().rstrip('/') if SUPABASE_URL else None
            except Exception:
                supabase_url = None
            try:
                supabase_key = SUPABASE_SERVICE_ROLE_KEY.strip() if SUPABASE_SERVICE_ROLE_KEY else None
            except Exception:
                supabase_key = None
        
        print(f"[存储服务] SUPABASE_URL 清理后 (repr): {repr(supabase_url)}")
        print(f"[存储服务] SUPABASE_URL 清理后长度: {len(supabase_url) if supabase_url else 0}")
        
        if not supabase_url:
            raise ValueError(
                "SUPABASE_URL 环境变量未设置。请在 Hugging Face Secrets 中配置 SUPABASE_URL。"
            )
        if not supabase_key:
            raise ValueError(
                "SUPABASE_SERVICE_ROLE_KEY 环境变量未设置。请在 Hugging Face Secrets 中配置 SUPABASE_SERVICE_ROLE_KEY。"
            )
        
        # 验证 URL 格式（必须是 https:// 开头）
        if not supabase_url.startswith("https://"):
            raise ValueError(
                f"SUPABASE_URL 格式错误，必须是 https:// 开头。当前值: {repr(supabase_url)}"
            )
        
        # ========== DNS 探测：尝试解析 Supabase 域名 ==========
        domain = None
        try:
            parsed_url = urlparse(supabase_url)
            domain = parsed_url.netloc
            if domain:
                print(f"[存储服务] 从 URL 提取的域名: {domain}")
                
                # 尝试 DNS 解析
                print(f"[存储服务] 开始 DNS 探测: {domain}")
                ip_address = socket.gethostbyname(domain)
                print(f"[存储服务] ✅ DNS 探测成功: {domain} -> {ip_address}")
            else:
                print(f"[存储服务] ⚠️ 无法从 URL 中提取域名: {supabase_url}")
        except socket.gaierror as e:
            domain_name = domain if domain else "未知域名"
            print(f"[存储服务] ❌ DNS 探测失败：无法解析 Supabase 域名 {domain_name}")
            print(f"[存储服务] DNS 错误详情: {type(e).__name__}: {str(e)}")
            # DNS 失败不阻止继续，可能是网络问题，让客户端库自己处理
        except Exception as e:
            domain_name = domain if domain else "未知域名"
            print(f"[存储服务] ⚠️ DNS 探测时发生其他错误: {type(e).__name__}: {str(e)}")
            print(f"[存储服务] 错误发生在域名: {domain_name}")
            # 其他错误也不阻止继续
        
        if create_client is None:
            raise ImportError("supabase 库未正确安装")
        
        print(f"[存储服务] 正在初始化 Supabase 客户端...")
        _supabase_client = create_client(supabase_url, supabase_key)
        print(f"[存储服务] ✅ Supabase 客户端初始化成功: {supabase_url}")
        print(f"[存储服务] ========== 诊断完成 ==========")
    
    return _supabase_client


def get_public_url(file_path: str) -> str:
    """
    获取文件的公网访问 URL
    
    Args:
        file_path: 文件在 Storage 中的路径（相对于 bucket）
        
    Returns:
        完整的公网访问 URL
    """
    # 确保 SUPABASE_URL 已去除空格和换行符，并去掉末尾斜杠
    supabase_url = SUPABASE_URL.strip().rstrip('/') if SUPABASE_URL else None
    if not supabase_url:
        raise ValueError("SUPABASE_URL 未配置")
    
    # Supabase Storage 公网 URL 格式
    # {SUPABASE_URL}/storage/v1/object/public/{bucket}/{file_path}
    public_url = f"{supabase_url}/storage/v1/object/public/{AVATARS_BUCKET}/{file_path}"
    return public_url


def normalize_avatar_url(avatar_url: Optional[str]) -> Optional[str]:
    """
    标准化头像 URL，处理旧路径兼容
    
    Args:
        avatar_url: 原始头像 URL（可能是旧路径或新 URL）
        
    Returns:
        标准化后的头像 URL（如果是旧路径则返回默认占位图）
    """
    if not avatar_url:
        return None
    
    # 如果是旧的本地路径（/avatars/ 开头），返回默认占位图
    if avatar_url.startswith("/avatars/"):
        print(f"[存储服务] 检测到旧路径头像: {avatar_url}，返回默认占位图")
        return DEFAULT_AVATAR_URL
    
    # 如果是完整的 Supabase Storage URL，直接返回
    if avatar_url.startswith("http") and "storage/v1/object/public" in avatar_url:
        return avatar_url
    
    # 其他情况（可能是相对路径或其他格式），返回默认占位图
    if not avatar_url.startswith("http"):
        print(f"[存储服务] 检测到非标准路径头像: {avatar_url}，返回默认占位图")
        return DEFAULT_AVATAR_URL
    
    return avatar_url


async def upload_avatar_file(file_content: bytes, file_name: str) -> str:
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
        upload_result = client.storage.from_(AVATARS_BUCKET).upload(
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
        
        # 检查返回结果是否是协程（Supabase 2.0+ 可能返回协程）
        if hasattr(upload_result, '__await__'):
            upload_result = await upload_result
        
        # Supabase Python 客户端在成功时返回数据，失败时抛出异常
        # 如果没有异常，说明上传成功
        
        # 获取公网 URL
        public_url = get_public_url(file_name)
        print(f"[存储服务] 头像上传成功: {file_name} -> {public_url}")
        
        return public_url
        
    except Exception as e:
        print(f"[存储服务] 上传头像失败: {type(e).__name__}: {str(e)}")
        raise


async def delete_avatar(file_path: str) -> bool:
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
        try:
            remove_result = client.storage.from_(AVATARS_BUCKET).remove([file_path])
            # 检查返回结果是否是协程（Supabase 2.0+ 可能返回协程）
            if hasattr(remove_result, '__await__'):
                remove_result = await remove_result
        except Exception as delete_error:
            print(f"[存储服务] 删除头像失败: {str(delete_error)}")
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
