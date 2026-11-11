"""
bulk_product_worker.py
Tiến trình thực thi (Execution Worker) xử lý tạo sản phẩm hàng loạt (Bulk Product Creation)
theo mô hình Async Worker / Concurrency Queue với Rate Limit Throttling (Cách 2)
chuẩn hóa cho WRYDECO Shopify Admin.

Đặc tính chính:
1. Durable Execution: Quản lý trạng thái và từng bước thực thi qua SQLite, không mất dữ liệu khi restart.
2. Adaptive Throttling: Đọc extensions.cost từ GraphQL response để điều tiết tốc độ gọi API an toàn.
3. Proxy Safety Gate: Với Custom Store, bắt buộc đi qua US Proxy Gate; nếu proxy lỗi -> PAUSED_PROXY ngay, không làm hỏng hàng trăm sản phẩm mù quáng.
4. Failure Isolation: Lỗi nghiệp vụ (Business Errors như duplicate handle, invalid variant) được cô lập ở từng item, không làm gián đoạn các sản phẩm khác.
5. Idempotent Start: Không thể kích hoạt duplicate worker cho cùng một Job đang chạy.
"""

import os
import time
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import bulk_product_job_store as store
from product_create_service import (
    create_wrydeco_product,
    check_shopify_product_exists_by_handle,
    check_shopify_product_exists_by_custom_id
)

