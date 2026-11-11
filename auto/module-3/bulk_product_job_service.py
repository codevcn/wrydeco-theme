"""
bulk_product_job_service.py
Tầng dịch vụ nghiệp vụ (Business Service Layer) điều phối chuẩn hóa, kiểm tra hợp lệ
và quản lý vòng đời cho các Job tạo sản phẩm hàng loạt (Bulk Product Creation).
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

import bulk_product_job_store as store
from product_create_service import validate_create_payload


def prepare_bulk_job(
    store_type: str, 
    items: List[Dict[str, Any]], 
    metadata: Optional[Dict[str, Any]] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Chuẩn bị và validate một Job tạo sản phẩm hàng loạt:
    1. Kiểm tra store_type ('default' hoặc 'custom').
    2. Quét phát hiện trùng lặp Handle ngay trong batch (Duplicate handle preflight).
    3. Chạy validation server-side nghiêm ngặt cho từng item bằng validate_create_payload.
    4. Phân loại trạng thái ban đầu: QUEUED (hợp lệ) hoặc FAILED_VALIDATION (không hợp lệ).
    5. Lưu trữ Job bền vững vào SQLite.
    6. Trả về tóm tắt đầy đủ để giao diện hiển thị cho người dùng xác nhận.
    """
    # 1. Kiểm tra store_type
    target_store = "custom" if str(store_type).lower() == "custom" else "default"

    if not items or not isinstance(items, list):
        return {
            "success": False,
            "error": "Danh sách sản phẩm tải lên không hợp lệ hoặc đang trống.",
            "job": None
        }

    job_id = f"job_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    # 2. Duplicate Handle Preflight trong chính batch
    seen_handles = {}
    duplicate_handles = set()
    for idx, raw_item in enumerate(items):
        payload = raw_item.get("payload") if (isinstance(raw_item, dict) and isinstance(raw_item.get("payload"), dict)) else raw_item
        handle = (payload.get("handle") or "").strip().lower()
        if handle:
            if handle in seen_handles:
                duplicate_handles.add(handle)
            seen_handles[handle] = idx

    # 3. Validate từng item
    prepared_items = []
    valid_count = 0
    invalid_count = 0

    for idx, raw_item in enumerate(items):
        client_item_id = raw_item.get("client_item_id") if isinstance(raw_item, dict) and "client_item_id" in raw_item else f"client_{idx}"
        payload = raw_item.get("payload") if (isinstance(raw_item, dict) and isinstance(raw_item.get("payload"), dict)) else raw_item
        handle = (payload.get("handle") or "").strip()
        handle_lower = handle.lower()

        item_errors = []

        # Kiểm tra trùng handle nội bộ batch
        if handle_lower in duplicate_handles:
            item_errors.append({
                "field": "handle",
                "message": f"URL Handle '{handle}' bị trùng lặp với sản phẩm khác trong cùng danh sách CSV tải lên.",
                "code": "DUPLICATE_HANDLE_IN_BATCH"
            })

        # Media contract: Đảm bảo hình ảnh phải có URL hợp lệ, không hỗ trợ device binary trong bulk CSV
        raw_media = payload.get("media") or []
        for m_idx, m_item in enumerate(raw_media):
            if isinstance(m_item, dict):
                kind = m_item.get("kind", "url")
                url = (m_item.get("url") or "").strip()
                if kind != "url" or not url:
                    item_errors.append({
                        "field": f"media[{m_idx}]",
                        "message": "Chế độ tạo hàng loạt từ CSV chỉ hỗ trợ hình ảnh qua đường dẫn URL công khai (Image URLs).",
                        "code": "UNSUPPORTED_MEDIA_TYPE"
                    })

        # Server-side validation thông qua Single Source of Truth
        is_valid, validation_errors = validate_create_payload(payload)
        if not is_valid:
            item_errors.extend(validation_errors)

        if item_errors:
            initial_status = "FAILED_VALIDATION"
            invalid_count += 1
        else:
            initial_status = "QUEUED"
            valid_count += 1

        item_id = f"{job_id}:{idx}"
        prepared_items.append({
            "item_id": item_id,
            "client_item_id": client_item_id,
            "payload": payload,
            "initial_status": initial_status,
            "initial_errors": item_errors
        })

    # 4. Ghi nhận Job vào Database
    meta = metadata or {}
    meta["prepared_valid_count"] = valid_count
    meta["prepared_invalid_count"] = invalid_count

    job_record = store.create_job_record(
        job_id=job_id,
        store_type=target_store,
        items=prepared_items,
        metadata=meta,
        db_path=db_path
    )

    return {
        "success": True,
        "job_id": job_id,
        "job": {
            "job_id": job_id,
            "status": "READY",
            "store_type": target_store,
            "total": len(prepared_items),
            "valid": valid_count,
            "invalid": invalid_count,
            "progress": job_record.get("progress")
        },
        "items": [
            {
                "item_id": it["item_id"],
                "client_item_id": it["client_item_id"],
                "handle": it["handle"],
                "title": it["title"],
                "status": it["status"],
                "error_code": it.get("error_code"),
                "error_message": it.get("error_message")
            }
            for it in job_record.get("items", [])
        ]
    }


def get_bulk_job_snapshot(job_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Truy vấn snapshot tiến độ và danh sách sản phẩm của một Job."""
    return store.get_job(job_id, db_path=db_path)


def get_bulk_job_events(
    job_id: str, 
    last_event_id: int = 0, 
    limit: int = 200, 
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Lấy danh sách các sự kiện mới nhất kể từ last_event_id (SSE Reconnect)."""
    return store.get_events_after(job_id, last_event_id=last_event_id, limit=limit, db_path=db_path)
