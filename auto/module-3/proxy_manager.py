# proxy_manager.py
# =====================================================================
# MODULE QUẢN LÝ TẬP TRUNG TOÀN BỘ LOGIC PROXY GATEWAY & SHOPIFY CLIENT
# =====================================================================
from __future__ import annotations

import os
import re
import json
import time
import threading
from datetime import datetime
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv

load_dotenv()

# =====================================================================
# 1. HẰNG SỐ, FILE CẤU HÌNH & NGOẠI LỆ AN TOÀN
# =====================================================================
PROXY_CONFIG_FILE = "proxy_config.json"
LOGO_UPDATER_CONFIG_FILE = "logo_updater_config.json"

DEFAULT_PROXY_CONFIG = {
    "enabled": False,
    "proxy_url": "http://nPMZfSl5QX0shvm:hKTQVcQVNAvYHXq@185.124.63.174:55031",
    "proxy_ip": "185.124.63.174",
    "is_stable": False,
    "last_status": "unknown",
    "last_latency_ms": 0,
    "last_checked_at": None,
    "last_error": None,
    "timeout_seconds": 8,
    "cache_ttl_seconds": 60,
    "geo": None
}

DEFAULT_LOGO_UPDATER_CONFIG = {
    "shop_domain": "",
    "shop_name": "",
    "client_id": "",
    "client_secret": "",
    "access_token": "",
    "is_custom": False,
    "updated_at": None,
    "token_obtained_at": None,
    "token_expires_at": None
}

class ProxySafetyException(Exception):
    """Ném ra khi Proxy Gateway đang bật nhưng mất kết nối hoặc không ổn định"""
    pass

# =====================================================================
# 2. THREAD LOCKS & QUẢN LÝ CẤU HÌNH THREAD-SAFE
# =====================================================================
_proxy_lock = threading.Lock()
_logo_updater_lock = threading.Lock()
_token_event_lock = threading.Lock()
_pending_token_notification = None

def get_env_shopify_shop() -> str:
    return clean_shopify_domain(os.getenv("SHOPIFY_SHOP", ""))

def get_env_admin_token() -> str:
    return (os.getenv("SHOPIFY_ADMIN_TOKEN") or "").strip().strip('"').strip("'")

def get_env_api_version() -> str:
    return (os.getenv("SHOPIFY_API_VERSION") or "2026-10").strip().strip('"').strip("'")

def load_proxy_config() -> dict:
    with _proxy_lock:
        if not os.path.exists(PROXY_CONFIG_FILE):
            tmp_file = f"{PROXY_CONFIG_FILE}.tmp"
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(DEFAULT_PROXY_CONFIG, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_file, PROXY_CONFIG_FILE)
            except Exception:
                pass
            return DEFAULT_PROXY_CONFIG.copy()
        try:
            with open(PROXY_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                for k, v in DEFAULT_PROXY_CONFIG.items():
                    if k not in cfg:
                        cfg[k] = v
                return cfg
        except Exception as e:
            print(f"Error loading proxy config: {e}")
            return DEFAULT_PROXY_CONFIG.copy()

def save_proxy_config(cfg: dict) -> None:
    with _proxy_lock:
        tmp_file = f"{PROXY_CONFIG_FILE}.tmp"
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, PROXY_CONFIG_FILE)
        except Exception as e:
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass
            print(f"Error saving proxy config: {e}")

def mark_proxy_unstable(err: str, latency: int = 0) -> None:
    try:
        cfg = load_proxy_config()
        cfg["is_stable"] = False
        cfg["last_status"] = "unstable"
        cfg["last_latency_ms"] = latency
        cfg["last_checked_at"] = datetime.now().isoformat()
        cfg["last_error"] = str(err)
        save_proxy_config(cfg)
    except Exception as e:
        print(f"Error marking proxy unstable: {e}")

def mark_proxy_stable(latency: int = 0) -> None:
    try:
        cfg = load_proxy_config()
        cfg["is_stable"] = True
        cfg["last_status"] = "stable"
        cfg["last_latency_ms"] = latency
        cfg["last_checked_at"] = datetime.now().isoformat()
        cfg["last_error"] = None
        save_proxy_config(cfg)
    except Exception as e:
        print(f"Error marking proxy stable: {e}")