logger = logging.getLogger("bulk_product_worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def run_bulk_job_worker(
    job_id: str, 
    worker_id: Optional[str] = None, 
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Thực thi xử lý toàn bộ các sản phẩm trong một Bulk Job theo thứ tự an toàn:
    - Lease-locking Concurrency Control
    - Worker Restart Recovery
    - Ambiguous Commit Idempotency Reconciliation
    - Adaptive Rate Limit Throttling
    - US Proxy Safety Guard
    - Isolated Error Recovery
    """
    worker_id = worker_id or f"worker_{os.getpid()}_{uuid.uuid4().hex[:6]}"
    job = store.get_job(job_id, db_path=db_path)
    if not job:
        logger.error(f"Job {job_id} không tồn tại.")
        return {"success": False, "error": "Job không tồn tại"}

    current_status = job.get("status")
    if current_status not in ("READY", "QUEUED", "RUNNING"):
        logger.warning(f"Job {job_id} đang ở trạng thái {current_status}, không thể thực thi.")
        return {"success": False, "status": current_status, "message": f"Job đang ở trạng thái {current_status}"}

    # Worker Restart Recovery: Khôi phục tất cả item kẹt ở CREATING do worker trước crash
    recovered_count = store.recover_stale_in_flight_items(job_id, db_path=db_path)
    if recovered_count > 0:
        logger.info(f"Worker Recovery: Đã khôi phục {recovered_count} items bị kẹt ở CREATING về QUEUED.")

    # Cập nhật Job sang RUNNING
    now_iso = datetime.now(timezone.utc).isoformat()
    store.update_job_status(job_id, "RUNNING", started_at=now_iso, db_path=db_path)
    store.append_job_event(job_id, "job_started", {
        "job_id": job_id,
        "worker_id": worker_id,
        "store_type": job["store_type"],
        "total_items": job["total_items"]
    }, db_path=db_path)

    # Ghi nhận nhịp tim worker
    store.record_worker_heartbeat(
        worker_id=worker_id,
        pid=os.getpid(),
        status="active",
        metadata={"job_id": job_id},
        db_path=db_path
    )

    # Khởi tạo trạng thái Leaky Bucket Throttle theo chuẩn Shopify
    store_type = job["store_type"]
    throttle_state = {
        "currently_available": 1000.0,
        "restore_rate": 50.0,  # 50 points/sec cho Standard, 100 points/sec cho Plus
        "max_available": 1000.0,
        "last_checked_time": time.time()
    }

    logger.info(f"Bắt đầu thực thi Bulk Job {job_id} [Worker: {worker_id}] (Store: {store_type}, Total: {job['total_items']})")

    while True:
        # Cập nhật nhịp tim worker định kỳ
        store.record_worker_heartbeat(
            worker_id=worker_id,
            pid=os.getpid(),
            status="active",
            metadata={"job_id": job_id, "last_active": datetime.now(timezone.utc).isoformat()},
            db_path=db_path
        )

        # Atomic Claim lease sản phẩm tiếp theo
        item = store.claim_next_queued_item(job_id, worker_id=worker_id, lease_seconds=120, db_path=db_path)
        if not item:
            # Đã xử lý hết tất cả items
            break

        item_id = item["item_id"]
        idempotency_key = item.get("idempotency_key") or item_id
        handle = item["handle"]
        title = item["title"]
        payload = item.get("payload") or {}

        store.append_job_event(job_id, "item_started", {
            "item_id": item_id,
            "idempotency_key": idempotency_key,
            "worker_id": worker_id,
            "handle": handle,
            "title": title
        }, db_path=db_path)

        # 0. Strong Idempotency & Preflight Check
        # A. Kiểm tra xem sản phẩm của chính job item này đã được tạo thành công ở lần trước chưa (Strong Idempotency)
        existing_by_custom_id = check_shopify_product_exists_by_custom_id(idempotency_key, store_type=store_type)
        if existing_by_custom_id:
            logger.info(f"STRONG IDEMPOTENCY RECONCILIATION: Item {item_id} (customId: {idempotency_key}) đã tồn tại trên Shopify: {existing_by_custom_id['id']}")
            prod_id = existing_by_custom_id.get("id") or ""
            gid_num = prod_id.split("/")[-1] if "/" in prod_id else prod_id
            admin_slug = "236qm8-w7" if store_type == "custom" else "wrydeco"
            storefront_url = f"https://236qm8-w7.myshopify.com/products/{handle}" if store_type == "custom" else f"https://wrydeco.com/products/{handle}"
            links = {
                "shopify_admin": f"https://admin.shopify.com/store/{admin_slug}/products/{gid_num}",
                "storefront": storefront_url,
                "tool": f"/product/{handle}?store_type={store_type}"
            }
            store.update_item_status(
                item_id=item_id,
                status="SUCCESS",
                product_id=prod_id,
                links=links,
                errors=None,
                db_path=db_path
            )
            store.append_job_event(job_id, "item_succeeded", {
                "item_id": item_id,
                "idempotency_key": idempotency_key,
                "handle": handle,
                "title": title,
                "product_id": prod_id,
                "links": links
            }, db_path=db_path)
            continue

        # B. Kiểm tra collision handle với sản phẩm khác trên store (Business Collision Check)
        existing_on_shopify = check_shopify_product_exists_by_handle(handle, store_type=store_type)
        if existing_on_shopify:
            # Nếu attempts <= 1: merchant đã có sản phẩm dùng handle này -> Reject
            if item.get("attempts", 1) <= 1:
                err_msg = f"URL Handle '{handle}' đã tồn tại trên Shopify Store ({store_type})."
                err_obj = [{"field": "handle", "code": "HANDLE_EXISTS", "message": err_msg}]
                store.update_item_status(
                    item_id=item_id,
                    status="FAILED",
                    errors=err_obj,
                    db_path=db_path
                )
                store.append_job_event(job_id, "item_failed", {
                    "item_id": item_id,
                    "handle": handle,
                    "title": title,
                    "errors": err_obj
                }, db_path=db_path)
                logger.warning(f"Preflight Rejection: Handle '{handle}' đã tồn tại trên Shopify.")
                continue
            else:
                # Nếu attempts > 1 và không match customId, nghĩa là có product khác đã chiếm handle này trong thời gian retry!
                err_msg = f"Xung đột Handle: Handle '{handle}' đã bị một sản phẩm khác chiếm dụng trong thời gian retry."
                err_obj = [{"field": "handle", "code": "HANDLE_CONFLICT_AFTER_AMBIGUOUS_FAILURE", "message": err_msg}]
                store.update_item_status(
                    item_id=item_id,
                    status="FAILED",
                    errors=err_obj,
                    db_path=db_path
                )
                store.append_job_event(job_id, "item_failed", {
                    "item_id": item_id,
                    "handle": handle,
                    "title": title,
                    "errors": err_obj
                }, db_path=db_path)
                logger.error(f"Handle Conflict: {err_msg}")
                continue

        # 1. Tính toán Adaptive Delay dựa trên GraphQL Rate Bucket
        now = time.time()
        elapsed = now - throttle_state["last_checked_time"]
        throttle_state["currently_available"] = min(
            throttle_state["max_available"],
            throttle_state["currently_available"] + (elapsed * throttle_state["restore_rate"])
        )
        throttle_state["last_checked_time"] = now

        estimated_next_cost = 35.0  # Ước lượng cost mutation productSet
        safety_reserve = 50.0      # Ngưỡng đệm an toàn

        if throttle_state["currently_available"] < (estimated_next_cost + safety_reserve):
            deficit = (estimated_next_cost + safety_reserve) - throttle_state["currently_available"]
            delay_sec = max(0.5, (deficit / throttle_state["restore_rate"]) + 0.1)
            logger.info(f"Throttling: Điểm khả dụng ({throttle_state['currently_available']:.1f}) thấp. Tạm dừng {delay_sec:.2f}s...")
            store.append_job_event(job_id, "item_throttled", {
                "item_id": item_id,
                "currently_available": round(throttle_state["currently_available"], 1),
                "wait_seconds": round(delay_sec, 2)
            }, db_path=db_path)
            time.sleep(delay_sec)
            throttle_state["currently_available"] += (delay_sec * throttle_state["restore_rate"])
            throttle_state["last_checked_time"] = time.time()

        # 2. Thực thi tạo sản phẩm thông qua product_create_service
        max_transient_retries = 4
        item_success = False
        final_result = None

        for attempt in range(max_transient_retries):
            try:
                res = create_wrydeco_product(payload=payload, store_type=store_type, idempotency_key=idempotency_key)
                final_result = res

                # Cập nhật lại điểm throttle từ phản hồi Shopify GraphQL nếu có
                if res.get("extensions") and isinstance(res["extensions"], dict):
                    cost_info = res["extensions"].get("cost") or {}
                    thr_status = cost_info.get("throttleStatus") or {}
                    if "currentlyAvailable" in thr_status:
                        throttle_state["currently_available"] = float(thr_status["currentlyAvailable"])
                    if "restoreRate" in thr_status:
                        throttle_state["restore_rate"] = float(thr_status["restoreRate"])
                    if "maximumAvailable" in thr_status:
                        throttle_state["max_available"] = float(thr_status["maximumAvailable"])
                    throttle_state["last_checked_time"] = time.time()

                # Kiểm tra Proxy Safety Block (Lỗi hạ tầng mạng Store Riêng)
                if res.get("phase") == "proxy_safety":
                    logger.error(f"CHỐT CHẶN AN TOÀN KÍCH HOẠT: US Proxy Gateway không khả dụng cho Store Riêng!")
                    # Đưa item hiện tại trở lại QUEUED để không làm mất
                    store.update_item_status(item_id, "QUEUED", errors=res.get("errors"), db_path=db_path)
                    # Tạm dừng toàn bộ Job
                    store.update_job_status(job_id, "PAUSED_PROXY", db_path=db_path)
                    store.append_job_event(job_id, "job_paused", {
                        "job_id": job_id,
                        "reason": "PROXY_SAFETY_BLOCKED",
                        "message": "Quá trình tạo sản phẩm hàng loạt tạm dừng do kết nối US Proxy Gateway của Store Riêng gặp sự cố."
                    }, db_path=db_path)
                    return {
                        "success": False,
                        "status": "PAUSED_PROXY",
                        "message": "Job tạm dừng do Proxy Safety Gate kích hoạt"
                    }

                # Kiểm tra lỗi THROTTLED từ Shopify GraphQL API (ngay cả khi HTTP 200)
                is_throttled = False
                for err in res.get("errors") or []:
                    code = str(err.get("code") or "").upper()
                    msg = str(err.get("message") or "").upper()
                    if "THROTTLED" in code or "THROTTLED" in msg:
                        is_throttled = True
                        break

                if is_throttled and attempt < max_transient_retries - 1:
                    backoff_delay = 2.0 * (attempt + 1)
                    logger.warning(f"Shopify báo lỗi THROTTLED cho item {item_id}. Chờ {backoff_delay}s để retry...")
                    store.append_job_event(job_id, "item_throttled", {
                        "item_id": item_id,
                        "attempt": attempt + 1,
                        "wait_seconds": backoff_delay
                    }, db_path=db_path)
                    time.sleep(backoff_delay)
                    continue

                if res.get("success"):
                    item_success = True
                    break
                else:
                    # Lỗi nghiệp vụ (Business error: handle trùng, thiếu dữ liệu, userErrors...) -> Không retry
                    break

            except Exception as ex:
                logger.error(f"Lỗi ngoại lệ khi tạo sản phẩm {item_id}: {str(ex)}")
                # Ambiguous Commit Recovery:
                # 1. Tra cứu bằng Strong Custom ID (productByIdentifier)
                recovered = check_shopify_product_exists_by_custom_id(idempotency_key, store_type=store_type)
                if recovered:
                    logger.info(f"Ambiguous commit recovered: Sản phẩm (customId: {idempotency_key}) đã được tạo trên Shopify: {recovered['id']}")
                    item_success = True
                    final_result = {"success": True, "product": recovered}
                    break

                # 2. Nếu không tìm thấy bằng customId, kiểm tra xem Handle có bị sản phẩm khác chiếm dụng trong lúc đứt mạng không
                unrelated_handle_product = check_shopify_product_exists_by_handle(handle, store_type=store_type)
                if unrelated_handle_product:
                    logger.error(f"Xung đột Handle sau ambiguous failure: Handle '{handle}' đã bị sản phẩm khác chiếm dụng!")
                    final_result = {
                        "success": False,
                        "phase": "handle_conflict",
                        "errors": [{
                            "field": "handle", 
                            "code": "HANDLE_CONFLICT_AFTER_AMBIGUOUS_FAILURE", 
                            "message": f"Handle '{handle}' đã bị một sản phẩm khác chiếm dụng trên Shopify trong thời gian gián đoạn mạng."
                        }]
                    }
                    break

                final_result = {
                    "success": False,
                    "phase": "worker_exception",
                    "errors": [{"field": "worker", "code": "WORKER_EXCEPTION", "message": str(ex)}]
                }
                if attempt < max_transient_retries - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                break

        # 3. Ghi nhận kết quả của Item
        if item_success and final_result and final_result.get("product"):
            prod = final_result["product"]
            prod_id = prod.get("id") or ""
            gid_num = prod_id.split("/")[-1] if "/" in prod_id else prod_id
            
            # Xây dựng bộ link chuẩn xác theo store_type
            if store_type == "custom":
                admin_slug = "236qm8-w7"
                storefront_url = f"https://236qm8-w7.myshopify.com/products/{handle}"
            else:
                admin_slug = "wrydeco"
                storefront_url = f"https://wrydeco.com/products/{handle}"

            links = {
                "shopify_admin": f"https://admin.shopify.com/store/{admin_slug}/products/{gid_num}",
                "storefront": storefront_url,
                "tool": f"/product/{handle}?store_type={store_type}"
            }

            store.update_item_status(
                item_id=item_id,
                status="SUCCESS",
                product_id=prod_id,
                links=links,
                errors=None,
                db_path=db_path
            )
            store.append_job_event(job_id, "item_succeeded", {
                "item_id": item_id,
                "handle": handle,
                "title": title,
                "product_id": prod_id,
                "links": links
            }, db_path=db_path)
            logger.info(f"Item {item_id} ({handle}) tạo THÀNH CÔNG: {prod_id}")
        else:
            errors = final_result.get("errors") if final_result else [
                {"field": "unknown", "code": "CREATION_FAILED", "message": "Không nhận được phản hồi hợp lệ"}
            ]
            store.update_item_status(
                item_id=item_id,
                status="FAILED",
                errors=errors,
                db_path=db_path
            )
            store.append_job_event(job_id, "item_failed", {
                "item_id": item_id,
                "handle": handle,
                "title": title,
                "errors": errors
            }, db_path=db_path)
            logger.warning(f"Item {item_id} ({handle}) THẤT BẠI: {errors[0].get('message') if errors else 'Lỗi không xác định'}")

    # 4. Cập nhật trạng thái hoàn tất của Job
    final_job = store.get_job(job_id, db_path=db_path)
    finish_iso = datetime.now(timezone.utc).isoformat()
    failed_count = final_job.get("failed_items", 0)

    if failed_count == 0:
        final_status = "COMPLETED"
    else:
        final_status = "COMPLETED_WITH_ERRORS"

    store.update_job_status(job_id, final_status, finished_at=finish_iso, db_path=db_path)
    store.append_job_event(job_id, "job_completed", {
        "job_id": job_id,
        "status": final_status,
        "total": final_job.get("total_items"),
        "success": final_job.get("success_items"),
        "failed": failed_count
    }, db_path=db_path)

    logger.info(f"Hoàn thành Bulk Job {job_id} với trạng thái {final_status} (Success: {final_job.get('success_items')}, Failed: {failed_count})")
    return store.get_job(job_id, db_path=db_path)
