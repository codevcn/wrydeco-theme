/* AEO-only Dashboard controls; the existing batch handlers stay independent. */
(() => {
  const root = document.querySelector("#store-aeo-panel");
  if (!root) return;
  const get = (id) => document.getElementById(id);
  const dialog = get("store-aeo-history-dialog");
  const expanded = new Map();
  let busy = false, refreshPromise = null, signature = "", reviewTicket = 0;
  let historyGeneration = 0, historyLoading = false, historyCursor = null, historyCount = 0;
  const statuses = {queued: "Chờ chạy", running: "Đang xử lý", paused: "Đã tạm dừng", interrupted: "Gián đoạn", completed: "Hoàn tất", exhausted: "Đã hết catalog", failed: "Job lỗi", written: "Đã ghi và xác minh", skipped: "Đã có AEO · bỏ qua", error: "Cần chú ý", not_needed: "Dừng vì đã đủ số lượng", pending: "Chờ xử lý", authoring: "Đang viết AEO", reviewing: "Đang đọc lại toàn bài", ready: "Đã kiểm định và review"};
  const text = (tag, value, className = "") => {
    const element = document.createElement(tag);
    element.textContent = value; element.className = className;
    return element;
  };
  function setBusy(button, active, label) {
    button.disabled = active;
    button.classList.toggle("is-loading", active);
    button.setAttribute("aria-busy", String(active));
    if (label) button.textContent = label;
  }
  function reportRefreshError(error) {
    get("store-aeo-status").textContent = `Không thể tải AEO: ${error.message}`;
  }

  async function reviewTask(task, button) {
    const ticket = ++reviewTicket, label = button.textContent;
    if (dialog.open) closeHistory();
    const review = get("store-aeo-review");
    review.hidden = false; review.open = true;
    review.setAttribute("aria-busy", "true");
    get("store-aeo-review-title").textContent = task.title;
    get("store-aeo-review-status").textContent = "Đang tải nội dung AEO…";
    get("store-aeo-preview").srcdoc = "";
    get("store-aeo-evidence").textContent = "";
    get("store-aeo-draft").textContent = "";
    review.scrollIntoView({block: "start", behavior: "smooth"});
    setBusy(button, true, "Đang mở AEO…");
    try {
      const detail = await api(`/api/aeo-backfill/tasks/${encodeURIComponent(task.id)}`);
      if (ticket !== reviewTicket) return;
      get("store-aeo-review-title").textContent = detail.title;
      get("store-aeo-review-status").textContent = `${statuses[detail.status] || detail.status} · ${detail.reviewed ? "Đã qua lượt đọc lại toàn bài" : "Chưa hoàn tất review"}${detail.error ? ` · ${detail.error}` : ""}`;
      get("store-aeo-preview").srcdoc = '<!doctype html><html lang="en"><meta charset="utf-8"><style>body{font:16px/1.65 system-ui;color:#24241f;margin:24px}h2{font-size:22px}h3{font-size:17px}</style><body>' + (detail.html || '<p>Chưa có draft AEO hợp lệ.</p>') + '</body></html>';
      get("store-aeo-evidence").textContent = JSON.stringify(detail.evidence, null, 2);
      get("store-aeo-draft").textContent = JSON.stringify(detail.draft, null, 2);
      get("store-aeo-review-title").focus({preventScroll: true});
    } catch (error) {
      if (ticket === reviewTicket) get("store-aeo-review-status").textContent = `Không thể mở AEO: ${error.message}`;
    } finally {
      setBusy(button, false, label);
      if (ticket === reviewTicket) review.setAttribute("aria-busy", "false");
    }
  }

  function caption(summary, run) {
    summary.replaceChildren(
      text("span", new Date(run.created_at).toLocaleString("vi-VN")),
      text("span", statuses[run.status] || run.status, "store-aeo-run-state"),
      text("strong", `${run.success}/${run.target} thành công`),
    );
    if (run.errors) summary.append(text("span", `${run.errors} sản phẩm lỗi`, "store-aeo-run-errors"));
  }
  async function mutateRun(button, url, card, modal) {
    const label = button.textContent;
    setBusy(button, true);
    try {
      await api(url, {method: "POST", body: "{}"});
      await refresh();
      if (modal && card.isConnected) {
        const {run} = await api(`/api/aeo-backfill/${encodeURIComponent(card.dataset.runId)}`);
        caption(card.querySelector("summary"), run);
        fillRunBody(card.querySelector(".store-aeo-run-body"), run, card, modal);
      }
    } catch (error) { notify(error.message, true); }
    finally { setBusy(button, false, label); }
  }
  function fillRunBody(body, run, card, modal) {
    body.replaceChildren(text("p", `Đã quét ${run.scanned} · Bỏ qua ${run.skipped} · Lỗi ${run.errors}`, "muted"));
    if (run.error) body.append(text("p", run.error, "error-text"));
    if (["running", "queued", "paused", "interrupted", "failed"].includes(run.status)) {
      const pause = ["running", "queued"].includes(run.status);
      const button = text("button", pause ? "Tạm dừng AEO" : "Tiếp tục AEO", "button secondary compact");
      button.type = "button";
      button.addEventListener("click", () => mutateRun(button, `/api/aeo-backfill/${run.id}/${pause ? "pause" : "resume"}`, card, modal));
      body.append(button);
    }
    const tasks = (run.tasks || []).filter((task) => task.status !== "skipped");
    const list = document.createElement("ol");
    for (const task of tasks) {
      const item = document.createElement("li");
      const button = text("button", `${task.title} · ${statuses[task.status] || task.status}`, "text-button");
      button.type = "button";
      button.addEventListener("click", () => reviewTask(task, button));
      item.append(button);
      if (task.error) item.append(text("p", task.error, "error-text"));
      if (task.status === "error" && ["paused", "interrupted", "failed", "exhausted"].includes(run.status)) {
        const retry = text("button", "Thử lại AEO sản phẩm này", "button secondary compact");
        retry.type = "button";
        retry.addEventListener("click", () => mutateRun(retry, `/api/aeo-backfill/tasks/${task.id}/retry`, card, modal));
        item.append(retry);
      }
      list.append(item);
    }
    body.append(tasks.length ? list : text("p", "Chưa có sản phẩm cần xem chi tiết.", "muted"));
  }
  function runCard(run, modal = false) {
    const card = document.createElement("details"), summary = document.createElement("summary");
    const body = document.createElement("div"), key = `${modal ? "history" : "recent"}:${run.id}`;
    card.className = "store-aeo-run"; card.dataset.runId = run.id;
    body.className = "store-aeo-run-body";
    caption(summary, run); card.append(summary, body);
    let loaded = Array.isArray(run.tasks), loading = false;
    if (loaded) fillRunBody(body, run, card, modal);
    async function loadDetails() {
      if (loaded || loading) return;
      loading = true; body.setAttribute("aria-busy", "true");
      body.replaceChildren(text("p", "Đang tải chi tiết lượt chạy…", "muted"));
      try {
        const data = await api(`/api/aeo-backfill/${encodeURIComponent(run.id)}`);
        caption(summary, data.run); fillRunBody(body, data.run, card, modal); loaded = true;
      } catch (error) {
        const retry = text("button", "Thử tải lại chi tiết", "button secondary compact");
        retry.type = "button"; retry.addEventListener("click", loadDetails);
        body.replaceChildren(text("p", error.message, "error-text"), retry);
      } finally { loading = false; body.setAttribute("aria-busy", "false"); }
    }
    card.addEventListener("toggle", () => { expanded.set(key, card.open); if (card.open) loadDetails(); });
    card.open = expanded.has(key) ? expanded.get(key) : ["running", "queued"].includes(run.status);
    return card;
  }

  async function loadSnapshot() {
    const {runs} = await api("/api/aeo-backfill");
    const active = runs.find((run) => !["completed", "exhausted", "failed"].includes(run.status));
    get("store-aeo-start").disabled = busy || Boolean(active);
    get("store-aeo-quantity").disabled = Boolean(active);
    if (active) get("store-aeo-quantity").value = active.target;
    const latest = runs[0], recent = runs.slice(0, 5);
    get("store-aeo-status").textContent = latest ? `${statuses[latest.status]} · Thành công ${latest.success}/${latest.target} · Đã quét ${latest.scanned} · Bỏ qua ${latest.skipped} · Lỗi ${latest.errors}${latest.status === "exhausted" ? ` · Còn thiếu ${Math.max(0, latest.target-latest.success)} sản phẩm` : ""}${latest.error ? ` · ${latest.error}` : ""}` : "Chưa có job AEO.";
    get("store-aeo-history-summary").textContent = `Hiển thị ${recent.length} lượt chạy mới nhất. Bấm từng lượt để xem sản phẩm.`;
    const next = JSON.stringify(recent.map((run) => ({id:run.id, status:run.status, success:run.success, target:run.target, error:run.error, scanned:run.scanned, skipped:run.skipped, errors:run.errors, tasks:run.tasks.map(task => ({id:task.id,title:task.title,status:task.status,error:task.error}))})));
    if (next !== signature) {
      // Preserve native disclosure state when progress polling updates the cards.
      get("store-aeo-runs").querySelectorAll(".store-aeo-run").forEach(card => expanded.set(`recent:${card.dataset.runId}`, card.open));
      get("store-aeo-runs").replaceChildren(...recent.map(run => runCard(run)));
      signature = next;
    }
    return recent;
  }
  function refresh() {
    if (!refreshPromise) refreshPromise = loadSnapshot().finally(() => { refreshPromise = null; });
    return refreshPromise;
  }
  async function manualRefresh() {
    const button = get("store-aeo-reload"), feedback = get("store-aeo-refresh-feedback");
    setBusy(button, true, "Đang tải tiến trình…");
    feedback.textContent = "Đang cập nhật tiến trình AEO…"; feedback.className = "help";
    try {
      await refresh();
      feedback.textContent = `Đã cập nhật tiến trình lúc ${new Date().toLocaleTimeString("vi-VN")}.`;
    } catch (error) {
      feedback.textContent = `Không thể tải lại: ${error.message}`; feedback.className = "error-text";
    } finally { setBusy(button, false, "Tải lại tiến trình AEO"); }
  }

  async function loadHistory() {
    if (historyLoading) return;
    const generation = historyGeneration, button = get("store-aeo-history-more");
    historyLoading = true; setBusy(button, true, "Đang tải lịch sử…"); button.hidden = false;
    get("store-aeo-history-status").textContent = "Đang tải lịch sử AEO…";
    try {
      const query = historyCursor ? `?before=${encodeURIComponent(historyCursor)}` : "";
      const page = await api(`/api/aeo-backfill/history${query}`);
      if (generation !== historyGeneration) return;
      get("store-aeo-history-list").append(...page.runs.map(run => runCard(run, true)));
      historyCount += page.runs.length; historyCursor = page.next_cursor;
      get("store-aeo-history-status").textContent = `Đang hiển thị ${historyCount}/${page.total} lượt chạy.`;
      if (!historyCount) get("store-aeo-history-list").append(text("p", "Chưa có lịch sử chạy AEO.", "muted"));
      button.hidden = !page.has_more;
    } catch (error) {
      if (generation !== historyGeneration) return;
      get("store-aeo-history-status").textContent = `Không thể tải lịch sử: ${error.message}`;
    } finally {
      if (generation === historyGeneration) { historyLoading = false; setBusy(button, false, "Xem thêm lịch sử"); }
    }
  }
  get("store-aeo-open-history").addEventListener("click", () => {
    if (dialog.open) return;
    historyGeneration++; historyLoading = false; historyCursor = null; historyCount = 0;
    get("store-aeo-history-list").replaceChildren(); dialog.showModal();
    document.body.classList.add("store-aeo-history-open"); loadHistory();
  });
  function releaseHistory() {
    // A delayed close event from an earlier opening must not unlock a new dialog.
    if (dialog.open || !document.body.classList.contains("store-aeo-history-open")) return;
    historyGeneration++; historyLoading = false;
    document.body.classList.remove("store-aeo-history-open");
  }
  function closeHistory() { dialog.close(); releaseHistory(); }
  get("store-aeo-close-history").addEventListener("click", closeHistory);
  dialog.addEventListener("keydown", (event) => {
    if (event.key === "Escape") { event.preventDefault(); closeHistory(); }
  });
  dialog.addEventListener("cancel", (event) => { event.preventDefault(); closeHistory(); });
  dialog.addEventListener("close", releaseHistory);
  dialog.addEventListener("click", (event) => {
    const box = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom)) closeHistory();
  });
  get("store-aeo-history-more").addEventListener("click", loadHistory);
  get("store-aeo-reload").addEventListener("click", manualRefresh);
  get("store-aeo-form").addEventListener("submit", async (event) => {
    event.preventDefault(); if (busy) return;
    busy = true; get("store-aeo-start").disabled = true;
    try {
      if (!state.csrf) throw new Error("Dashboard đang khởi tạo. Hãy thử lại sau giây lát.");
      await api("/api/aeo-backfill", {method:"POST",body:JSON.stringify({quantity:Number(get("store-aeo-quantity").value)})});
      notify("Đã tạo job AEO. Tool xử lý từ sản phẩm mới đến cũ.");
    } catch (error) { notify(error.message, true); }
    finally { busy = false; refresh().catch(reportRefreshError); }
  });
  refresh().catch(reportRefreshError);
  window.setInterval(() => refresh().catch(reportRefreshError), 4000);
})();