def load_logo_updater_config() -> dict:
    with _logo_updater_lock:
        if not os.path.exists(LOGO_UPDATER_CONFIG_FILE):
            tmp_file = f"{LOGO_UPDATER_CONFIG_FILE}.tmp"
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(DEFAULT_LOGO_UPDATER_CONFIG, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_file, LOGO_UPDATER_CONFIG_FILE)
            except Exception:
                pass
            return DEFAULT_LOGO_UPDATER_CONFIG.copy()
        try:
            with open(LOGO_UPDATER_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                for k, v in DEFAULT_LOGO_UPDATER_CONFIG.items():
                    if k not in cfg:
                        cfg[k] = v
                return cfg
        except Exception as e:
            print(f"Error loading logo updater config: {e}")
            return DEFAULT_LOGO_UPDATER_CONFIG.copy()

def save_logo_updater_config(cfg: dict) -> None:
    with _logo_updater_lock:
        tmp_file = f"{LOGO_UPDATER_CONFIG_FILE}.tmp"
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, LOGO_UPDATER_CONFIG_FILE)
        except Exception as e:
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass
            print(f"Error saving logo updater config: {e}")

# =====================================================================
# 3. TIỆN ÍCH XỬ LÝ CHUỖI, PARSE URL VÀ MASK BẢO MẬT
# =====================================================================
def clean_shopify_domain(raw: str) -> str:
    if not raw:
        return ""
    d = str(raw).strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = d.split("?")[0].split("#")[0].strip("/")
    m = re.search(r"admin\.shopify\.com/store/([^/]+)", d)
    if m:
        return m.group(1).replace(".myshopify.com", "")
    d = d.split("/")[0].split(":")[0]
    d = d.replace(".myshopify.com", "")
    return d

def mask_secret(s: str) -> str:
    if not s:
        return ""
    s = str(s).strip()
    if len(s) <= 8:
        return "********"
    return f"{s[:4]}...{s[-4:]}"

def parse_proxy_input(raw: str) -> dict:
    if not raw:
        return {}
    s = str(raw).strip()
    
    # 1. Định dạng URL có scheme (http://, https://, socks5://, etc.)
    if re.match(r"^[a-zA-Z0-9+.-]+://", s):
        p = urlparse(s)
        host = p.hostname or ""
        port = p.port or 80
        user = p.username or ""
        pwd = p.password or ""
        scheme = p.scheme or "http"
        auth_part = f"{user}:{pwd}@" if user or pwd else ""
        proxy_url = f"{scheme}://{auth_part}{host}:{port}"
        return {
            "proxy_url": proxy_url,
            "proxy_ip": host,
            "host": host,
            "port": port,
            "username": user,
            "password": pwd,
            "scheme": scheme
        }
    
    # 2. Định dạng host:port:user:pass (Ví dụ: 185.124.63.174:55031:nPMZfSl5QX0shvm:hKTQVcQVNAvYHXq)
    parts = s.split(":")
    if len(parts) == 4:
        host, port_str, user, pwd = parts
        try:
            port = int(port_str)
        except ValueError:
            port = 80
        proxy_url = f"http://{user}:{pwd}@{host}:{port}"
        return {
            "proxy_url": proxy_url,
            "proxy_ip": host,
            "host": host,
            "port": port,
            "username": user,
            "password": pwd,
            "scheme": "http"
        }
        
    # 3. Định dạng user:pass@host:port
    if "@" in s:
        p = urlparse(f"http://{s}")
        host = p.hostname or ""
        port = p.port or 80
        user = p.username or ""
        pwd = p.password or ""
        auth_part = f"{user}:{pwd}@" if user or pwd else ""
        proxy_url = f"http://{auth_part}{host}:{port}"
        return {
            "proxy_url": proxy_url,
            "proxy_ip": host,
            "host": host,
            "port": port,
            "username": user,
            "password": pwd,
            "scheme": "http"
        }

    # 4. Định dạng host:port
    if len(parts) == 2:
        host, port_str = parts
        try:
            port = int(port_str)
        except ValueError:
            port = 80
        proxy_url = f"http://{host}:{port}"
        return {
            "proxy_url": proxy_url,
            "proxy_ip": host,
            "host": host,
            "port": port,
            "username": "",
            "password": "",
            "scheme": "http"
        }

    # Fallback
    clean_host = s.replace("http://", "").replace("https://", "").split(":")[0]
    return {
        "proxy_url": s if s.startswith("http") else f"http://{s}",
        "proxy_ip": clean_host,
        "host": clean_host,
        "port": 80,
        "username": "",
        "password": "",
        "scheme": "http"
    }

def mask_proxy_url(url: str) -> str:
    if not url:
        return ""
    try:
        p = urlparse(url)
        if p.password:
            masked_pwd = mask_secret(p.password)
            masked_netloc = f"{p.username}:{masked_pwd}@{p.hostname}"
            if p.port:
                masked_netloc += f":{p.port}"
            return f"{p.scheme}://{masked_netloc}"
        return url
    except Exception:
        return url

# =====================================================================
# 4. KIỂM TRA ĐỘ ỔN ĐỊNH (LIVENESS) VÀ LIVE EGRESS GEO
# =====================================================================
def get_configured_timeout(cfg: dict = None) -> int:
    if not cfg:
        cfg = load_proxy_config()
    val = cfg.get("timeout_seconds")
    try:
        val_int = int(val)
        if val_int > 0:
            return val_int
    except Exception:
        pass
    return 8

