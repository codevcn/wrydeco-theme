const $ = (selector) => document.querySelector(selector);
const state = { csrf: "", manifest: { products: [] }, runs: [], currentRun: null, currentTask: null, refreshTimer: null, agent: null, agentReady: false, agentSessions: [], documents: [], currentDocument: null, prompts: null, productTypes: [], productTypeTarget: null, eventLines: [], pendingEvents: [], eventFlushTimer: null, eventCursor: 0, eventSource: null };
const INITIAL_EVENT_LOG_LIMIT = 250;
const MAX_EVENT_LOG_LINES = 500;

const labels = {
  pending: "Chờ crawl", crawling: "Đang crawl", crawled: "Đã crawl", price_verified: "Giá hợp lệ",
  content_queued: "Chờ content", content_claimed: "Agent đang xử lý", content_ready: "Content ready",
  apply_queued: "Chờ Shopify", applying: "Đang sync", applied: "Đã applied", dry_run_complete: "Dry run xong",
  failed: "Thất bại", needs_attention: "Cần chú ý", cancelled: "Đã đóng",
};
const agentStatusHelp = {
  ready: "Tiến trình Antigravity còn sống, bootstrap thành công và server đang giữ conversation.",
  busy: "Conversation còn sống và đang xử lý một prompt.",
  starting: "Antigravity đang khởi động.",
  initializing: "Antigravity đang khởi động và kiểm tra bootstrap.",
  failed: "Không còn giữ được conversation; content queue sẽ chờ Agent hoạt động lại.",
  stopped: "Không còn giữ được conversation; content queue sẽ chờ Agent hoạt động lại.",
  interrupted: "Không còn giữ được conversation; content queue sẽ chờ Agent hoạt động lại.",
};
const fieldIds = {
  title: "content-title", description_html: "content-description-html", seo_product_title: "content-seo-product-title",
  seo_title: "content-seo-title", seo_description: "content-seo-description", handle: "content-handle",
};

function notify(message, error = false) {
  const box = $("#notice"); box.textContent = message; box.classList.toggle("error", error); box.hidden = false;
  clearTimeout(notify.timer); notify.timer = setTimeout(() => { box.hidden = true; }, 7000);
}

function loading(button, active) {
  if (!button) return;
  button.disabled = active; button.classList.toggle("is-loading", active);
  if (!active) applyAgentGate();
}

async function api(url, options = {}) {
  const mutation = options.method && options.method !== "GET";
  const headers = { ...(options.headers || {}) };
  if (mutation) { headers["Content-Type"] = "application/json"; headers["X-CSRF-Token"] = state.csrf; }
  const response = await fetch(url, { ...options, headers });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `${response.status} ${response.statusText}`);
  return payload;
}

function updatePromptCounts() {
  $("#agent-prompt-count").textContent = `${$("#agent-prompt-editor").value.length.toLocaleString("vi-VN")} ký tự`;
  $("#content-task-prompt-count").textContent = `${$("#content-task-prompt-editor").value.length.toLocaleString("vi-VN")} ký tự`;
}

function closePrompts() {
  $("#prompts-modal").hidden = true;
  document.body.classList.remove("prompts-open");
  $("#open-prompts").focus();
}

async function openPrompts() {
  const modal = $("#prompts-modal");
  modal.hidden = false;
  document.body.classList.add("prompts-open");
  $("#prompts-status").textContent = "Đang tải hai prompt…";
  $("#agent-prompt-editor").disabled = true;
  $("#content-task-prompt-editor").disabled = true;
  $("#save-prompts").disabled = true;
  $("#close-prompts").focus();
  try {
    const payload = await api("/api/prompts");
    state.prompts = payload.prompts;
    $("#agent-prompt-editor").value = payload.prompts.agent_prompt || "";
    $("#content-task-prompt-editor").value = payload.prompts.content_task_prompt || "";
    $("#prompts-status").textContent = "Prompt đang dùng được tải từ scraper. Lưu thay đổi để dùng từ lần khởi động server kế tiếp.";
    updatePromptCounts();
  } catch (error) {
    $("#prompts-status").textContent = `Không thể tải prompt: ${error.message}`;
    $("#prompts-status").classList.add("error-text");
  } finally {
    $("#agent-prompt-editor").disabled = false;
    $("#content-task-prompt-editor").disabled = false;
    $("#save-prompts").disabled = false;
  }
}

async function savePrompts() {
  const payload = {
    prompts: {
      agent_prompt: $("#agent-prompt-editor").value,
      content_task_prompt: $("#content-task-prompt-editor").value,
    },
  };
  const result = await api("/api/prompts", { method: "PUT", body: JSON.stringify(payload) });
  state.prompts = payload.prompts;
  $("#prompts-status").classList.remove("error-text");
  $("#prompts-status").textContent = "Đã lưu. Conversation hiện tại không đổi; prompt mới có hiệu lực từ lần khởi động server kế tiếp.";
  notify(result.message || "Đã lưu hai prompt.");
}

function closeAgentSessions() {
  $("#agent-sessions-modal").hidden = true;
  document.body.classList.remove("sessions-open");
  $("#open-agent-sessions").focus();
}

function updateAgentCleanupCount() {
  const pending = state.agentSessions.filter((session) => session.cleanup_status === "pending_cleanup").length;
  const badge = $("#agent-cleanup-count");
  badge.textContent = pending;
  badge.hidden = pending === 0;
}

