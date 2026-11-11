"""Durable, resumable image imports using verified bytes and Shopify staged uploads."""
import hashlib
import io
import json
import os
from pathlib import Path
import time
import uuid
from urllib.parse import unquote, urlparse

from PIL import Image
import requests

import bulk_product_job_store as store
from proxy_manager import execute_shopify_graphql


class MediaImportError(Exception):
    pass


class MissingImportedProduct(MediaImportError):
    pass


def fingerprint(payload):
    keys = ('handle', 'title', 'descriptionHtml', 'description', 'productType', 'categoryId',
            'category', 'status', 'vendor', 'tags', 'seo', 'authorId', 'richDescription',
            'aeoHtml', 'interiorStyle', 'roomType', 'options', 'variants')
    normalized = {k: payload[k] for k in keys if k in payload}
    normalized['media'] = [{'url': m.get('url'), 'kind': m.get('kind', 'url'),
                            'fileIndex': m.get('fileIndex'), 'contentHash': m.get('contentHash')}
                           for m in payload.get('media', [])]
    return hashlib.sha256(json.dumps(normalized, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _connection(db_path=None):
    conn = store.get_db_connection(db_path)
    conn.execute('''CREATE TABLE IF NOT EXISTS product_import_receipts (
        store_type TEXT NOT NULL, handle TEXT NOT NULL, payload_hash TEXT NOT NULL,
        product_id TEXT NOT NULL, manifest_json TEXT NOT NULL, updated_at REAL NOT NULL,
        PRIMARY KEY(store_type, handle, payload_hash))''')
    conn.commit()
    return conn


def find_owned_import(payload, store_type, db_path=None):
    """Resume only a persisted import of this exact payload, never an arbitrary handle."""
    handle = str(payload.get('handle') or '').strip()
    if not handle:
        return None
    key = fingerprint(payload)
    conn = _connection(db_path)
    try:
        row = conn.execute('''SELECT product_id, manifest_json FROM product_import_receipts
            WHERE store_type=? AND handle=? AND payload_hash=?''', (store_type, handle, key)).fetchone()
        if row:
            return {'product_id': row['product_id'], 'manifest': json.loads(row['manifest_json'])}
        # Bridge imports made by the previous version, including partially created products.
        rows = conn.execute('''SELECT i.product_id, i.payload_json FROM bulk_job_items i
            JOIN bulk_jobs j ON j.job_id=i.job_id
            WHERE j.store_type=? AND i.handle=? AND i.product_id IS NOT NULL
            ORDER BY i.updated_at DESC LIMIT 20''', (store_type, handle)).fetchall()
        for row in rows:
            if fingerprint(json.loads(row['payload_json'])) == key:
                return {'product_id': row['product_id'], 'manifest': {}}
        return None
    finally:
        conn.close()


def save_receipt(payload, store_type, product_id, manifest, db_path=None):
    conn = _connection(db_path)
    try:
        with conn:
            conn.execute('''INSERT INTO product_import_receipts
                (store_type,handle,payload_hash,product_id,manifest_json,updated_at)
                VALUES (?,?,?,?,?,?) ON CONFLICT(store_type,handle,payload_hash)
                DO UPDATE SET product_id=excluded.product_id,manifest_json=excluded.manifest_json,
                              updated_at=excluded.updated_at''',
                (store_type, str(payload.get('handle') or '').strip(), fingerprint(payload),
                 product_id, json.dumps(manifest), time.time()))
    finally:
        conn.close()


def _api(client, query, variables, write=False):
    """Retry explicit throttling; ambiguous writes are reconciled by their media IDs."""
    for attempt in range(4):
        result = execute_shopify_graphql(client, query, variables,
                                         retry_ambiguous=not write)
        errors = result.get('errors') or []
        if not errors:
            return result.get('data') or {}
        throttled = all((e.get('extensions') or {}).get('code') == 'THROTTLED'
                        or 'throttl' in e.get('message', '').lower() for e in errors)
        if not throttled or attempt == 3:
            raise MediaImportError('; '.join(e.get('message', 'GraphQL error') for e in errors))
        time.sleep(2 * (attempt + 1))


MEDIA_QUERY = '''query ResumableProductImages($id:ID!, $first:Int!){product(id:$id){id handle
  media(first:$first){nodes{id status mediaErrors{code message}
    ... on MediaImage{image{url} fileStatus fileErrors{code message}}}}}}'''
ATTACH = '''mutation AttachStagedImage($product:ProductUpdateInput!,$media:[CreateMediaInput!]!){
  productUpdate(product:$product,media:$media){product{id} userErrors{field message}}}'''
REMOVE_FAILED = '''mutation RemoveFailedImportImages($id:ID!,$mediaIds:[ID!]!){
  productDeleteMedia(productId:$id,mediaIds:$mediaIds){deletedMediaIds mediaUserErrors{field message}}}'''
REORDER = '''mutation ReorderImportedImages($id:ID!,$moves:[MoveInput!]!){
  productReorderMedia(id:$id,moves:$moves){job{id} mediaUserErrors{field message}}}'''


def _nodes(client, product_id, expected):
    product = _api(client, MEDIA_QUERY, {'id': product_id, 'first': min(250, expected + 20)}).get('product')
    if not product:
        raise MissingImportedProduct('Sản phẩm đã tạo không còn tồn tại trên store đã chọn.')
    return product


def _ready(node):
    return (node.get('status') == 'READY' and not node.get('mediaErrors')
            and (node.get('image') or {}).get('url'))


def _check_result(result, error_key='userErrors'):
    if result.get(error_key):
        raise MediaImportError('; '.join(e.get('message', 'Shopify rejected media') for e in result[error_key]))


def cache_image(source_url, content):
    if len(content) > 32 * 1024 * 1024:
        raise MediaImportError('Ảnh vượt giới hạn lưu 32 MB.')
    with Image.open(io.BytesIO(content)) as image:
        image.verify()
    # Persist original bytes so a retry can survive deleted/expired CDN source URLs.
    cache_dir = Path(store.DB_PATH).resolve().parent / 'product_media_cache'
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / (hashlib.sha256(source_url.encode()).hexdigest() + '.bin')
    tmp = path.with_suffix('.' + uuid.uuid4().hex + '.tmp')
    tmp.write_bytes(content)
    os.replace(tmp, path)


def cached_sources(sources):
    root = Path(store.DB_PATH).resolve().parent / 'product_media_cache'
    return [source for source in sources if
            (root / (hashlib.sha256(source.encode()).hexdigest() + '.bin')).is_file()]


def download_image(client, source_url):
    cache = Path(store.DB_PATH).resolve().parent / 'product_media_cache' / (hashlib.sha256(source_url.encode()).hexdigest() + '.bin')
    if cache.exists():
        content = cache.read_bytes()
    else:
        with requests.get(source_url, proxies=client.get('proxies'), timeout=(15, 60), stream=True) as response:
            response.raise_for_status()
            chunks, size = [], 0
            for chunk in response.iter_content(128 * 1024):
                size += len(chunk)
                if size > 32 * 1024 * 1024:
                    raise MediaImportError('Ảnh vượt giới hạn tải 32 MB.')
                chunks.append(chunk)
            content = b''.join(chunks)
    with Image.open(io.BytesIO(content)) as image:
        fmt = image.format
        image.verify()
    types = {'JPEG': ('jpg', 'image/jpeg'), 'PNG': ('png', 'image/png'),
             'WEBP': ('webp', 'image/webp'), 'GIF': ('gif', 'image/gif')}
    if fmt not in types:
        raise MediaImportError('Định dạng ảnh không được hỗ trợ: ' + str(fmt))
    if not cache.exists():
        cache_image(source_url, content)
    extension, mime = types[fmt]
    return content, extension, mime


def preflight_images(client, media_inputs):
    for item in media_inputs:
        download_image(client, item['originalSource'])


def ensure_product_media(client, product, media_inputs, manifest, save_manifest, stage_upload):
    """Keep READY images, replace failed slots with staged bytes, and resume safely."""
    pid = product['id']
    count = len(media_inputs)
    current = _nodes(client, pid, count)
    if product.get('handle') and current.get('handle') != product['handle']:
        raise MediaImportError('Handle sản phẩm đã thay đổi; đã dừng để tránh sửa nhầm sản phẩm.')
    nodes = current['media']['nodes']
    ready = [n for n in nodes if _ready(n)]
    # Reconcile a write whose response was lost after its unique filename was saved.
    for entry in manifest.values():
        if not entry.get('media_id') and entry.get('filename'):
            found = next((n for n in ready if Path(unquote(urlparse(n['image']['url']).path)).name == entry['filename']), None)
            if found:
                entry['media_id'] = found['id']
            elif any(n.get('status') in ('PROCESSING', 'UPLOADED') for n in nodes):
                raise MediaImportError('Một ảnh đã gửi vẫn đang xử lý; chờ rồi chạy lại để tránh gắn trùng.')
    # First migration from old imports: matching filenames identify already completed slots.
    used = {v.get('media_id') for v in manifest.values()}
    for index, item in enumerate(media_inputs):
        slot = str(index)
        if slot in manifest:
            continue
        source_stem = Path(unquote(urlparse(item['originalSource']).path)).stem
        match = next((n for n in ready if n['id'] not in used and
            (Path(unquote(urlparse(n['image']['url']).path)).stem == source_stem or
             Path(unquote(urlparse(n['image']['url']).path)).stem.startswith(source_stem + '_'))), None)
        if match:
            manifest[slot] = {'source': item['originalSource'], 'media_id': match['id']}
            used.add(match['id'])
    # Older staged uploads retained order; ownership is proven by the original import record.
    if not manifest and len(ready) == count:
        manifest.update({str(i): {'source': media_inputs[i]['originalSource'], 'media_id': n['id']}
                         for i, n in enumerate(ready)})
    save_manifest(manifest)

    # Preserve every required source BEFORE deleting failed records: a source URL may
    # reference the very Shopify file being removed, or survive only in a CDN cache.
    by_id = {n['id']: n for n in nodes}
    for index, item in enumerate(media_inputs):
        existing = by_id.get((manifest.get(str(index)) or {}).get('media_id'))
        if not existing or not _ready(existing):
            download_image(client, item['originalSource'])

    # Remove only failed media from this owned product; never delete a READY asset.
    failed = [n['id'] for n in nodes if n.get('status') == 'FAILED']
    if failed:
        result = _api(client, REMOVE_FAILED, {'id': pid, 'mediaIds': failed}, write=True).get('productDeleteMedia') or {}
        _check_result(result, 'mediaUserErrors')
        if set(result.get('deletedMediaIds') or []) != set(failed):
            raise MediaImportError('Không thể gỡ hết media lỗi trước khi tiếp tục.')
        current = _nodes(client, pid, count)

    for index, item in enumerate(media_inputs):
        slot = str(index)
        for attempt in range(3):
            nodes = current['media']['nodes']
            entry = manifest.get(slot) or {}
            node = next((n for n in nodes if n['id'] == entry.get('media_id')), None)
            if node and _ready(node):
                break
            if node and node.get('status') == 'FAILED':
                result = _api(client, REMOVE_FAILED, {'id': pid, 'mediaIds': [node['id']]}, write=True).get('productDeleteMedia') or {}
                _check_result(result, 'mediaUserErrors')
                current = _nodes(client, pid, count)
                node = None
            if not node:
                content, ext, mime = download_image(client, item['originalSource'])
                filename = 'wry-import-' + hashlib.sha256(content).hexdigest()[:20] + '-' + uuid.uuid4().hex[:10] + '.' + ext
                resource = stage_upload(client, filename, content, mime)
                before_ids = {n['id'] for n in current['media']['nodes']}
                manifest[slot] = {'source': item['originalSource'], 'filename': filename}
                save_manifest(manifest)
                try:
                    result = _api(client, ATTACH, {'product': {'id': pid}, 'media': [{
                        'originalSource': resource, 'mediaContentType': 'IMAGE', 'alt': item.get('alt', '')
                    }]}, write=True).get('productUpdate') or {}
                    _check_result(result)
                    if not (result.get('product') or {}).get('id'):
                        raise MediaImportError('Shopify không xác nhận bước gắn ảnh.')
                except requests.RequestException:
                    # The write may have committed. Read back before considering another write.
                    time.sleep(2)
                current = _nodes(client, pid, count)
                added = [n for n in current['media']['nodes'] if n['id'] not in before_ids]
                if len(added) != 1:
                    raise MediaImportError('Không xác định được kết quả gắn ảnh; dữ liệu đã lưu để tiếp tục an toàn.')
                node = added[0]
                manifest[slot]['media_id'] = node['id']
                save_manifest(manifest)
            for poll in range(60):
                if _ready(node) or node.get('status') == 'FAILED':
                    break
                time.sleep(1)
                current = _nodes(client, pid, count)
                node = next((n for n in current['media']['nodes'] if n['id'] == manifest[slot].get('media_id')), None)
                if not node:
                    raise MediaImportError('Media vừa gắn đã biến mất; đã lưu tiến độ để tiếp tục.')
            if _ready(node):
                break
            if node.get('status') != 'FAILED':
                raise MediaImportError('Ảnh vẫn đang xử lý; chạy lại để tiếp tục trên cùng sản phẩm, không tạo bản trùng.')
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
        else:
            raise MediaImportError(f'Ảnh #{index + 1} chưa xử lý được sau 3 lần staged upload; tiến độ đã được lưu.')

    current = _nodes(client, pid, count)
    ids = [manifest[str(i)]['media_id'] for i in range(count)]
    nodes = current['media']['nodes']
    if len(nodes) != count or set(ids) != {n['id'] for n in nodes} or not all(_ready(n) for n in nodes):
        raise MediaImportError('Số lượng/URL ảnh chưa khớp dữ liệu import; đã dừng trước khi báo thành công.')
    if ids != [n['id'] for n in nodes]:
        moves = [{'id': media_id, 'newPosition': str(i)} for i, media_id in enumerate(ids)]
        result = _api(client, REORDER, {'id': pid, 'moves': moves}, write=True).get('productReorderMedia') or {}
        _check_result(result, 'mediaUserErrors')
        for _ in range(20):
            current = _nodes(client, pid, count)
            if [n['id'] for n in current['media']['nodes']] == ids:
                break
            time.sleep(1)
        else:
            raise MediaImportError('Shopify chưa hoàn tất sắp xếp ảnh; tiến độ đã được lưu để tiếp tục.')
    return {'nodes': current['media']['nodes']}