def get_configured_cache_ttl(cfg: dict = None) -> int:
    if not cfg:
        cfg = load_proxy_config()
    val = cfg.get("cache_ttl_seconds")
    try:
        val_int = int(val)
        if val_int > 0:
            return val_int
    except Exception:
        pass
    return 60

def test_proxy_connectivity(proxy_url: str = None, timeout: int = None, target_shop: str = None) -> tuple[bool, int, str | None]:
    cfg = load_proxy_config()
    if not proxy_url:
        proxy_url = cfg.get("proxy_url") or os.getenv("PROXY_URL")
    
    if timeout is None:
        timeout = get_configured_timeout(cfg)

    if not proxy_url or not str(proxy_url).strip():
        return False, 0, "Chưa cấu hình URL Proxy Gateway!"

    proxy_url = str(proxy_url).strip()
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    
    logo_cfg = load_logo_updater_config()
    if not target_shop:
        target_shop = clean_shopify_domain(logo_cfg.get("shop_domain")) if logo_cfg.get("is_custom") else get_env_shopify_shop()
    if not target_shop:
        target_shop = get_env_shopify_shop() or "wrydeco"
        
    api_ver = get_env_api_version()
    test_url = f"https://{target_shop}.myshopify.com/admin/api/{api_ver}/shop.json"
    token = logo_cfg.get("access_token") if logo_cfg.get("is_custom") else get_env_admin_token()
    test_headers = {"X-Shopify-Access-Token": token} if token else {}
    
    t0 = time.time()
    try:
        resp = requests.get(test_url, headers=test_headers, proxies=proxies, timeout=timeout)
        latency_ms = int((time.time() - t0) * 1000)
        if resp.status_code in (200, 301, 302, 401, 403, 404):
            return True, latency_ms, None
        else:
            return False, latency_ms, f"Shopify phản hồi HTTP {resp.status_code}"
    except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as pe:
        latency_ms = int((time.time() - t0) * 1000)
        return False, latency_ms, f"Lỗi Proxy Gateway: {str(pe)}"
    except requests.exceptions.Timeout:
        latency_ms = int((time.time() - t0) * 1000)
        return False, latency_ms, f"Hết thời gian chờ kết nối Proxy (Timeout > {timeout}s)"
    except Exception as e:
        latency_ms = int((time.time() - t0) * 1000)
        try:
            r2 = requests.get("https://ipwho.is/", proxies=proxies, timeout=timeout)
            if r2.status_code == 200:
                return True, latency_ms, None
        except Exception:
            pass
        return False, latency_ms, str(e)

def fetch_proxy_egress_geo(proxy_url: str = None, timeout: int = None) -> dict | None:
    cfg = load_proxy_config()
    if not proxy_url:
        proxy_url = cfg.get("proxy_url") or os.getenv("PROXY_URL")
    
    if timeout is None:
        timeout = get_configured_timeout(cfg)

    if not proxy_url or not str(proxy_url).strip():
        return None

    proxy_url = str(proxy_url).strip()
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    
    try:
        resp = requests.get("https://ipwho.is/", proxies=proxies, timeout=timeout)
        if resp.status_code == 200:
            d = resp.json()
            if d.get("success", False) or "country" in d:
                flag = "🌐"
                if isinstance(d.get("flag"), dict) and d.get("flag", {}).get("emoji"):
                    flag = d["flag"]["emoji"]
                elif d.get("country_code") == "US":
                    flag = "🇺🇸"
                
                isp = None
                if isinstance(d.get("connection"), dict):
                    isp = d["connection"].get("isp")
                
                return {
                    "ip": d.get("ip"),
                    "country": d.get("country"),
                    "country_code": d.get("country_code"),
                    "region": d.get("region"),
                    "city": d.get("city"),
                    "flag": flag,
                    "isp": isp,
                    "verified_at": datetime.now().isoformat()
                }
    except Exception as e:
        print(f"fetch_proxy_egress_geo (ipwho.is) notice: {e}")
        
    try:
        resp = requests.get("https://ipapi.co/json/", proxies=proxies, timeout=timeout)
        if resp.status_code == 200:
            d = resp.json()
            country_code = d.get("country_code")
            return {
                "ip": d.get("ip"),
                "country": d.get("country_name"),
                "country_code": country_code,
                "region": d.get("region"),
                "city": d.get("city"),
                "flag": "🇺🇸" if country_code == "US" else "🌐",
                "isp": d.get("org"),
                "verified_at": datetime.now().isoformat()
            }
    except Exception as e:
        print(f"fetch_proxy_egress_geo (ipapi.co) notice: {e}")
        
    return None