function relativeElapsed(value) {
  if (!value) return "không rõ thời gian";
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return "không rõ thời gian";
  const elapsedSeconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
  if (elapsedSeconds < 60) return "vừa xong";
  const minutes = Math.floor(elapsedSeconds / 60);
  if (minutes < 60) return `${minutes} phút trước`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} giờ trước`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} ngày trước`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} tháng trước`;
  return `${Math.floor(months / 12)} năm trước`;
}

function closeProductTypePicker() {
  const target = state.productTypeTarget;
  $("#product-type-modal").hidden = true;
  document.body.classList.remove("product-type-open");
  state.productTypeTarget = null;
  if (target?.isConnected) target.focus();
}

function renderProductTypeOptions(selectedValue = "") {
  const root = $("#product-type-options");
  if (!state.productTypes.length) {
    root.innerHTML = '<p class="docs-placeholder">Chưa có product type trong product_types.json.</p>';
    return;
  }
  root.innerHTML = state.productTypes.map((value) => `<button class="product-type-option${value === selectedValue ? " selected" : ""}" type="button" role="option" aria-selected="${value === selectedValue}" data-product-type="${escapeHtml(value)}">${escapeHtml(value)}</button>`).join("");
  root.querySelectorAll("[data-product-type]").forEach((button) => button.addEventListener("click", () => {
    $("#product-type-custom").value = button.dataset.productType;
    $("#product-type-status").textContent = `Đã chọn ${button.dataset.productType}. Nhấn Áp dụng để cập nhật sản phẩm.`;
    renderProductTypeOptions(button.dataset.productType);
  }));
}

async function openProductTypePicker(target) {
  state.productTypeTarget = target;
  $("#product-type-modal").hidden = false;
  document.body.classList.add("product-type-open");
  $("#product-type-custom").value = target.value;
  $("#product-type-status").textContent = "Danh sách được đọc từ scraper/product_types.json.";
  renderProductTypeOptions(target.value);
  $("#product-type-custom").focus();
  if (!state.productTypes.length) {
    try {
      const payload = await api("/api/product-types");
      state.productTypes = payload.product_types || [];
      renderProductTypeOptions(target.value);
    } catch (error) {
      $("#product-type-status").textContent = `Không thể tải danh sách: ${error.message}`;
    }
  }
}

function renderAgentSessions() {
  const sessions = state.agentSessions;
  const pending = sessions.filter((session) => session.cleanup_status === "pending_cleanup");
  const current = sessions.filter((session) => session.cleanup_status === "current");
  $("#sessions-current-count").textContent = current.length;
  $("#sessions-pending-count").textContent = pending.length;
  updateAgentCleanupCount();
  const root = $("#agent-sessions-list");
  if (!sessions.length) {
    root.innerHTML = '<div class="empty-state">Chưa có Antigravity conversation nào được scraper ghi nhận.</div>';
    return;
  }
  root.innerHTML = sessions.map((session) => {
    const isPending = session.cleanup_status === "pending_cleanup";
    const statusLabel = isPending ? "CHỜ DỌN" : "ĐANG DÙNG";
    const date = session.started_at ? new Date(session.started_at).toLocaleString("vi-VN") : "—";
    const stopped = session.stopped_at ? ` · dừng ${new Date(session.stopped_at).toLocaleString("vi-VN")}` : "";
    const lastUsedAt = session.stopped_at || session.last_activity_at || session.started_at;
    const relative = relativeElapsed(lastUsedAt);
    const kind = session.session_kind === "content"
      ? `CONTENT · ${session.product_asin || (session.product_id ? String(session.product_id).slice(0, 8) : "task")}`
      : "CONTROL";
    return `<article class="agent-session-card ${isPending ? "pending" : "current"}">
      <div class="agent-session-main">
        <div class="agent-session-title"><span class="status-pill ${isPending ? "warning" : "success"}">${statusLabel}</span><span class="status-pill neutral">${kind}</span><strong>${escapeHtml(session.conversation_id)}</strong></div>
        <p>Generation ${session.generation} · ${session.num_turns || session.recorded_turns || 0} turns · ${date}${stopped} <span class="session-relative-time">· ${relative}</span></p>
      </div>
      <div class="agent-session-actions">
        <button class="button secondary compact" type="button" data-session-action="copy" data-session-id="${escapeHtml(session.id)}" data-conversation-id="${escapeHtml(session.conversation_id)}"><span class="button-icon">⧉</span><span class="button-label">Copy ID</span></button>
        ${isPending ? `<button class="button warning compact" type="button" data-session-action="open" data-session-id="${escapeHtml(session.id)}" data-conversation-id="${escapeHtml(session.conversation_id)}"><span class="button-icon">▣</span><span class="button-label">Mở TUI để xóa</span></button>
        <button class="button danger compact" type="button" data-session-action="acknowledge" data-session-id="${escapeHtml(session.id)}" data-conversation-id="${escapeHtml(session.conversation_id)}"><span class="button-icon">✓</span><span class="button-label">Đã xóa trong Antigravity</span></button>` : ""}
      </div>
    </article>`;
  }).join("");
  root.querySelectorAll("[data-session-action]").forEach((button) => button.addEventListener("click", () => {
    const actionName = button.dataset.sessionAction;
    const sessionId = button.dataset.sessionId;
    const conversationId = button.dataset.conversationId;
    if (actionName === "copy") return copyValue(button, conversationId);
    if (actionName === "open") return action(button, async () => {
      await navigator.clipboard.writeText(conversationId).catch(() => {});
      await api(`/api/agent/sessions/${encodeURIComponent(sessionId)}/open-cleanup`, { method: "POST", body: "{}" });
      notify("Đã mở Antigravity TUI tại đúng workspace và copy conversation ID. Gõ /resume để xóa.");
    });
    if (!window.confirm(`Chỉ tiếp tục nếu bạn đã xóa conversation ${conversationId} trong Antigravity. Dọn metadata scraper ngay?`)) return;
    return action(button, async () => {
      await api(`/api/agent/sessions/${encodeURIComponent(sessionId)}/acknowledge-cleanup`, { method: "POST", body: "{}" });
      await loadAgentSessions();
      notify("Đã dọn metadata của conversation khỏi scraper.");
    });
  }));
}

async function loadAgentSessions() {
  const payload = await api("/api/agent/sessions");
  state.agentSessions = payload.sessions || [];
  renderAgentSessions();
}

async function openAgentSessions() {
  $("#agent-sessions-modal").hidden = false;
  document.body.classList.add("sessions-open");
  $("#close-agent-sessions").focus();
  $("#agent-sessions-list").innerHTML = '<p class="docs-placeholder">Đang tải danh sách conversation…</p>';
  await loadAgentSessions();
}

function closeDocs() {
  $("#docs-modal").hidden = true;
  document.body.classList.remove("docs-open");
  $("#open-docs").focus();
}

function renderDocsList() {
  const root = $("#docs-list");
  $("#docs-count").textContent = `${state.documents.length} file`;
  if (!state.documents.length) {
    root.innerHTML = '<p class="docs-empty">Không tìm thấy file .md hoặc .txt trong scraper/docs.</p>';
    return;
  }
  root.innerHTML = state.documents.map((document) => `
    <button class="docs-file${document.path === state.currentDocument ? " active" : ""}" type="button" data-doc-path="${escapeHtml(document.path)}" title="${escapeHtml(document.path)}">
      <span class="docs-file-badge">${escapeHtml(document.extension.slice(1))}</span>
      <span class="docs-file-name">${escapeHtml(document.path)}</span>
    </button>`).join("");
  root.querySelectorAll("[data-doc-path]").forEach((button) => button.addEventListener("click", () => loadDocument(button.dataset.docPath)));
}

async function loadDocument(path) {
  const content = $("#docs-content");
  content.innerHTML = '<p class="docs-placeholder">Đang tải tài liệu…</p>';
  try {
    const document = await api(`/api/docs/content?path=${encodeURIComponent(path)}`);
    state.currentDocument = document.path;
    $("#docs-current-file").textContent = document.path;
    content.dataset.format = document.format;
    content.innerHTML = document.rendered_html;
    content.querySelectorAll("a[href]").forEach((link) => {
      if (/^https?:\/\//i.test(link.getAttribute("href") || "")) {
        link.target = "_blank";
        link.rel = "noopener noreferrer";
      }
    });
    content.scrollTop = 0;
    $("#docs-scroll-bottom").disabled = false;
    renderDocsList();
  } catch (error) {
    content.removeAttribute("data-format");
    content.innerHTML = `<p class="docs-placeholder error">Không thể tải tài liệu: ${escapeHtml(error.message)}</p>`;
    $("#docs-scroll-bottom").disabled = true;
  }
}

async function openDocs() {
  const modal = $("#docs-modal");
  modal.hidden = false;
  document.body.classList.add("docs-open");
  $("#close-docs").focus();
  const payload = await api("/api/docs");
  state.documents = payload.documents || [];
  renderDocsList();
  const preferred = state.documents.some((item) => item.path === state.currentDocument) ? state.currentDocument : state.documents[0]?.path;
  if (preferred) await loadDocument(preferred);
  else {
    state.currentDocument = null;
    $("#docs-current-file").textContent = "Chưa có tài liệu";
    $("#docs-content").innerHTML = '<p class="docs-placeholder">Không tìm thấy file .md hoặc .txt trong scraper/docs.</p>';
    $("#docs-scroll-bottom").disabled = true;
  }
}

function setButtonText(button, text) {
  const label = button.querySelector(".button-label"); if (label) label.textContent = text;
}

function handleMultiValuePaste(event, fieldName, startRow) {
  const clipboardData = event.clipboardData || window.clipboardData;
  if (!clipboardData) return;
  const rawText = clipboardData.getData("text") || "";
  const items = rawText
    .split(/[\r\n,\t]+/)
    .map((item) => item.trim())
    .filter(Boolean);

  if (items.length <= 1) return;

  event.preventDefault();

  const allRows = Array.from(document.querySelectorAll("#products-body .product-row"));
  const startIndex = allRows.indexOf(startRow);
  if (startIndex === -1) return;

  const baseConfig = readRow(startRow);

  items.forEach((value, index) => {
    const targetIndex = startIndex + index;
    let targetRow;
    if (targetIndex < allRows.length) {
      targetRow = allRows[targetIndex];
    } else {
      targetRow = addRow({
        mode: baseConfig.mode,
        preset: baseConfig.preset,
        overrides: baseConfig.overrides,
      });
      allRows.push(targetRow);
    }
    const input = targetRow.querySelector(`[data-field="${fieldName}"]`);
    if (input) {
      input.value = value;
      if (["amazon_url", "shopify_product_id"].includes(fieldName)) clearStoreExistence(targetRow);
    }
  });

  updatePreview();
  notify(`Đã tự động điền ${items.length} giá trị vào các dòng.`);
}

function addRow(product = {}) {
  const row = $("#product-row-template").content.firstElementChild.cloneNode(true);
  const overrides = product.overrides || {};
  const values = {
    amazon_url: product.amazon_url || "", shopify_product_id: product.shopify_product_id || "", mode: product.mode || "auto",
    furniture_type: product.preset?.furniture_type || "", price_tier: product.preset?.price_tier || "",
    product_type: overrides.product_type || "", tags: Array.isArray(overrides.tags) ? overrides.tags.join(", ") : (overrides.tags || ""),
    status: overrides.status || "ACTIVE",
  };
  Object.entries(values).forEach(([key, value]) => { row.querySelector(`[data-field="${key}"]`).value = value; });
  const togglePreset = () => { row.querySelector(".preset-fields").hidden = row.querySelector('[data-field="mode"]').value !== "preset"; updatePreview(); };
  row.querySelectorAll("input,select").forEach((input) => input.addEventListener("input", updatePreview));
  row.querySelector('[data-field="mode"]').addEventListener("change", togglePreset);
  const productTypeInput = row.querySelector('[data-field="product_type"]');
  productTypeInput.addEventListener("click", () => openProductTypePicker(productTypeInput));
  productTypeInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openProductTypePicker(productTypeInput);
    }
  });
  const amazonUrlInput = row.querySelector('[data-field="amazon_url"]');
  amazonUrlInput.addEventListener("input", () => clearStoreExistence(row));
  amazonUrlInput.addEventListener("paste", (event) => handleMultiValuePaste(event, "amazon_url", row));
  const shopifyIdInput = row.querySelector('[data-field="shopify_product_id"]');
  shopifyIdInput.addEventListener("input", () => clearStoreExistence(row));
  shopifyIdInput.addEventListener("paste", (event) => handleMultiValuePaste(event, "shopify_product_id", row));
  row.querySelector('[data-action="remove"]').addEventListener("click", () => { row.remove(); updatePreview(); });
  row.querySelector('[data-action="duplicate"]').addEventListener("click", () => addRow(readRow(row)));
  $("#products-body").append(row); togglePreset(); applyAgentGate(); updatePreview();
  return row;
}

function clearStoreExistence(row) {
  const status = row.querySelector('[data-role="store-existence"]');
  status.hidden = true;
  status.textContent = "";
  status.className = "store-existence-status";
  row.classList.remove("store-product-exists", "store-product-conflict");
}

function renderShopifyPreflight(preflight) {
  const allRows = Array.from(document.querySelectorAll("#products-body .product-row"));
  allRows.forEach(clearStoreExistence);
  const rows = manifestRows();
  (preflight.products || []).forEach((result) => {
    const row = rows[result.index];
    if (!row || !result.exists) return;
    const status = row.querySelector('[data-role="store-existence"]');
    const ids = (result.matches || []).map((item) => item.shopify_product_id).filter(Boolean);
    const uniqueIds = [...new Set(ids)];
    const matchesTarget = Boolean(result.matches_target_product);
    status.hidden = false;
    status.classList.add(matchesTarget ? "matched" : "conflict");
    status.textContent = matchesTarget
      ? `✓ ASIN ${result.asin} đã tồn tại trên sản phẩm này`
      : `! ASIN ${result.asin} đã tồn tại ở Shopify ID ${uniqueIds.join(", ")}`;
    status.title = (result.matches || []).map((item) => `${item.title || "Untitled"} · ${item.amazon_url}`).join("\n");
    row.classList.add(matchesTarget ? "store-product-exists" : "store-product-conflict");
  });
}

function readRow(row) {
  const get = (name) => row.querySelector(`[data-field="${name}"]`).value.trim();
  const mode = get("mode");
  const overrides = { product_type: get("product_type"), tags: get("tags").split(",").map((x) => x.trim()).filter(Boolean), status: get("status") };
  const item = { amazon_url: get("amazon_url"), shopify_product_id: get("shopify_product_id"), mode, overrides };
  if (mode === "preset") item.preset = { furniture_type: get("furniture_type"), price_tier: get("price_tier") };
  return item;
}

function collectManifest() {
  return { products: manifestRows().map(readRow) };
}

function manifestRows() {
  return [...document.querySelectorAll(".product-row")]
    .filter((row) => {
      const item = readRow(row);
      return item.amazon_url || item.shopify_product_id;
    });
}
function updatePreview() {
  state.manifest = collectManifest();
  $("#manifest-preview").textContent = JSON.stringify(state.manifest, null, 2);
  $("#hero-product-count").textContent = state.manifest.products.length;
  const rowCountBadge = $("#manifest-row-count");
  if (rowCountBadge) {
    rowCountBadge.textContent = document.querySelectorAll("#products-body .product-row").length;
  }
}

function optionsPayload() {
  return { headless: $("#headless").checked, dry_run: $("#dry-run").checked, max_combinations: Number($("#max-combinations").value), amazon_postal_code: $("#postal-code").value.trim() };
}

function tone(status) {
  if (["applied", "completed", "dry_run_complete"].includes(status)) return "success";
  if (["failed", "needs_attention", "completed_with_errors"].includes(status)) return "error";
  if (["content_queued", "content_claimed", "waiting_for_content", "interrupted", "initializing", "starting"].includes(status)) return "warning";
  if (["crawling", "applying", "running", "apply_queued", "busy", "ready"].includes(status)) return "running";
  return "neutral";
}

function updateBatchFlowIndicator() {
  const indicator = $("#batch-flow-indicator");
  const activeStatuses = new Set(["crawling", "waiting_for_content", "applying"]);
  const activeRuns = state.runs.filter((run) => activeStatuses.has(run.status));
  const isRunning = activeRuns.length > 0;
  indicator.classList.toggle("running", isRunning);
  indicator.classList.toggle("stopped", !isRunning);
  if (!isRunning) {
    $("#batch-flow-title").textContent = "Batch đã dừng";
    return;
  }
  const phase = activeRuns.some((run) => run.status === "applying")
    ? "Đang sync Shopify"
    : (activeRuns.some((run) => run.status === "crawling") ? "Đang crawl Amazon" : "Đang xử lý content");
  $("#batch-flow-title").textContent = "Batch đang chạy";
}

function applyAgentGate() {
  if (state.currentTask) {
    const taskLocked = state.currentTask.state === "claimed" || state.currentTask.is_final;
    Object.values(fieldIds).forEach((id) => { $("#" + id).disabled = taskLocked; });
    $("#save-content").disabled = taskLocked; $("#finalize-content").disabled = taskLocked;
  }
  const hint = $("#run-hint");
  if (hint) hint.textContent = state.agentReady
    ? "Một crawler, một Antigravity turn và một Shopify worker; mỗi hàng đợi chạy tuần tự."
    : "Crawler có thể chạy ngay; content queue sẽ tự tiếp tục khi Antigravity sẵn sàng.";
}

function updateAgentStartupToast(agent) {
  const toast = $("#agent-startup-toast");
  const status = agent?.status || "starting";
  if (state.agentReady) {
    toast.hidden = true;
    toast.classList.remove("error");
    return;
  }
  toast.hidden = false;
  const failed = ["failed", "stopped", "interrupted"].includes(status);
  toast.classList.toggle("error", failed);
  $("#agent-startup-title").textContent = failed ? "Antigravity chưa sẵn sàng" : "Đang khởi động Antigravity";
  $("#agent-startup-message").textContent = failed
    ? (agent?.message || "Không thể khởi tạo conversation. Hãy kiểm tra Event log rồi khởi động lại Agent.")
    : (agent?.message || "Server đang tạo conversation và kiểm tra kết nối MCP trong nền. Crawler vẫn có thể chạy.");
}

function updateAgent(agent) {
  state.agent = agent || {}; state.agentReady = Boolean(agent?.ready);
  const status = agent?.status || "stopped";
  $("#agent-status").textContent = status.toUpperCase(); $("#agent-status").className = `status-pill ${tone(status)}`;
  $("#agent-status-tooltip").textContent = agentStatusHelp[status] || "Trạng thái runtime Antigravity hiện tại.";
  $("#agent-message").textContent = agent?.message || "Không có trạng thái Antigravity.";
  $("#agent-conversation").textContent = agent?.conversation_id ? String(agent.conversation_id).slice(0, 12) : "—";
  $("#agent-pid").textContent = agent?.pid || "—"; $("#agent-turns").textContent = agent?.num_turns || 0;
  $("#agent-current-task").textContent = agent?.current_asin || (agent?.current_product_id ? String(agent.current_product_id).slice(0, 10) : "—");
  $("#agent-last-activity").textContent = agent?.last_activity_at ? new Date(agent.last_activity_at).toLocaleTimeString("vi-VN") : "—";
  $("#restart-agent").hidden = !["failed", "stopped", "interrupted"].includes(status);
  $("#check-agent").disabled = status !== "ready";
  updateAgentStartupToast(agent);
  applyAgentGate();
}

function updateQueue(queue) {
  const content = queue.content || {}, apply = queue.apply || {};
  $("#count-queued").textContent = content.queued || 0;
  $("#count-claimed").textContent = content.claimed || 0;
  $("#count-ready").textContent = content.ready || 0;
  $("#count-applying").textContent = apply.running || 0;
  $("#count-failed").textContent = queue.failed || 0;
}

function stagePercent(status) {
  return ({ pending: 5, crawling: 15, crawled: 28, price_verified: 38, content_queued: 45, content_claimed: 55,
    content_ready: 65, apply_queued: 70, applying: 82, applied: 100, dry_run_complete: 100,
    failed: 100, needs_attention: 100, cancelled: 100 })[status] || 5;
}

function renderRun(run) {
  state.currentRun = run;
  $("#job-id").textContent = run ? `run ${run.id.slice(0, 12)}` : "Chưa có run";
  $("#hero-job-state").textContent = run ? run.status.replaceAll("_", " ") : "Sẵn sàng";
  $("#hero-job-state").className = `status-pill ${tone(run?.status)}`;
  $("#resume-crawl").hidden = !run || run.crawl_status !== "interrupted";
  const products = run ? Object.values(run.products || {}) : [];
  const root = $("#product-progress");
  if (!products.length) { root.className = "product-progress empty-state"; root.textContent = "Chạy một batch để xem tiến trình từng ASIN."; }
  else {
    root.className = "product-progress";
    root.innerHTML = products.map((product, index) => {
      const task = product.content_task;
      const checkpoints = Object.keys(product.shopify_checkpoint || {});
      const meta = task ? ` · rev ${task.revision}${task.queue_position ? ` · queue #${task.queue_position}` : ""}${task.lease_expires_at ? ` · lease ${new Date(task.lease_expires_at).toLocaleTimeString("vi-VN")}` : ""}${checkpoints.length ? ` · checkpoint ${checkpoints.at(-1)}` : ""}` : "";
      const retryAction = product.apply_task
        ? `<button class="text-button" data-product-action="retry-shopify" data-product-id="${product.id}">Retry Shopify</button>`
        : (task?.state === "error" && !task?.is_final
          ? `<button class="text-button" data-product-action="retry-content" data-product-id="${product.id}">Retry content</button>` : "");
      const actions = product.status === "needs_attention" ? `<div class="card-actions">${retryAction}<button class="text-button" data-product-action="close" data-product-id="${product.id}">Acknowledge & close</button></div>` : "";
      return `<article class="product-card"><span class="product-index">#${index + 1}</span><div><strong>${product.asin}</strong><small>${product.amazon_url}</small></div><div><small>${product.status}${meta}</small><div class="progress-track"><span style="width:${stagePercent(product.status)}%"></span></div>${product.error ? `<small class="error-text">${escapeHtml(product.error)}</small>` : ""}${actions}</div><span class="status-pill ${tone(product.status)}">${labels[product.status] || product.status}</span></article>`;
    }).join("");
    root.querySelectorAll("[data-product-action]").forEach((button) => button.addEventListener("click", () => action(button, async () => {
      const endpoint = button.dataset.productAction === "retry-shopify"
        ? `/api/apply-tasks/${button.dataset.productId}/retry`
        : (button.dataset.productAction === "retry-content"
          ? `/api/content-tasks/${button.dataset.productId}/retry`
          : `/api/products/${button.dataset.productId}/acknowledge`);
      await api(endpoint, { method: "POST", body: "{}" }); await refreshState();
    })));
  }
  updateStepper(run);
  updateContentSelector(products);
  applyAgentGate();
}

