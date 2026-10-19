/* AEO-only Dashboard controls; the existing batch handlers stay independent. */
(() => {
  const root = document.querySelector("#store-aeo-panel");
  if (!root) return;
  const get = (id) => document.getElementById(id);
  let busy = false;
  let refreshing = false;
  let signature = "";
  const statuses = {queued: "Chờ chạy", running: "Đang xử lý", paused: "Đã tạm dừng", interrupted: "Gián đoạn", completed: "Hoàn tất", exhausted: "Đã hết catalog", failed: "Job lỗi", written: "Đã ghi và xác minh", skipped: "Đã có AEO · bỏ qua", error: "Cần chú ý", not_needed: "Dừng vì đã đủ số lượng", pending: "Chờ xử lý", authoring: "Đang viết AEO", reviewing: "Đang đọc lại toàn bài", ready: "Đã kiểm định và review"};

  async function reviewTask(task) {
    try {
      const detail = await api(`/api/aeo-backfill/tasks/${encodeURIComponent(task.id)}`);
      get("store-aeo-review").hidden = false;
      get("store-aeo-review").open = true;
      get("store-aeo-review-title").textContent = detail.title;
      get("store-aeo-review-status").textContent = `${statuses[detail.status] || detail.status} · ${detail.reviewed ? "Đã qua lượt đọc lại toàn bài" : "Chưa hoàn tất review"}${detail.error ? ` · ${detail.error}` : ""}`;
      get("store-aeo-preview").srcdoc = '<!doctype html><html lang="en"><meta charset="utf-8"><style>body{font:16px/1.65 system-ui;color:#24241f;margin:24px}h2{font-size:22px}h3{font-size:17px}</style><body>' + (detail.html || '<p>Chưa có draft AEO hợp lệ.</p>') + '</body></html>';
      get("store-aeo-evidence").textContent = JSON.stringify(detail.evidence, null, 2);
      get("store-aeo-draft").textContent = JSON.stringify(detail.draft, null, 2);
    } catch (error) { notify(error.message, true); }
  }

  async function refresh() {
    if (refreshing) return;
    refreshing = true;
    try {
      const {runs} = await api("/api/aeo-backfill");
      const active = runs.find((r) => !["completed", "exhausted", "failed"].includes(r.status));
      get("store-aeo-start").disabled = busy || Boolean(active);
      get("store-aeo-quantity").disabled = Boolean(active);
      if (active) get("store-aeo-quantity").value = active.target;
      const latest = runs[0];
      get("store-aeo-status").textContent = latest ? `${statuses[latest.status]} · Thành công ${latest.success}/${latest.target} · Đã quét ${latest.scanned} · Bỏ qua ${latest.skipped} · Lỗi ${latest.errors}${latest.status === "exhausted" ? ` · Còn thiếu ${Math.max(0, latest.target-latest.success)} sản phẩm` : ""}${latest.error ? ` · ${latest.error}` : ""}` : "Chưa có job AEO.";
      const nextSignature = JSON.stringify(runs.map((run) => ({
        id: run.id, status: run.status, success: run.success, target: run.target, error: run.error,
        tasks: run.tasks.map((task) => ({id: task.id, title: task.title, status: task.status, error: task.error})),
      })));
      if (nextSignature === signature) return;
      signature = nextSignature;
      const container = get("store-aeo-runs");
      container.replaceChildren();
      for (const run of runs.slice(0, 5)) {
        const card = document.createElement("article");
        card.className = "store-aeo-run";
        const heading = document.createElement("p");
        heading.textContent = `${new Date(run.created_at).toLocaleString("vi-VN")} · ${statuses[run.status]} · ${run.success}/${run.target}`;
        card.append(heading);
        if (["running", "queued", "paused", "interrupted", "failed"].includes(run.status)) {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "button secondary compact";
          const pause = ["running", "queued"].includes(run.status);
          button.textContent = pause ? "Tạm dừng AEO" : "Tiếp tục AEO";
          button.addEventListener("click", async () => {
            button.disabled = true;
            try { await api(`/api/aeo-backfill/${run.id}/${pause ? "pause" : "resume"}`, {method: "POST", body: "{}"}); await refresh(); }
            catch (error) { notify(error.message, true); button.disabled = false; }
          });
          card.append(button);
        }
        const list = document.createElement("ol");
        for (const task of run.tasks.filter((t) => t.status !== "skipped").slice(-50)) {
          const item = document.createElement("li");
          const button = document.createElement("button");
          button.type = "button"; button.className = "text-button";
          button.textContent = `${task.title} · ${statuses[task.status] || task.status}`;
          button.addEventListener("click", () => reviewTask(task));
          item.append(button);
          if (task.error) { const error = document.createElement("p"); error.className = "error-text"; error.textContent = task.error; item.append(error); }
          if (task.status === "error" && ["paused", "interrupted", "failed", "exhausted"].includes(run.status)) {
            const retry = document.createElement("button");
            retry.type = "button"; retry.className = "button secondary compact"; retry.textContent = "Thử lại AEO sản phẩm này";
            retry.addEventListener("click", async () => {
              retry.disabled = true;
              try { await api(`/api/aeo-backfill/tasks/${task.id}/retry`, {method: "POST", body: "{}"}); await refresh(); }
              catch (error) { notify(error.message, true); retry.disabled = false; }
            });
            item.append(retry);
          }
          list.append(item);
        }
        card.append(list); container.append(card);
      }
    } catch (error) { get("store-aeo-status").textContent = `Không thể tải AEO: ${error.message}`; }
    finally { refreshing = false; }
  }
  get("store-aeo-form").addEventListener("submit", async (event) => {
    event.preventDefault(); if (busy) return;
    busy = true; get("store-aeo-start").disabled = true;
    try {
      if (!state.csrf) throw new Error("Dashboard đang khởi tạo. Hãy thử lại sau giây lát.");
      await api("/api/aeo-backfill", {method: "POST", body: JSON.stringify({quantity: Number(get("store-aeo-quantity").value)})});
      notify("Đã tạo job AEO. Tool xử lý từ sản phẩm mới đến cũ.");
    } catch (error) { notify(error.message, true); }
    finally { busy = false; await refresh(); }
  });
  get("store-aeo-reload").addEventListener("click", refresh);
  refresh(); window.setInterval(refresh, 4000);
})();