def get_shopify_request_proxies() -> dict | None:
    cfg = load_proxy_config()
    if not cfg.get("enabled"):
        return None
    
    now = datetime.now()
    last_check = None
    if cfg.get("last_checked_at"):
        try:
            last_check = datetime.fromisoformat(cfg["last_checked_at"])
        except Exception:
            last_check = None

    cache_ttl = get_configured_cache_ttl(cfg)
    timeout = get_configured_timeout(cfg)

    if not cfg.get("is_stable") or not last_check or (now - last_check).total_seconds() > cache_ttl:
        is_ok, latency, err = test_proxy_connectivity(cfg.get("proxy_url"), timeout=timeout)
        if not is_ok:
            cfg["is_stable"] = False
            cfg["last_status"] = "unstable"
            cfg["last_latency_ms"] = latency
            cfg["last_checked_at"] = now.isoformat()
            cfg["last_error"] = err
            save_proxy_config(cfg)
            raise ProxySafetyException("CHỐT CHẶN AN TOÀN: Proxy đang BẬT nhưng mất kết nối/không ổn định! Đã chặn toàn bộ request đi đến Shopify để bảo vệ gian hàng.")
        else:
            cfg["is_stable"] = True
            cfg["last_status"] = "stable"
            cfg["last_latency_ms"] = latency
            cfg["last_checked_at"] = now.isoformat()
            cfg["last_error"] = None
            save_proxy_config(cfg)

    return {
        "http": cfg["proxy_url"],
        "https": cfg["proxy_url"]
    }

# =====================================================================
# 5. TOKEN EVENT NOTIFICATIONS & OAUTH TOKEN EXCHANGE OVER PROXY
# =====================================================================
def set_token_notification(msg_type: str, message: str) -> None:
    global _pending_token_notification
    with _token_event_lock:
        _pending_token_notification = {
            "type": msg_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }

def pop_token_notification() -> dict | None:
    global _pending_token_notification
    with _token_event_lock:
        notif = _pending_token_notification
        _pending_token_notification = None
        return notif

def request_custom_app_access_token(
    shop_domain: str, 
    client_id: str, 
    client_secret: str, 
    timeout: int = 25, 
    force_proxy: bool = False
) -> tuple[bool, str, str | None]:
    default_shop = get_env_shopify_shop()
    shop = clean_shopify_domain(shop_domain) or default_shop
    if not shop or not client_id or not client_secret:
        err = "Thiếu Shop Domain, Client ID hoặc Client Secret để cấp Access Token cho Store Riêng."
        set_token_notification("error", f"Yêu cầu cấp Access Token mới thất bại qua Proxy: {err}")
        return False, err, None

    proxy_cfg = load_proxy_config()
    if not proxy_cfg.get("enabled") and not force_proxy:
        err = "Proxy Gateway đang TẮT! Yêu cầu lấy Access Token cho App riêng bắt buộc phải đi qua Proxy để bảo vệ gian hàng."
        set_token_notification("error", f"Yêu cầu cấp Access Token mới thất bại qua Proxy: {err}")
        return False, err, None

    proxy_url = proxy_cfg.get("proxy_url")
    if not proxy_url:
        err = "Chưa cấu hình URL Proxy Gateway!"
        set_token_notification("error", f"Yêu cầu cấp Access Token mới thất bại qua Proxy: {err}")
        return False, err, None

    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }

    token_url = f"https://{shop}.myshopify.com/admin/oauth/access_token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id.strip(),
        "client_secret": client_secret.strip()
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }

    try:
        res = requests.post(token_url, data=payload, headers=headers, proxies=proxies, timeout=timeout)
        if res.status_code == 200:
            data = res.json()
            new_token = data.get("access_token")
            if new_token:
                cfg = load_logo_updater_config()
                cfg["shop_domain"] = f"{shop}.myshopify.com"
                cfg["client_id"] = client_id.strip()
                cfg["client_secret"] = client_secret.strip()
                cfg["access_token"] = new_token
                cfg["is_custom"] = True
                cfg["updated_at"] = datetime.now().isoformat()
                cfg["token_obtained_at"] = datetime.now().isoformat()
                expires_in = data.get("expires_in")
                if expires_in:
                    cfg["token_expires_at"] = datetime.now().timestamp() + int(expires_in)
                else:
                    cfg["token_expires_at"] = None
                save_logo_updater_config(cfg)
                
                try:
                    p_cfg = load_proxy_config()
                    p_cfg["is_stable"] = True
                    p_cfg["last_status"] = "stable"
                    p_cfg["last_error"] = None
                    p_cfg["last_checked_at"] = datetime.now().isoformat()
                    save_proxy_config(p_cfg)
                except Exception:
                    pass

                success_msg = f"Đã tự động lấy Access Token mới thành công qua Proxy US cho store '{shop}'!"
                set_token_notification("success", success_msg)
                return True, success_msg, new_token
            else:
                err = "Shopify không trả về access_token trong phản hồi OAuth"
                set_token_notification("error", f"Yêu cầu cấp Access Token mới thất bại qua Proxy: {err}")
                return False, err, None
        else:
            err_text = res.text
            try:
                ej = res.json()
                if "error_description" in ej:
                    err_text = ej["error_description"]
                elif "error" in ej:
                    err_text = ej["error"]
            except Exception:
                pass
            err_msg = f"Shopify từ chối cấp token (HTTP {res.status_code}): {err_text}"
            set_token_notification("error", f"Yêu cầu cấp Access Token mới thất bại qua Proxy: {err_msg}")
            return False, err_msg, None
    except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as pe:
        mark_proxy_unstable(str(pe))
        err_msg = f"Lỗi Proxy Gateway: {str(pe)}"
        set_token_notification("error", f"Yêu cầu cấp Access Token mới thất bại qua Proxy: {err_msg}")
        return False, err_msg, None
    except Exception as e:
        err_msg = str(e)
        set_token_notification("error", f"Yêu cầu cấp Access Token mới thất bại qua Proxy: {err_msg}")
        return False, err_msg, None