function escapeHtml(value) { const node = document.createElement("span"); node.textContent = String(value); return node.innerHTML; }

function updateStepper(run) {
  const steps = [...document.querySelectorAll("#stepper li")]; steps.forEach((item) => item.className = "");
  if (!run) return;
  const products = Object.values(run.products || {}), statuses = new Set(products.map((p) => p.status));
  steps[0].className = "done";
  if (run.crawl_status === "complete") steps[1].className = "done"; else steps[1].className = "active";
  if (statuses.size && [...statuses].every((s) => ["apply_queued", "applying", "applied", "dry_run_complete", "needs_attention", "failed"].includes(s))) steps[2].className = "done";
  else if (statuses.has("content_queued") || statuses.has("content_claimed")) steps[2].className = "active";
  if (statuses.has("applying") || statuses.has("apply_queued")) steps[3].className = "active";
  if (statuses.size && [...statuses].every((s) => ["applied", "dry_run_complete", "failed", "needs_attention", "cancelled"].includes(s))) { steps[3].className = "done"; steps[4].className = "done"; }
}

function updateContentSelector(products) {
  const select = $("#content-product"), previous = select.value;
  const eligible = products.filter((p) => p.content_task);
  select.innerHTML = eligible.length ? eligible.map((p) => `<option value="${p.id}">${p.asin} · ${labels[p.status] || p.status}</option>`).join("") : '<option value="">Chưa có content task</option>';
  if (eligible.some((p) => p.id === previous)) select.value = previous;
  if (!select.value) clearEditor(); else if (!state.currentTask || state.currentTask.task_id !== select.value) loadTask(select.value);
}

