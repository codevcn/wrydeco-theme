(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const state = {
    csrf: "", currentJob: null, events: null, agentEvents: null, agentEventCursor: 0,
    jobs: [], agentConfigured: null, agent: null, jobRefreshTimer: null, agentRefreshTimer: null,
    contentJobId: null, contentAsin: null, contentPayload: {}
  };
  const terminal = new Set(["applied", "completed", "failed", "needs_attention", "waiting_for_agent", "interrupted"]);
  const statusLabels = {
    pending: "Chờ", crawled: "Đã crawl", price_verified: "Giá đã verify", waiting_for_content: "Chờ content",
    content_ready: "Content sẵn sàng", applied: "Đã sync", failed: "Thất bại", needs_attention: "Cần chú ý",
    running: "Đang chạy", queued: "Trong hàng", agent_running: "Antigravity", waiting_for_agent: "Chờ Agent",
    completed: "Dry run xong", interrupted: "Bị gián đoạn"
  };

  function notify(message, error = false) {
    const node = $("#notice");
    node.textContent = message;
    node.classList.toggle("error", error);
    node.hidden = false;
    window.clearTimeout(notify.timer);
    notify.timer = window.setTimeout(() => { node.hidden = true; }, 5500);
  }

  function setButtonLoading(button, loading) {
    if (!button) return;
    button.classList.toggle("is-loading", loading);
    button.setAttribute("aria-busy", String(loading));
    button.disabled = loading;
  }

  function tags(value) {
    return String(value || "").split(",").map(item => item.trim()).filter(Boolean);
  }

  function addProduct(product = {}) {
    const fragment = $("#product-row-template").content.cloneNode(true);
    const row = $("tr", fragment);
    const overrides = product.overrides || {};
    const values = {
      amazon_url: product.amazon_url || "", shopify_product_id: product.shopify_product_id || "",
      mode: product.mode || "auto", furniture_type: product.preset?.furniture_type || "",
      price_tier: product.preset?.price_tier || "", product_type: overrides.product_type || "",
      tags: Array.isArray(overrides.tags) ? overrides.tags.join(", ") : (overrides.tags || "source_amazon"),
      status: overrides.status || "ACTIVE"
    };
    Object.entries(values).forEach(([key, value]) => { $(`[data-field="${key}"]`, row).value = value; });
    $("[data-action=remove]", row).addEventListener("click", () => { row.remove(); refreshPreview(); });
    $("[data-action=duplicate]", row).addEventListener("click", () => addProduct(productFromRow(row)));
    $("[data-field=mode]", row).addEventListener("change", () => { togglePreset(row); refreshPreview(); });
    $$('input, select', row).forEach(input => input.addEventListener("input", refreshPreview));
    $("#products-body").append(row);
    togglePreset(row);
    refreshPreview();
  }

  function togglePreset(row) {
    $(".preset-fields", row).hidden = $("[data-field=mode]", row).value !== "preset";
  }

  function productFromRow(row) {
    const value = name => $(`[data-field="${name}"]`, row).value.trim();
    const mode = value("mode");
    const item = { amazon_url: value("amazon_url"), shopify_product_id: value("shopify_product_id"), mode };
    if (mode === "preset") item.preset = { furniture_type: value("furniture_type"), price_tier: value("price_tier") };
    const overrides = { status: value("status"), product_type: value("product_type"), tags: tags(value("tags")) };
    item.overrides = overrides;
    return item;
  }

  function manifest() { return { products: $$(".product-row").map(productFromRow) }; }

  function refreshPreview() {
    const payload = manifest();
    $("#manifest-preview").textContent = JSON.stringify(payload, null, 2);
    $("#hero-product-count").textContent = payload.products.length;
  }

  async function api(path, options = {}) {
    const method = options.method || "GET";
    const headers = { ...(options.headers || {}) };
    if (method !== "GET") {
      headers["Content-Type"] = "application/json";
      headers["X-CSRF-Token"] = state.csrf;
    }
    const response = await fetch(path, { ...options, method, headers });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    return data;
  }

  function runOptions() {
    return {
      headless: $("#headless").checked, dry_run: $("#dry-run").checked,
      amazon_postal_code: $("#postal-code").value.trim(),
      max_combinations: Number($("#max-combinations").value)
    };
  }

  function setBusy(busy) {
    setButtonLoading($("#run-batch"), busy);
    $("#save-manifest").disabled = busy;
    $("#add-product").disabled = busy;
  }

  function renderAgent(agent) {
    if (!agent) return;
    state.agent = agent;
    state.agentConfigured = Boolean(agent.configured);
    const status = agent.status || "disconnected";
    const labels = {
      disconnected: "Chưa kết nối", connecting: "Đang kết nối", connected: "Đã kết nối",
      busy: "Đang xử lý", error: "Kết nối lỗi"
    };
    const badge = $("#agent-connection-status");
    badge.textContent = labels[status] || status;
    badge.className = `status-pill ${status === "connected" ? "success" : (["connecting", "busy"].includes(status) ? "running" : (status === "error" ? "error" : "neutral"))}`;
    const dot = $("#agent-connection-dot");
    dot.className = `connection-dot ${status}`;
    $("#agent-connection-message").textContent = agent.message || "Không có thông tin trạng thái.";
    const conversation = agent.conversation_id ? `${agent.conversation_id.slice(0, 8)}… · ${agent.num_turns || 0} turns` : "—";
    $("#agent-conversation-id").textContent = `Conversation: ${conversation}`;
    setButtonLoading($("#connect-agent"), ["connecting", "busy"].includes(status));
    $("#connect-agent").disabled = ["connecting", "busy"].includes(status);
    if (!agent.configured) {
      const detail = agent.configuration_error ? ` (${agent.configuration_error})` : "";
      $("#run-hint").textContent = `Antigravity chưa cấu hình${detail}. Batch sẽ dừng sau bước verify giá để chờ content.json.`;
    } else {
      $("#run-hint").textContent = "Server chỉ cho phép một batch hoạt động tại một thời điểm.";
    }
  }

  const contentFieldIds = {
    title: "content-title",
    seo_product_title: "content-seo-product-title",
    seo_title: "content-seo-title",
    handle: "content-handle",
    seo_description: "content-seo-description",
    description_html: "content-description-html"
  };

  function contentPayloadFromForm() {
    const payload = { ...(state.contentPayload || {}) };
    Object.entries(contentFieldIds).forEach(([field, id]) => { payload[field] = $(`#${id}`).value.trim(); });
    return payload;
  }

  function updateContentCounters() {
    const ranges = {
      "content-title": [50, 70], "content-seo-product-title": [50, 70],
      "content-seo-title": [50, 60], "content-handle": [50, 60],
      "content-seo-description": [150, 160]
    };
    Object.entries(ranges).forEach(([id, [minimum, maximum]]) => {
      const input = $(`#${id}`), count = input.value.trim().length;
      const counter = $(`[data-count-for="${id}"]`);
      counter.textContent = `${count} / ${minimum}–${maximum}`;
      input.closest(".content-field").classList.toggle("invalid", count > 0 && (count < minimum || count > maximum));
    });
  }

  function renderContentValidation(valid, message) {
    const badge = $("#content-validation-status");
    badge.textContent = valid === true ? "Hợp lệ" : (valid === false ? "Chưa hợp lệ" : "Chưa tải");
    badge.className = `status-pill ${valid === true ? "success" : (valid === false ? "error" : "neutral")}`;
    $("#content-editor-message").textContent = message || "Các field được validate theo scraper/content.py trước khi lưu.";
  }

  async function loadContent() {
    if (!state.contentJobId || !state.contentAsin) return;
    const button = $("#reload-content");
    setButtonLoading(button, true);
    const expectedJob = state.contentJobId, expectedAsin = state.contentAsin;
    try {
      const data = await api(`/api/runs/${expectedJob}/products/${expectedAsin}/content`);
      if (state.contentJobId !== expectedJob || state.contentAsin !== expectedAsin) return;
      state.contentPayload = data.content || {};
      Object.entries(contentFieldIds).forEach(([field, id]) => { $(`#${id}`).value = state.contentPayload[field] || ""; });
      $("#content-editor-empty").hidden = true;
      $("#content-editor-form").hidden = false;
      renderContentValidation(data.exists ? data.valid : null,
        data.exists
          ? (data.validation_error || "content.json hợp lệ theo schema. Các ràng buộc Shopify như handle duy nhất sẽ được kiểm tra khi Resume.")
          : "Chưa có content.json; điền đủ các field để tạo file.");
      updateContentCounters();
    } catch (error) {
      renderContentValidation(false, error.message);
      notify(`Không tải được content.json: ${error.message}`, true);
    } finally {
      setButtonLoading(button, false);
    }
  }

  function configureContentEditor(job) {
    const select = $("#content-product");
    const asins = Object.keys(job?.products || {});
    if (!job || !asins.length) {
      state.contentJobId = null; state.contentAsin = null; state.contentPayload = {};
      select.innerHTML = "";
      $("#content-editor-form").hidden = true;
      $("#content-editor-empty").hidden = false;
      renderContentValidation(null);
      return;
    }
    const changedJob = state.contentJobId !== job.id;
    const optionSignature = asins.join("|");
    if (changedJob || select.dataset.signature !== optionSignature) {
      select.innerHTML = asins.map(asin => `<option value="${escapeHtml(asin)}">${escapeHtml(asin)}</option>`).join("");
      select.dataset.signature = optionSignature;
      state.contentJobId = job.id;
      state.contentAsin = asins[0];
      loadContent();
    }
  }

  async function saveContent(event) {
    event.preventDefault();
    if (!state.contentJobId || !state.contentAsin) return;
    const button = $("#save-content");
    setButtonLoading(button, true);
    try {
      const payload = contentPayloadFromForm();
      const data = await api(`/api/runs/${state.contentJobId}/products/${state.contentAsin}/content`, {
        method: "PUT", body: JSON.stringify(payload)
      });
      state.contentPayload = data.content;
      renderContentValidation(true, "content.json đã được validate và lưu atomic. Bạn có thể Resume checkpoint.");
      appendLog({ event: "content_saved", asin: state.contentAsin, message: "content.json đã được validate và lưu atomic." });
      notify(`Đã lưu content.json cho ${state.contentAsin}.`);
    } catch (error) {
      renderContentValidation(false, error.message);
      notify(`Không thể lưu content.json: ${error.message}`, true);
    } finally {
      setButtonLoading(button, false);
      updateContentCounters();
    }
  }

  function badgeClass(status) {
    if (["applied", "completed", "content_ready", "price_verified"].includes(status)) return "success";
    if (["failed", "needs_attention"].includes(status)) return "error";
    if (["waiting_for_agent", "interrupted", "waiting_for_content"].includes(status)) return "warning";
    if (["running", "queued", "agent_running", "crawled"].includes(status)) return "running";
    return "neutral";
  }

  function stageFor(job) {
    if (!job) return "manifest";
    if (["applied", "completed"].includes(job.status)) return "done";
    if (["agent_running", "waiting_for_agent"].includes(job.status)) return "agent";
    const products = Object.values(job.products || {});
    if (products.some(item => item.stage?.startsWith("media") || ["product_set", "metafields", "publications", "old_media_cleanup"].includes(item.stage))) return "shopify";
    if (products.some(item => ["content_ready", "applied"].includes(item.status))) return "shopify";
    if (products.some(item => item.status !== "pending")) return "crawl";
    return "manifest";
  }

  function renderJob(job) {
    if (!job) return;
    state.currentJob = job;
    $("#job-id").textContent = `${job.id.slice(0, 8)} · run ${job.run_id}`;
    const hero = $("#hero-job-state");
    hero.textContent = statusLabels[job.status] || job.status;
    hero.className = `status-pill ${badgeClass(job.status)}`;
    const currentStage = stageFor(job);
    const order = ["manifest", "crawl", "agent", "shopify", "done"];
    const position = order.indexOf(currentStage);
    $$("#stepper li").forEach((item, index) => {
      item.classList.toggle("active", index === position);
      item.classList.toggle("done", index < position || (currentStage === "done" && index === position));
    });
    const productRoot = $("#product-progress");
    productRoot.className = "product-progress";
    productRoot.innerHTML = "";
    Object.entries(job.products || {}).forEach(([asin, product]) => {
      const card = document.createElement("div");
      card.className = "product-card";
      const current = Number(product.current || 0), total = Number(product.total || 0);
      const progress = total ? Math.max(5, Math.round((current / total) * 100)) : (["applied"].includes(product.status) ? 100 : 8);
      card.innerHTML = `<div><strong>${asin}</strong><small>${escapeHtml(product.amazon_url || "")}</small></div>
        <div><small>${escapeHtml(product.stage || product.error || "Đang chờ checkpoint tiếp theo")}</small><div class="progress-track"><span style="width:${progress}%"></span></div></div>
        <span class="status-pill ${badgeClass(product.status)}">${escapeHtml(statusLabels[product.status] || product.status)}</span>`;
      productRoot.append(card);
    });
    const resumable = terminal.has(job.status) && !["applied", "completed"].includes(job.status);
    $("#resume-batch").hidden = !resumable;
    setBusy(!terminal.has(job.status));
    configureContentEditor(job);
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
  }

  function appendLog(event) {
    const log = $("#event-log");
    const time = new Date(event.at || Date.now()).toLocaleTimeString("vi-VN", { hour12: false });
    const detail = event.message || event.error || event.status || event.stage || event.price || "";
    log.textContent += `[${time}] ${event.asin ? event.asin + " · " : ""}${event.event}${detail ? " · " + detail : ""}\n`;
    log.scrollTop = log.scrollHeight;
  }

  function connectAgentEvents() {
    if (state.agentEvents) state.agentEvents.close();
    const source = new EventSource(`/api/antigravity/events?after=${state.agentEventCursor}`);
    state.agentEvents = source;
    source.addEventListener("antigravity", async message => {
      const event = JSON.parse(message.data);
      state.agentEventCursor = Math.max(state.agentEventCursor, Number(event.id || 0));
      appendLog(event);
      window.clearTimeout(state.agentRefreshTimer);
      state.agentRefreshTimer = window.setTimeout(async () => {
        try { renderAgent(await api("/api/antigravity")); } catch (_) {}
      }, 80);
    });
    source.onerror = async () => {
      source.close();
      try { renderAgent(await api("/api/antigravity")); } catch (_) {}
      window.setTimeout(connectAgentEvents, 1500);
    };
  }

  function connectEvents(jobId) {
    if (state.events) state.events.close();
    const source = new EventSource(`/api/runs/${jobId}/events`);
    state.events = source;
    source.addEventListener("progress", async message => {
      const event = JSON.parse(message.data);
      appendLog(event);
      window.clearTimeout(state.jobRefreshTimer);
      state.jobRefreshTimer = window.setTimeout(async () => {
        try {
          const job = await api(`/api/runs/${jobId}`);
          renderJob(job);
          if (terminal.has(job.status)) {
            source.close();
            await loadHistory();
          }
        } catch (_) {}
      }, 80);
    });
    source.onerror = async () => {
      source.close();
      try {
        const job = await api(`/api/runs/${jobId}`);
        renderJob(job);
        await loadHistory();
        if (!terminal.has(job.status)) window.setTimeout(() => connectEvents(jobId), 1500);
      } catch (_) {}
    };
  }

  async function saveManifest(showNotice = true) {
    const button = $("#save-manifest");
    setButtonLoading(button, true);
    try {
      const data = await api("/api/manifest", { method: "PUT", body: JSON.stringify(manifest()) });
      if (showNotice) notify(`Đã lưu ${data.products} sản phẩm · run ${data.run_id}`);
      return data;
    } finally {
      setButtonLoading(button, false);
    }
  }

  async function startRun() {
    setBusy(true);
    try {
      const job = await api("/api/runs", { method: "POST", body: JSON.stringify({
        manifest: manifest(), prompt: $("#agent-prompt").value, options: runOptions()
      }) });
      $("#event-log").textContent = "";
      renderJob(job);
      connectEvents(job.id);
      notify("Batch đã bắt đầu.");
    } catch (error) {
      setBusy(false); notify(error.message, true);
    }
  }

  async function resumeRun() {
    if (!state.currentJob) return;
    const button = $("#resume-batch");
    setButtonLoading(button, true);
    if (state.currentJob.status === "waiting_for_agent" && state.agentConfigured === false) {
      notify("Antigravity chưa được cấu hình. Hãy cấu hình ANTIGRAVITY_COMMAND_JSON hoặc tạo content.json thủ công trước khi Resume.", true);
    }
    setBusy(true);
    try {
      const job = await api(`/api/runs/${state.currentJob.id}/resume`, { method: "POST", body: "{}" });
      renderJob(job); connectEvents(job.id); notify("Đang resume từ checkpoint.");
    } catch (error) { setBusy(false); notify(error.message, true); }
    finally { setButtonLoading(button, false); }
  }

  async function connectAgent() {
    setButtonLoading($("#connect-agent"), true);
    try {
      const agent = await api("/api/antigravity/connect", { method: "POST", body: "{}" });
      renderAgent(agent);
      notify("Đang kết nối persistent conversation với Antigravity.");
    } catch (error) {
      setButtonLoading($("#connect-agent"), false);
      notify(error.message, true);
    }
  }

  async function loadHistory() {
    const data = await api("/api/runs");
    state.jobs = data.jobs;
    const root = $("#job-history");
    root.innerHTML = "";
    data.jobs.forEach(job => {
      const item = document.createElement("div");
      item.className = "history-item";
      item.innerHTML = `<div><strong>${job.run_id}</strong><small>${new Date(job.updated_at).toLocaleString("vi-VN")} · ${Object.keys(job.products || {}).length} sản phẩm</small></div><span class="status-pill ${badgeClass(job.status)}">${escapeHtml(statusLabels[job.status] || job.status)}</span>`;
      item.addEventListener("click", () => { renderJob(job); connectEvents(job.id); });
      root.append(item);
    });
    if (!data.jobs.length) root.innerHTML = '<div class="empty-state">Chưa có execution nào.</div>';
  }

  async function bootstrap() {
    try {
      const data = await api("/api/bootstrap");
      state.csrf = data.csrf_token;
      renderAgent(data.agent);
      (data.manifest.products || []).forEach(addProduct);
      if (!data.manifest.products?.length) addProduct();
      $("#agent-prompt").value = data.prompt;
      $("#headless").checked = data.defaults.headless;
      $("#dry-run").checked = data.defaults.dry_run;
      $("#postal-code").value = data.defaults.amazon_postal_code;
      $("#max-combinations").value = data.defaults.max_combinations;
      state.jobs = data.jobs;
      connectAgentEvents();
      await loadHistory();
      const active = data.jobs.find(job => !terminal.has(job.status)) || data.jobs[0];
      if (active) { renderJob(active); connectEvents(active.id); }
      refreshPreview();
    } catch (error) { notify(`Không tải được dashboard: ${error.message}`, true); }
  }

  $("#add-product").addEventListener("click", () => addProduct());
  $("#save-manifest").addEventListener("click", () => saveManifest().catch(error => notify(error.message, true)));
  $("#run-batch").addEventListener("click", startRun);
  $("#resume-batch").addEventListener("click", resumeRun);
  $("#connect-agent").addEventListener("click", connectAgent);
  $("#content-product").addEventListener("change", event => {
    state.contentAsin = event.target.value;
    loadContent();
  });
  $("#reload-content").addEventListener("click", loadContent);
  $("#content-editor-form").addEventListener("submit", saveContent);
  $$('[data-content-field]').forEach(input => input.addEventListener("input", updateContentCounters));
  $("#copy-prompt").addEventListener("click", async () => {
    const button = $("#copy-prompt");
    setButtonLoading(button, true);
    try { await navigator.clipboard.writeText($("#agent-prompt").value); notify("Đã copy prompt."); }
    finally { setButtonLoading(button, false); }
  });
  $("#clear-log").addEventListener("click", () => { $("#event-log").textContent = ""; });
  bootstrap();
})();