def request_default_store_access_token(timeout: int = 25, force_proxy: bool = False) -> tuple[bool, str, str | None]:
    shop = get_env_shopify_shop()
    client_id = (os.getenv("SHOPIFY_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("SHOPIFY_CLIENT_SECRET") or "").strip()
    if not shop or not client_id or not client_secret:
        return False, "Thiếu SHOPIFY_CLIENT_ID hoặc SHOPIFY_CLIENT_SECRET của store mặc định trong .env", None

    proxies = None
    if force_proxy:
        proxy_cfg = load_proxy_config()
        proxy_url = proxy_cfg.get("proxy_url")
        if proxy_url:
            proxies = {"http": proxy_url, "https": proxy_url}

    token_url = f"https://{shop}.myshopify.com/admin/oauth/access_token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }

    try:
        res = requests.post(token_url, data=payload, headers=headers, proxies=proxies, timeout=timeout)
        if res.status_code == 200:
            data = res.json()
            new_tok = data.get("access_token")
            if new_tok:
                os.environ["SHOPIFY_ADMIN_TOKEN"] = new_tok
                try:
                    env_file = ".env"
                    if os.path.exists(env_file):
                        with open(env_file, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                        new_lines = []
                        written = False
                        for line in lines:
                            if line.strip().startswith("SHOPIFY_ADMIN_TOKEN="):
                                new_lines.append(f'SHOPIFY_ADMIN_TOKEN={new_tok}\n')
                                written = True
                            else:
                                new_lines.append(line)
                        if not written:
                            new_lines.append(f'SHOPIFY_ADMIN_TOKEN={new_tok}\n')
                        with open(env_file, "w", encoding="utf-8") as f:
                            f.writelines(new_lines)
                except Exception as e_env:
                    print(f"Warning: could not update .env token: {e_env}")
                return True, "Cấp mới Access Token thành công!", new_tok
        return False, f"Shopify từ chối cấp token ({res.status_code}): {res.text[:200]}", None
    except Exception as exc:
        return False, f"Lỗi kết nối cấp token: {exc}", None

def get_logo_updater_credentials(auto_refresh: bool = True) -> dict:
    proxy_cfg = load_proxy_config()
    is_proxy_enabled = bool(proxy_cfg.get("enabled", False))
    default_shop = get_env_shopify_shop()
    api_ver = get_env_api_version()
    default_token = get_env_admin_token()
    
    # 1. NẾU PROXY TẮT: BẮT BUỘC DÙNG LOẠI 1 (MẶC ĐỊNH SERVER TỪ .ENV)
    if not is_proxy_enabled:
        return {
            "type": 1,
            "is_custom": False,
            "proxy_enabled": False,
            "shop": default_shop,
            "token": default_token,
            "client_id": os.getenv("SHOPIFY_CLIENT_ID") or "",
            "client_secret": os.getenv("SHOPIFY_CLIENT_SECRET") or "",
            "headers": {
                "X-Shopify-Access-Token": default_token,
                "Content-Type": "application/json"
            },
            "graphql_url": f"https://{default_shop}.myshopify.com/admin/api/{api_ver}/graphql.json"
        }
        
    # 2. NẾU PROXY BẬT: ĐỌC LOẠI 2 TỪ logo_updater_config.json
    custom_cfg = load_logo_updater_config()
    if custom_cfg.get("is_custom"):
        raw_shop = custom_cfg.get("shop_domain")
        shop = clean_shopify_domain(raw_shop) if raw_shop else default_shop
        if not shop:
            shop = default_shop
            
        client_id = (custom_cfg.get("client_id") or "").strip()
        client_secret = (custom_cfg.get("client_secret") or "").strip()
        custom_token = (custom_cfg.get("access_token") or "").strip()
        expires_at = custom_cfg.get("token_expires_at")
        
        # Kiểm tra nếu token trống HOẶC đã hết hạn
        is_expired = False
        if expires_at:
            try:
                if datetime.now().timestamp() >= (float(expires_at) - 60):
                    is_expired = True
            except Exception:
                pass

        if (not custom_token or is_expired) and auto_refresh and client_id and client_secret:
            ok, msg, new_tok = request_custom_app_access_token(shop, client_id, client_secret)
            if ok and new_tok:
                custom_token = new_tok

        if custom_token:
            return {
                "type": 2,
                "is_custom": True,
                "proxy_enabled": True,
                "shop": shop,
                "token": custom_token,
                "client_id": client_id,
                "client_secret": client_secret,
                "headers": {
                    "X-Shopify-Access-Token": custom_token,
                    "Content-Type": "application/json"
                },
                "graphql_url": f"https://{shop}.myshopify.com/admin/api/{api_ver}/graphql.json"
            }
        
    # 3. FALLBACK NẾU PROXY BẬT NHƯNG CHƯA CẤU HÌNH LOẠI 2 (HOẶC CHƯA CÓ TOKEN)
    return {
        "type": 1,
        "is_custom": False,
        "proxy_enabled": True,
        "shop": default_shop,
        "token": default_token,
        "client_id": os.getenv("SHOPIFY_CLIENT_ID") or "",
        "client_secret": os.getenv("SHOPIFY_CLIENT_SECRET") or "",
        "headers": {
            "X-Shopify-Access-Token": default_token,
            "Content-Type": "application/json"
        },
        "graphql_url": f"https://{default_shop}.myshopify.com/admin/api/{api_ver}/graphql.json"
    }

# =====================================================================
# 6. UNIFIED SHOPIFY CLIENT FACTORY
# =====================================================================
def get_shopify_client(
    store_type: str = "default",
    force_proxy_for_custom: bool = True,
    auto_refresh_token: bool = True,
    proxy_for_default: bool = False,
    proxy_config_loader=None,
    logo_updater_config_loader=None,
    test_proxy_func=None,
    credentials_loader=None,
    save_proxy_func=None
) -> dict:
    """
    Client Factory chuẩn hóa duy nhất thay thế toàn bộ các hàm khởi tạo trùng lặp:
    - Hỗ trợ dependency injection cho loaders để đảm bảo tương thích 100% với mock/unit tests.
    """
    st = str(store_type or "default").strip().lower()
    api_ver = get_env_api_version()
    
    _load_logo = logo_updater_config_loader or load_logo_updater_config
    _load_proxy = proxy_config_loader or load_proxy_config
    _test_proxy = test_proxy_func or test_proxy_connectivity
    _creds_loader = credentials_loader or get_logo_updater_credentials
    _save_proxy = save_proxy_func or save_proxy_config

    if st == "custom":
        logo_cfg = _load_logo()
        if not logo_cfg.get("is_custom") or not logo_cfg.get("shop_domain"):
            raise ValueError("Chưa cấu hình Store Riêng tại trang Cài đặt! Vui lòng vào Cài đặt để thêm thông tin Store Riêng (Shop Domain, Client ID, Client Secret).")

        p_cfg = _load_proxy()
        if force_proxy_for_custom and not p_cfg.get("enabled"):
            raise ProxySafetyException("CHỐT CHẶN AN TOÀN: Khi chuyển qua Store Riêng, BẮT BUỘC phải BẬT Proxy Gateway! Vui lòng bật Proxy tại trang Cài đặt hoặc qua công tắc điều khiển.")

        proxy_url = (p_cfg.get("proxy_url") or os.getenv("PROXY_URL") or "").strip()
        if not proxy_url:
            raise ProxySafetyException("Chưa cấu hình URL Proxy Gateway tại Settings!")

        # Kiểm tra liveness và độ ổn định proxy
        timeout = get_configured_timeout(p_cfg)
        is_ok, latency, err = _test_proxy(proxy_url, timeout=timeout)
        if not is_ok:
            mark_proxy_unstable(err or "Timeout", latency)
            raise ProxySafetyException(f"CHỐT CHẶN AN TOÀN: Kết nối Proxy không ổn định ({err or 'Mất kết nối'})! Đã từ chối mọi yêu cầu từ server đến Shopify để bảo vệ gian hàng.")

        p_cfg["is_stable"] = True
        p_cfg["last_status"] = "stable"
        p_cfg["last_latency_ms"] = latency
        p_cfg["last_checked_at"] = datetime.now().isoformat()
        p_cfg["last_error"] = None
        _save_proxy(p_cfg)

        proxies = {"http": proxy_url, "https": proxy_url}

        creds = _creds_loader(auto_refresh=auto_refresh_token)
        token = creds.get("token")
        if not token:
            raise ValueError("Không thể lấy Access Token cho Store Riêng qua Proxy! Vui lòng kiểm tra lại Client ID & Client Secret tại Settings.")

        shop = creds.get("shop") or clean_shopify_domain(logo_cfg.get("shop_domain"))
        shop_domain = f"{shop}.myshopify.com" if not shop.endswith(".myshopify.com") else shop
        brand_domain = (logo_cfg.get("custom_domain") or "").strip() or "wrydeco.com"
        shop_name = logo_cfg.get("shop_name") or shop.title()

        headers = {
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json"
        }
        graphql_url = creds.get("graphql_url") or f"https://{shop_domain}/admin/api/{api_ver}/graphql.json"
        rest_url = f"https://{shop_domain}/admin/api/{api_ver}"

        return {
            "shop": shop,
            "shop_domain": shop_domain,
            "display_domain": shop_domain,
            "brand_domain": brand_domain,
            "shop_name": shop_name,
            "store_name": shop_name,
            "token": token,
            "headers": headers,
            "graphql_url": graphql_url,
            "rest_url": rest_url,
            "proxies": proxies,
            "is_custom": True,
            "is_proxy_active": True,
            "store_type": "custom"
        }
    else:
        # Store Mặc định
        shop = get_env_shopify_shop()
        token = get_env_admin_token()
        shop_domain = f"{shop}.myshopify.com" if not shop.endswith(".myshopify.com") else shop
        headers = {
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json"
        }
        graphql_url = f"https://{shop_domain}/admin/api/{api_ver}/graphql.json"
        rest_url = f"https://{shop_domain}/admin/api/{api_ver}"
        
        # Store Mặc định mặc định kết nối trực tiếp từ VPS (Direct VPS)
        proxies = get_shopify_request_proxies() if proxy_for_default else None
        
        return {
            "shop": shop,
            "shop_domain": shop_domain,
            "display_domain": shop_domain,
            "brand_domain": shop_domain,
            "store_name": f"Store Mặc Định ({shop})",
            "shop_name": shop.title() if shop else "Default Store",
            "token": token,
            "headers": headers,
            "graphql_url": graphql_url,
            "rest_url": rest_url,
            "proxies": proxies,
            "is_custom": False,
            "is_proxy_active": bool(proxies),
            "store_type": "default"
        }

# =====================================================================
# 7. UNIFIED GRAPHQL EXECUTOR
# =====================================================================
def execute_shopify_graphql(
    client_info: dict, 
    query: str, 
    variables: dict = None, 
    max_retries: int = 2,
    timeout: int = 35,
    retry_ambiguous: bool = True
) -> dict:
    is_custom = bool(client_info.get("is_custom") or client_info.get("store_type") == "custom")
    proxies = client_info.get("proxies")

    if is_custom and not proxies:
        raise ProxySafetyException("CHỐT CHẶN AN TOÀN TUYỆT ĐỐI: Thao tác tới Store Riêng KHÔNG CÓ PROXY GATEWAY! Đã chặn ngay lập tức để bảo vệ gian hàng.")

    url = client_info.get("graphql_url")
    if not url:
        raise ValueError("Missing graphql_url in client_info")

    headers = dict(client_info.get("headers") or {})
    payload = {"query": query, "variables": variables or {}}

    for attempt in range(max_retries):
        try:
            resp = requests.post(
                url,
                json=payload,
                headers=headers,
                proxies=proxies,
                timeout=timeout
            )
            
            # Xử lý token hết hạn (401)
            if resp.status_code == 401 and attempt < max_retries - 1:
                if is_custom:
                    cfg = load_logo_updater_config()
                    ok, msg, new_tok = request_custom_app_access_token(
                        client_info.get("shop") or cfg.get("shop_domain"),
                        cfg.get("client_id", ""),
                        cfg.get("client_secret", ""),
                        force_proxy=True
                    )
                    if ok and new_tok:
                        headers["X-Shopify-Access-Token"] = new_tok
                        client_info["headers"]["X-Shopify-Access-Token"] = new_tok
                        client_info["token"] = new_tok
                        continue
                else:
                    ok, msg, new_tok = request_default_store_access_token()
                    if ok and new_tok:
                        headers["X-Shopify-Access-Token"] = new_tok
                        client_info["headers"]["X-Shopify-Access-Token"] = new_tok
                        client_info["token"] = new_tok
                        continue

            resp.raise_for_status()
            data = resp.json()
            if "errors" in data and not data.get("data"):
                return {"errors": data["errors"], "data": None}
            return data
            
        except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as pe:
            mark_proxy_unstable(str(pe))
            raise ProxySafetyException(f"CHỐT CHẶN AN TOÀN: Proxy Gateway mất kết nối trong quá trình gửi request: {str(pe)}")
        except requests.exceptions.RequestException as re_err:
            if not retry_ambiguous:
                raise
            if attempt == max_retries - 1:
                if is_custom and isinstance(re_err, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
                    mark_proxy_unstable(str(re_err))
                    raise ProxySafetyException(f"CHỐT CHẶN AN TOÀN: Kết nối tới Store Riêng qua Proxy thất bại: {re_err}")
                raise

    raise RuntimeError("GraphQL execution reached unexpected state")


# =====================================================================
# 8. UNIFIED REST EXECUTOR
# =====================================================================
def execute_shopify_rest(
    client_info: dict,
    method: str,
    path_or_url: str,
    json_data: dict = None,
    data = None,
    params: dict = None,
    headers: dict = None,
    max_retries: int = 2,
    timeout: int = 40
) -> requests.Response:
    """
    Thực thi request REST Admin API tới Shopify thông qua chuẩn bảo mật Proxy:
    - Bắt buộc kiểm tra chốt chặn Proxy nếu client_info là Store Riêng (custom).
    - Tự động bắt mã lỗi 401 để refresh Access Token và retry.
    - Tự động bắt lỗi Proxy (ProxyError, ConnectTimeout) để đánh dấu proxy không ổn định
      và quăng ProxySafetyException (HTTP 503) bảo vệ an toàn gian hàng.
    """
    is_custom = bool(client_info.get("is_custom") or client_info.get("store_type") == "custom")
    proxies = client_info.get("proxies")

    if is_custom and not proxies:
        raise ProxySafetyException("CHỐT CHẶN AN TOÀN TUYỆT ĐỐI: Thao tác REST tới Store Riêng KHÔNG CÓ PROXY GATEWAY! Đã chặn ngay lập tức để bảo vệ gian hàng.")

    clean_path = str(path_or_url or "").strip()
    if clean_path.startswith("http://") or clean_path.startswith("https://"):
        url = clean_path
    else:
        base_rest = client_info.get("rest_url")
        if not base_rest:
            shop = client_info.get("shop") or get_env_shopify_shop()
            shop_domain = f"{shop}.myshopify.com" if not str(shop).endswith(".myshopify.com") else shop
            api_ver = get_env_api_version()
            base_rest = f"https://{shop_domain}/admin/api/{api_ver}"

        rel_path = clean_path.lstrip("/")
        if rel_path.startswith("admin/api/"):
            shop_domain = client_info.get("shop_domain") or f"{client_info.get('shop')}.myshopify.com"
            url = f"https://{shop_domain}/{rel_path}"
        else:
            url = f"{base_rest.rstrip('/')}/{rel_path}"

    req_headers = dict(client_info.get("headers") or {})
    if "Content-Type" not in req_headers:
        req_headers["Content-Type"] = "application/json"
    if headers:
        req_headers.update(headers)

    method_upper = method.strip().upper()

    for attempt in range(max_retries):
        try:
            resp = requests.request(
                method=method_upper,
                url=url,
                json=json_data,
                data=data,
                params=params,
                headers=req_headers,
                proxies=proxies,
                timeout=timeout
            )

            # Xử lý token hết hạn (401)
            if resp.status_code == 401 and attempt < max_retries - 1:
                if is_custom:
                    cfg = load_logo_updater_config()
                    ok, msg, new_tok = request_custom_app_access_token(
                        client_info.get("shop") or cfg.get("shop_domain"),
                        cfg.get("client_id", ""),
                        cfg.get("client_secret", ""),
                        force_proxy=True
                    )
                    if ok and new_tok:
                        req_headers["X-Shopify-Access-Token"] = new_tok
                        client_info["headers"]["X-Shopify-Access-Token"] = new_tok
                        client_info["token"] = new_tok
                        continue
                else:
                    ok, msg, new_tok = request_default_store_access_token()
                    if ok and new_tok:
                        req_headers["X-Shopify-Access-Token"] = new_tok
                        client_info["headers"]["X-Shopify-Access-Token"] = new_tok
                        client_info["token"] = new_tok
                        continue

            return resp

        except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as pe:
            mark_proxy_unstable(str(pe))
            raise ProxySafetyException(f"CHỐT CHẶN AN TOÀN: Proxy Gateway mất kết nối trong quá trình gửi request REST: {str(pe)}")
        except requests.exceptions.RequestException as re_err:
            if attempt == max_retries - 1:
                if is_custom and isinstance(re_err, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
                    mark_proxy_unstable(str(re_err))
                    raise ProxySafetyException(f"CHỐT CHẶN AN TOÀN: Kết nối tới Store Riêng qua Proxy thất bại: {re_err}")
                raise

    raise RuntimeError("REST execution reached unexpected state")