function clearEditor() { state.currentTask = null; $("#content-editor-empty").hidden = false; $("#content-editor-form").hidden = true; }

async function loadTask(taskId) {
  if (!taskId) return clearEditor();
  try {
    const task = await api(`/api/content-tasks/${taskId}/draft`); state.currentTask = task;
    Object.entries(fieldIds).forEach(([field, id]) => { $("#" + id).value = task.content?.[field] || ""; });
    const visual = task.visual_analysis;
    $("#visual-analysis-state").textContent = visual ? "Sẵn sàng" : "Chưa có";
    $("#visual-analysis-state").className = `status-pill ${visual ? "success" : "neutral"}`;
    $("#visual-target").textContent = visual ? `Target: ${visual.target_identity} · ${visual.evidence_ids.length} evidence` : "Agent chưa xác định sản phẩm chính trong gallery.";
    const keywords = visual ? [...(visual.design_keywords || []), ...(visual.shape_keywords || [])] : [];
    $("#visual-keywords").innerHTML = keywords.map((value) => `<span>${escapeHtml(value)}</span>`).join("");
    const collisions = task.content_validation?.collisions || [];
    $("#content-collisions").hidden = !collisions.length;
    $("#content-collisions").innerHTML = collisions.length ? `<strong>Content collision</strong><br>${collisions.map((item) => `${escapeHtml(item.field)} ↔ ${escapeHtml(item.conflicting_asin)} (${Number(item.score).toFixed(2)})`).join("<br>")}` : "";
    $("#content-editor-empty").hidden = true; $("#content-editor-form").hidden = false;
    const locked = task.state === "claimed" || task.is_final;
    Object.values(fieldIds).forEach((id) => { $("#" + id).disabled = locked; });
    $("#save-content").disabled = locked; $("#finalize-content").disabled = locked;
    $("#release-claim").hidden = task.state !== "claimed";
    $("#requeue-content").hidden = !task.is_final;
    const product = Object.values(state.currentRun?.products || {}).find((p) => p.id === task.task_id);
    $("#retry-content").hidden = !(product?.status === "needs_attention" && task.state === "error" && !task.is_final);
    $("#retry-shopify").hidden = !(product?.status === "needs_attention" && product?.apply_task);
    $("#acknowledge-product").hidden = product?.status !== "needs_attention";
    const status = $("#content-validation-status"); status.textContent = task.valid ? "Hợp lệ" : "Chưa hợp lệ"; status.className = `status-pill ${task.valid ? "success" : "warning"}`;
    $("#content-editor-message").textContent = task.state === "claimed" ? `Read-only: ${task.claimed_by || "Agent"} giữ claim đến ${new Date(task.lease_expires_at).toLocaleString("vi-VN")}.` : (task.validation_error || `State: ${task.state} · revision ${task.revision}`);
    updateCounts(); applyAgentGate();
  } catch (error) { clearEditor(); notify(error.message, true); }
}

function collectContent() { const output = {}; Object.entries(fieldIds).forEach(([key, id]) => { output[key] = $("#" + id).value.trim(); }); return output; }
function updateCounts() {
  Object.values(fieldIds).forEach((id) => { const target = document.querySelector(`[data-count-for="${id}"]`); if (target) target.textContent = `${$("#" + id).value.length} ký tự`; });
}

function renderHistory() {
  const root = $("#job-history");
  root.innerHTML = state.runs.length ? state.runs.map((run) => `<button class="history-item history-button" data-run="${run.id}"><span><strong>${run.id.slice(0, 12)}</strong><small>${new Date(run.created_at).toLocaleString("vi-VN")} · <span class="history-relative-time">${relativeElapsed(run.created_at)}</span> · ${Object.keys(run.products || {}).length} sản phẩm · crawl ${run.crawl_status}</small></span><span class="status-pill ${tone(run.status)}">${run.status.replaceAll("_", " ")}</span></button>`).join("") : '<div class="empty-state">Chưa có execution.</div>';
  root.querySelectorAll("[data-run]").forEach((button) => button.addEventListener("click", () => selectRun(button.dataset.run)));
  updateBatchFlowIndicator();
}

async function selectRun(id) { try { renderRun(await api(`/api/runs/${id}`)); } catch (error) { notify(error.message, true); } }

function eventText(event) {
  const at = event.at ? new Date(event.at).toLocaleTimeString("vi-VN") : "--";
  const subject = event.asin || (event.run_id ? event.run_id.slice(0, 8) : event.source || "system");
  const detail = event.message || event.status || event.error || event.worker_id || "";
  return `[${at}] ${subject} · ${event.source || "server"} · ${event.event}${detail ? ` · ${detail}` : ""}`;
}

function scheduleRefresh() { clearTimeout(state.refreshTimer); state.refreshTimer = setTimeout(refreshState, 250); }
async function refreshState() {
  try {
    const [runsData, queue, agent, sessionData] = await Promise.all([api("/api/runs"), api("/api/queue"), api("/api/agent"), api("/api/agent/sessions")]);
    state.runs = runsData.runs; state.agentSessions = sessionData.sessions || []; updateQueue(queue); updateAgent(agent); updateAgentCleanupCount(); renderHistory();
    if (!$("#agent-sessions-modal").hidden) renderAgentSessions();
    if (state.currentRun) {
      const run = state.runs.find((item) => item.id === state.currentRun.id);
      if (run) renderRun(run);
    } else if (state.runs[0]) renderRun(state.runs[0]);
  } catch (error) { notify(error.message, true); }
}

function renderEventLines(scrollToBottom = false) {
  const log = $("#event-log");
  log.textContent = state.eventLines.length ? `${state.eventLines.join("\n")}\n` : "";
  if (scrollToBottom) log.scrollTop = log.scrollHeight;
}

function flushPendingEvents() {
  state.eventFlushTimer = null;
  if (!state.pendingEvents.length) return;
  const log = $("#event-log");
  const wasNearBottom = log.scrollHeight - log.scrollTop - log.clientHeight < 80;
  const events = state.pendingEvents.splice(0);
  state.eventLines.push(...events.map(eventText));
  if (state.eventLines.length > MAX_EVENT_LOG_LINES) {
    state.eventLines.splice(0, state.eventLines.length - MAX_EVENT_LOG_LINES);
  }
  renderEventLines(wasNearBottom);
  scheduleRefresh();
}

function queueEvent(event) {
  const eventId = Number(event.id || 0);
  if (eventId && eventId <= state.eventCursor) return;
  if (eventId) state.eventCursor = eventId;
  state.pendingEvents.push(event);
  if (!state.eventFlushTimer) state.eventFlushTimer = setTimeout(flushPendingEvents, 100);
}

function connectEvents(after = 0) {
  if (state.eventSource) state.eventSource.close();
  const source = new EventSource(`/api/queue/events?after=${encodeURIComponent(after)}`);
  state.eventSource = source;
  source.onmessage = (message) => {
    try { queueEvent(JSON.parse(message.data)); } catch (_error) { /* Ignore malformed event frames. */ }
  };
  source.onerror = () => { $("#agent-message").textContent = "Event stream đang kết nối lại…"; };
}

async function initializeEventLog() {
  try {
    const payload = await api(`/api/events/recent?limit=${INITIAL_EVENT_LOG_LIMIT}`);
    const events = payload.events || [];
    state.eventLines = events.map(eventText).slice(-MAX_EVENT_LOG_LINES);
    state.eventCursor = Number(payload.cursor || 0);
    renderEventLines(true);
    connectEvents(state.eventCursor);
  } catch (error) {
    notify(`Không thể tải Event Log: ${error.message}`, true);
    connectEvents(state.eventCursor);
  }
}

async function action(button, callback) {
  loading(button, true);
  try { await callback(); } catch (error) { notify(error.message, true); } finally { loading(button, false); }
}

async function copyValue(button, value) {
  await action(button, async () => { await navigator.clipboard.writeText(value); notify("Đã copy vào clipboard."); });
}

async function bootstrap() {
  try {
    const data = await api("/api/bootstrap"); state.csrf = data.csrf_token; state.manifest = data.manifest; state.runs = data.runs; state.agentSessions = data.agent_sessions || [];
    state.productTypes = data.product_types || [];
    (data.manifest.products || []).forEach(addRow); if (!data.manifest.products?.length) addRow();
    $("#headless").checked = data.options.headless; $("#dry-run").checked = data.options.dry_run;
    $("#max-combinations").value = data.options.max_combinations; $("#postal-code").value = data.options.amazon_postal_code;
    updateQueue(data.queue); updateAgent(data.agent); updateAgentCleanupCount(); renderHistory(); renderRun(state.runs[0] || null); updatePreview();
    initializeEventLog();
  } catch (error) { notify(error.message, true); }
}

function updatePageScrollControls() {
  const root = document.documentElement;
  const maxScroll = Math.max(0, root.scrollHeight - window.innerHeight);
  $("#page-scroll-top").disabled = window.scrollY <= 4;
  $("#page-scroll-bottom").disabled = window.scrollY >= maxScroll - 4;
}

$("#add-product").addEventListener("click", () => addRow());
$("#save-manifest").addEventListener("click", (event) => action(event.currentTarget, async () => { await api("/api/manifest", { method: "PUT", body: JSON.stringify(collectManifest()) }); notify("Đã lưu products.json atomically."); }));
$("#run-batch").addEventListener("click", (event) => action(event.currentTarget, async () => {
  const manifest = collectManifest();
  const result = await api("/api/runs", { method: "POST", body: JSON.stringify({
    manifest,
    options: optionsPayload(),
    skip_existing_store_products: true,
  }) });
  renderShopifyPreflight(result.preflight);
  if (!result.run) {
    notify(`Đã bỏ qua ${result.skipped_existing} row vì toàn bộ sản phẩm đã tồn tại trên store.`);
    return;
  }
  const run = result.run;
  state.runs.unshift(run); renderHistory(); renderRun(run);
  notify(result.skipped_existing
    ? `Đã tạo run cho ${Object.keys(run.products || {}).length} sản phẩm; bỏ qua ${result.skipped_existing} row đã tồn tại.`
    : `Đã tạo run. Tiền kiểm tra ${result.preflight.checked} sản phẩm không phát hiện ASIN đã tồn tại.`);
}));
$("#resume-crawl").addEventListener("click", (event) => action(event.currentTarget, async () => { renderRun(await api(`/api/runs/${state.currentRun.id}/resume-crawl`, { method: "POST", body: "{}" })); notify("Crawler đã được đưa lại vào queue."); }));
$("#restart-agent").addEventListener("click", (event) => action(event.currentTarget, async () => { updateAgent(await api("/api/agent/restart", { method: "POST", body: "{}" })); notify("Đang khởi động một Antigravity conversation mới."); }));
$("#check-agent").addEventListener("click", (event) => action(event.currentTarget, async () => {
  const result = await api("/api/agent/health-check", { method: "POST", body: "{}" });
  updateAgent(result.agent);
  notify(`Antigravity đang hoạt động. Thời gian phản hồi lệch ${Math.round(result.drift_seconds)} giây.`);
}));
$("#open-agent-sessions").addEventListener("click", (event) => action(event.currentTarget, openAgentSessions));
$("#close-agent-sessions").addEventListener("click", closeAgentSessions);
$("#close-agent-sessions-footer").addEventListener("click", closeAgentSessions);
$("#agent-sessions-modal").addEventListener("click", (event) => { if (event.target === event.currentTarget) closeAgentSessions(); });
$("#reload-agent-sessions").addEventListener("click", (event) => action(event.currentTarget, loadAgentSessions));
$("#content-product").addEventListener("change", (event) => loadTask(event.target.value));
$("#reload-content").addEventListener("click", (event) => action(event.currentTarget, () => loadTask($("#content-product").value)));
$("#content-editor-form").addEventListener("input", updateCounts);
$("#content-editor-form").addEventListener("submit", (event) => { event.preventDefault(); action($("#save-content"), async () => { await api(`/api/content-tasks/${state.currentTask.task_id}/draft`, { method: "PUT", body: JSON.stringify({ content: collectContent() }) }); await loadTask(state.currentTask.task_id); notify("Đã lưu content.temp.json."); }); });
$("#finalize-content").addEventListener("click", (event) => action(event.currentTarget, async () => { await api(`/api/content-tasks/${state.currentTask.task_id}/finalize`, { method: "POST", body: "{}" }); await refreshState(); await loadTask(state.currentTask.task_id); notify("Content hợp lệ và đã vào Shopify queue."); }));
$("#release-claim").addEventListener("click", (event) => action(event.currentTarget, async () => { await api(`/api/content-tasks/${state.currentTask.task_id}/release`, { method: "POST", body: JSON.stringify({ reason: "Released manually from Dashboard." }) }); await refreshState(); await loadTask(state.currentTask.task_id); }));
$("#requeue-content").addEventListener("click", (event) => action(event.currentTarget, async () => { await api(`/api/content-tasks/${state.currentTask.task_id}/requeue`, { method: "POST", body: "{}" }); await refreshState(); await loadTask(state.currentTask.task_id); notify("Đã trả content về queue và tăng revision."); }));
$("#retry-content").addEventListener("click", (event) => action(event.currentTarget, async () => { await api(`/api/content-tasks/${state.currentTask.task_id}/retry`, { method: "POST", body: "{}" }); await refreshState(); await loadTask(state.currentTask.task_id); notify("Đã queue lại content bằng một Agent session mới."); }));
$("#retry-shopify").addEventListener("click", (event) => action(event.currentTarget, async () => { await api(`/api/apply-tasks/${state.currentTask.task_id}/retry`, { method: "POST", body: "{}" }); await refreshState(); notify("Đã queue Retry Shopify từ checkpoint."); }));
$("#acknowledge-product").addEventListener("click", (event) => action(event.currentTarget, async () => { await api(`/api/products/${state.currentTask.task_id}/acknowledge`, { method: "POST", body: "{}" }); await refreshState(); notify("Đã đóng task; ASIN và Shopify product ID được giải phóng."); }));
$("#log-scroll-bottom").addEventListener("click", () => { const log = $("#event-log"); log.scrollTop = log.scrollHeight; log.focus({ preventScroll: true }); });
$("#page-view-log").addEventListener("click", () => $(".progress-panel").scrollIntoView());
$("#page-scroll-top").addEventListener("click", () => window.scrollTo(0, 0));
$("#page-scroll-bottom").addEventListener("click", () => window.scrollTo(0, document.documentElement.scrollHeight));
$("#close-product-type").addEventListener("click", closeProductTypePicker);
$("#product-type-modal").addEventListener("click", (event) => { if (event.target === event.currentTarget) closeProductTypePicker(); });
$("#product-type-custom").addEventListener("input", () => renderProductTypeOptions($("#product-type-custom").value.trim()));
$("#apply-product-type").addEventListener("click", () => {
  const value = $("#product-type-custom").value.trim();
  if (!value) {
    $("#product-type-status").textContent = "Hãy chọn hoặc nhập một product type.";
    return;
  }
  if (state.productTypeTarget?.isConnected) {
    state.productTypeTarget.value = value;
    state.productTypeTarget.dispatchEvent(new Event("input", { bubbles: true }));
  }
  closeProductTypePicker();
});
window.addEventListener("scroll", updatePageScrollControls, { passive: true });
window.addEventListener("resize", updatePageScrollControls);
$("#clear-log").addEventListener("click", () => {
  state.eventLines = [];
  state.pendingEvents = [];
  renderEventLines();
});
$("#open-docs").addEventListener("click", (event) => action(event.currentTarget, openDocs));
$("#close-docs").addEventListener("click", closeDocs);
$("#docs-modal").addEventListener("click", (event) => { if (event.target === event.currentTarget) closeDocs(); });
$("#docs-scroll-bottom").addEventListener("click", () => { const content = $("#docs-content"); content.scrollTop = content.scrollHeight; content.focus({ preventScroll: true }); });
$("#open-prompts").addEventListener("click", (event) => action(event.currentTarget, openPrompts));
$("#close-prompts").addEventListener("click", closePrompts);
$("#prompts-modal").addEventListener("click", (event) => { if (event.target === event.currentTarget) closePrompts(); });
$("#prompts-form").addEventListener("submit", (event) => { event.preventDefault(); action($("#save-prompts"), savePrompts); });
$("#agent-prompt-editor").addEventListener("input", updatePromptCounts);
$("#content-task-prompt-editor").addEventListener("input", updatePromptCounts);
document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (!$("#product-type-modal").hidden) closeProductTypePicker();
  else if (!$("#agent-sessions-modal").hidden) closeAgentSessions();
  else if (!$("#prompts-modal").hidden) closePrompts();
  else if (!$("#docs-modal").hidden) closeDocs();
});

applyAgentGate();
updatePageScrollControls();
bootstrap();
window.setInterval(() => {
  renderHistory();
  if (!$("#agent-sessions-modal").hidden) renderAgentSessions();
}, 60000);
