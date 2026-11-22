import json
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from crawler import crawl_fast_stream, list_cached_threads

HTML_UI = r"""
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>fallenpito</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, sans-serif; }
    body { background: #0d0d0d; color: #f5f5f5; padding: 12px; padding-bottom: 60px; }
    .box { background: #181818; padding: 12px; border-radius: 12px; border: 1px solid #2b2b2b; margin-bottom: 10px; }
    .row { display: flex; gap: 6px; margin-bottom: 8px; }
    input {
      background: #242424; border: 1px solid #3a3a3a; color: #fff;
      padding: 9px 10px; border-radius: 8px; font-size: 13px; outline: none; width: 100%;
    }
    .btn {
      border: none; padding: 9px 12px; border-radius: 8px; font-weight: 600;
      font-size: 13px; color: #fff; white-space: nowrap; cursor: pointer;
    }
    .btn-red { background: #e50914; }
    .btn-dark { background: #333; }
    .progress-wrap { margin-top: 6px; display: none; }
    .progress-bar-bg { width: 100%; height: 6px; background: #2a2a2a; border-radius: 4px; overflow: hidden; margin-top: 5px; }
    .progress-bar-fill { height: 100%; width: 0%; background: #e50914; transition: width 0.15s; }
    .status-text { font-size: 12px; color: #bbb; display: flex; justify-content: space-between; }

    /* Danh sách Đã xử lý gần đây kiểu hayho.org */
    .history-section { display: block; }
    .history-header { font-size: 13px; font-weight: 600; color: #ddd; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
    .history-card {
      background: #171717; border: 1px solid #282828; border-radius: 10px;
      padding: 11px 12px; margin-bottom: 8px; cursor: pointer;
    }
    .history-card:active { background: #222; }
    .history-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; font-size: 11px; }
    .history-status { color: #22c55e; font-weight: 600; }
    .history-time { color: #888; }
    .history-title { font-size: 13px; font-weight: 600; color: #f5f5f5; line-height: 1.4; margin-bottom: 5px; }
    .history-meta { font-size: 12px; color: #999; }

    /* Khu vực xem chi tiết (ẩn mặc định, bấm vào thẻ mới hiện) */
    .viewer-section { display: none; }
    .viewer-topbar {
      display: flex; align-items: center; gap: 8px; margin-bottom: 10px;
      background: #181818; padding: 9px 10px; border-radius: 10px; border: 1px solid #2b2b2b;
    }
    .back-btn {
      background: #282828; border: 1px solid #3a3a3a; color: #fff;
      padding: 6px 10px; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer; white-space: nowrap;
    }
    .viewer-title {
      font-size: 13px; font-weight: 600; color: #eee;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }

    .tabs { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 10px; }
    .tab-btn {
      background: #1a1a1a; border: 1px solid #2e2e2e; color: #aaa; padding: 9px 4px;
      border-radius: 8px; font-size: 12px; font-weight: 600; text-align: center; cursor: pointer;
    }
    .tab-btn.active { background: #e50914; border-color: #e50914; color: #fff; }
    .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; align-items: start; }
    .card { background: #171717; border-radius: 10px; overflow: hidden; border: 1px solid #262626; }
    .thumb-box { position: relative; width: 100%; background: #000; }
    .thumb { width: 100%; height: auto; object-fit: contain; display: block; }
    .page-badge {
      position: absolute; bottom: 6px; left: 6px; background: rgba(229,9,20,0.9);
      color: #fff; font-size: 10px; font-weight: 600; padding: 2px 5px; border-radius: 4px;
    }
    .info { padding: 7px 8px; font-size: 11px; color: #aaa; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .list-item {
      background: #171717; border: 1px solid #282828; border-radius: 10px;
      padding: 10px 12px; margin-bottom: 8px; font-size: 13px; line-height: 1.4;
    }
    .list-head { display: flex; justify-content: space-between; font-size: 11px; color: #e50914; font-weight: 600; margin-bottom: 4px; }
    .link-url { color: #3b82f6; text-decoration: none; word-break: break-all; font-size: 12px; display: block; margin-top: 4px; }
    .load-more {
      width: 100%; padding: 12px; background: #222; color: #fff; border: 1px solid #333;
      border-radius: 8px; margin-top: 12px; font-weight: 600; font-size: 13px;
    }
    .modal {
      display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.96);
      z-index: 100; flex-direction: column; justify-content: center; align-items: center;
      padding: 14px; touch-action: pan-y; user-select: none;
    }
    .modal.open { display: flex; }
    .modal-media { max-width: 100%; max-height: 80vh; border-radius: 8px; object-fit: contain; }
    .modal-counter {
      position: fixed; top: 18px; left: 18px; background: rgba(40,40,40,0.85);
      color: #fff; padding: 5px 12px; border-radius: 20px; font-size: 12px;
    }
    .close-btn {
      position: fixed; top: 14px; right: 18px; background: #333; color: #fff;
      width: 36px; height: 36px; border-radius: 50%; border: none; font-size: 20px; z-index: 102;
    }
    .nav-btn {
      position: fixed; top: 50%; transform: translateY(-50%);
      background: rgba(255,255,255,0.15); color: #fff; border: none;
      width: 38px; height: 54px; border-radius: 8px; font-size: 20px; z-index: 101;
    }
    .nav-prev { left: 8px; }
    .nav-next { right: 8px; }
  </style>
</head>
<body>

  <div class="box">
    <div class="row">
      <input type="url" id="threadUrl" placeholder="Dán link thớt xamvn...">
      <input type="number" id="maxPages" value="30" min="1" max="200" style="max-width:58px;text-align:center;">
      <button class="btn btn-red" onclick="startCrawl(false)">Quét</button>
      <button class="btn btn-dark" onclick="startCrawl(true)" title="Bỏ qua cache, cào lại từ đầu">↻</button>
    </div>
    <div class="row">
      <input type="text" id="cookieInput" placeholder="Cookie đăng nhập (tự lưu)" onchange="saveCookie()">
    </div>
    <div class="row" style="margin-bottom:0;">
      <input type="text" id="searchInput" placeholder="Lọc cực nhanh theo tên, tác giả, trang..." oninput="resetRender()">
    </div>

    <div class="progress-wrap" id="progressWrap">
      <div class="status-text">
        <span id="progressLabel">Đang chuẩn bị...</span>
        <span id="progressPercent">0%</span>
      </div>
      <div class="progress-bar-bg"><div class="progress-bar-fill" id="progressFill"></div></div>
    </div>
  </div>

  <!-- Danh sách link đã lọc (hiện sẵn lúc mới mở web) -->
  <div class="box history-section" id="historySection">
    <div class="history-header">
      <span>🕒 Đã xử lý gần đây</span>
      <span id="historyCount" style="color:#888;font-weight:400;"></span>
    </div>
    <div id="historyList"></div>
  </div>

  <!-- Khu vực xem nội dung (chỉ mở khi bấm vào 1 thẻ lịch sử hoặc bấm Quét) -->
  <div class="viewer-section" id="viewerSection">
    <div class="viewer-topbar">
      <button class="back-btn" onclick="backToHistory()">← Danh sách</button>
      <div class="viewer-title" id="viewerTitle">Đang tải...</div>
    </div>

    <div class="tabs">
      <div class="tab-btn active" id="tab-image" onclick="switchTab('image')">Ảnh (0)</div>
      <div class="tab-btn" id="tab-video" onclick="switchTab('video')">Video (0)</div>
      <div class="tab-btn" id="tab-comment" onclick="switchTab('comment')">Bình luận (0)</div>
      <div class="tab-btn" id="tab-link" onclick="switchTab('link')">Link (0)</div>
    </div>

    <div id="contentArea"></div>
  </div>

  <div class="modal" id="modal" onclick="closeModal(event)">
    <span class="modal-counter" id="modalCounter">1 / 1</span>
    <button class="close-btn" onclick="closeModal(event, true)">&times;</button>
    <button class="nav-btn nav-prev" onclick="stepMedia(-1); event.stopPropagation();">&#10094;</button>
    <div id="modalBody" style="display:flex;flex-direction:column;align-items:center;"></div>
    <button class="nav-btn nav-next" onclick="stepMedia(1); event.stopPropagation();">&#10095;</button>
  </div>

  <script>
    let store = { image: [], video: [], comment: [], link: [] };
    let currentTab = 'image';
    let renderLimit = 40;
    let abortCtrl = null;
    let currentIdx = 0;
    window.allFilteredMedia = [];

    document.getElementById('cookieInput').value = localStorage.getItem('xam_cookie') || '';
    function saveCookie() { localStorage.setItem('xam_cookie', document.getElementById('cookieInput').value.trim()); }

    function formatTimeAgo(ts) {
      if (!ts) return '';
      const diff = Math.max(1, Math.floor(Date.now() / 1000 - ts));
      if (diff < 60) return diff + ' giây trước';
      if (diff < 3600) return Math.floor(diff / 60) + ' phút trước';
      if (diff < 86400) return Math.floor(diff / 3600) + ' giờ trước';
      return Math.floor(diff / 86400) + ' ngày trước';
    }

    async function loadHistory() {
      try {
        const res = await fetch('/history');
        const list = await res.json();
        const container = document.getElementById('historyList');
        const countEl = document.getElementById('historyCount');
        container.innerHTML = '';

        if (!list || !list.length) {
          countEl.textContent = '0 mục';
          container.innerHTML = '<div style="text-align:center;color:#777;font-size:12px;padding:14px 0;">Chưa có link nào được lọc. Dán link phía trên để bắt đầu.</div>';
          return;
        }

        countEl.textContent = list.length + ' mục';
        list.forEach(item => {
          const card = document.createElement('div');
          card.className = 'history-card';

          const top = document.createElement('div');
          top.className = 'history-top';
          top.innerHTML = `<span class="history-status">Hoàn thành</span><span class="history-time">${formatTimeAgo(item.mtime)}</span>`;

          const title = document.createElement('div');
          title.className = 'history-title';
          title.textContent = item.title;

          const meta = document.createElement('div');
          meta.className = 'history-meta';
          meta.textContent = `${item.img_count} ảnh - ${item.vid_count} video - ${item.cmt_count} bình luận - ${item.lnk_count} link`;

          card.appendChild(top);
          card.appendChild(title);
          card.appendChild(meta);
          card.onclick = () => openHistoryItem(item);
          container.appendChild(card);
        });
      } catch (e) {}
    }

    function openHistoryItem(item) {
      document.getElementById('threadUrl').value = item.url;
      document.getElementById('viewerTitle').textContent = item.title;
      startCrawl(false);
    }

    function backToHistory() {
      if (abortCtrl) abortCtrl.abort();
      document.getElementById('viewerSection').style.display = 'none';
      document.getElementById('progressWrap').style.display = 'none';
      document.getElementById('historySection').style.display = 'block';
      loadHistory();
    }

    loadHistory();

    function switchTab(tab) {
      currentTab = tab;
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
      document.getElementById('tab-' + tab).classList.add('active');
      resetRender();
    }

    function resetRender() {
      renderLimit = 40;
      renderTab();
    }

    function updateCounters() {
      document.getElementById('tab-image').textContent = `Ảnh (${store.image.length})`;
      document.getElementById('tab-video').textContent = `Video (${store.video.length})`;
      document.getElementById('tab-comment').textContent = `Bình luận (${store.comment.length})`;
      document.getElementById('tab-link').textContent = `Link (${store.link.length})`;
    }

    async function startCrawl(forceRefresh) {
      const url = document.getElementById('threadUrl').value.trim();
      const cookie = document.getElementById('cookieInput').value.trim();
      const maxPages = parseInt(document.getElementById('maxPages').value) || 30;
      if (!url) return alert('Chưa dán link!');

      if (abortCtrl) abortCtrl.abort();
      abortCtrl = new AbortController();

      document.getElementById('historySection').style.display = 'none';
      document.getElementById('viewerSection').style.display = 'block';
      if (!document.getElementById('viewerTitle').textContent || document.getElementById('viewerTitle').textContent === 'Đang tải...') {
        document.getElementById('viewerTitle').textContent = url;
      }

      store = { image: [], video: [], comment: [], link: [] };
      updateCounters();
      resetRender();

      const pWrap = document.getElementById('progressWrap');
      const pLabel = document.getElementById('progressLabel');
      const pPercent = document.getElementById('progressPercent');
      const pFill = document.getElementById('progressFill');
      pWrap.style.display = 'block';
      pLabel.textContent = 'Đang kiểm tra cache & kết nối 8 luồng...';
      pPercent.textContent = '0%';
      pFill.style.width = '0%';

      try {
        const res = await fetch('/crawl', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url, cookie, max_pages: maxPages, force: forceRefresh }),
          signal: abortCtrl.signal
        });

        const reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\\\\n');

          for (const line of lines) {
            if (!line.trim()) continue;
            const msg = JSON.parse(line);

            if (msg.error) { pLabel.textContent = 'Lỗi: ' + msg.error; return; }

            if (msg.cached) {
              store.image = msg.data.images || [];
              store.video = msg.data.videos || [];
              store.comment = msg.data.comments || [];
              store.link = msg.data.links || [];
              if (msg.data.title) document.getElementById('viewerTitle').textContent = msg.data.title;
              updateCounters();
              resetRender();
              pLabel.textContent = 'Nạp tức thì từ Cache (bấm ↻ nếu muốn cào mới)';
              pPercent.textContent = '100%';
              pFill.style.width = '100%';
              return;
            }

            if (msg.progress) {
              const pct = Math.min(100, Math.round((msg.done_pages / msg.total) * 100));
              pLabel.textContent = `Đa luồng: xong ${msg.done_pages}/${msg.total} trang`;
              pPercent.textContent = pct + '%';
              pFill.style.width = pct + '%';
            }

            if (msg.images) store.image.push(...msg.images);
            if (msg.videos) store.video.push(...msg.videos);
            if (msg.comments) store.comment.push(...msg.comments);
            if (msg.links) store.link.push(...msg.links);

            updateCounters();
            renderTab();

            if (msg.done) {
              pLabel.textContent = `Hoàn tất ${msg.total_crawled} trang (Đã lưu Cache)`;
              pPercent.textContent = '100%';
              pFill.style.width = '100%';
            }
          }
        }
      } catch (e) {
        if (e.name !== 'AbortError') pLabel.textContent = 'Ngắt kết nối.';
      }
    }

    function renderTab() {
      const q = document.getElementById('searchInput').value.toLowerCase().trim();
      const area = document.getElementById('contentArea');

      let filtered = [];
      if (currentTab === 'image' || currentTab === 'video') {
        filtered = store[currentTab].filter(i => !q || i.name.toLowerCase().includes(q) || ('p.' + i.page).includes(q));
        window.allFilteredMedia = filtered;
      } else if (currentTab === 'comment') {
        filtered = store.comment.filter(c => !q || c.text.toLowerCase().includes(q) || c.author.toLowerCase().includes(q));
      } else {
        filtered = store.link.filter(l => !q || l.url.toLowerCase().includes(q) || l.author.toLowerCase().includes(q));
      }

      const visible = filtered.slice(0, renderLimit);

      let html = '';
      if (currentTab === 'image' || currentTab === 'video') {
        html = `<div class="grid">` + visible.map((i, idx) => `
          <div class="card" onclick="openModal(${idx})">
            <div class="thumb-box">
              <span class="page-badge">P.${i.page}</span>
              ${currentTab === 'video'
                ? `<video class="thumb" src="${i.url}#t=0.5" preload="metadata" muted playsinline></video>`
                : `<img class="thumb" src="${i.url}" loading="lazy" referrerpolicy="no-referrer">`
              }
            </div>
            <div class="info">${i.name}</div>
          </div>
        `).join('') + `</div>`;
      } else if (currentTab === 'comment') {
        html = visible.map(c => `
          <div class="list-item">
            <div class="list-head"><span>@${c.author}</span><span>Trang ${c.page}</span></div>
            <div>${c.text}</div>
          </div>
        `).join('');
      } else {
        html = visible.map(l => `
          <div class="list-item">
            <div class="list-head"><span>@${l.author}</span><span>Trang ${l.page}</span></div>
            <a class="link-url" href="${l.url}" target="_blank">${l.url}</a>
          </div>
        `).join('');
      }

      if (filtered.length > renderLimit) {
        html += `<button class="load-more" onclick="renderLimit += 40; renderTab()">Xem thêm (${filtered.length - renderLimit} mục còn lại)</button>`;
      }
      area.innerHTML = html;
    }

    function openModal(idx) {
      currentIdx = idx;
      renderModal();
      document.getElementById('modal').classList.add('open');
    }

    function renderModal() {
      const list = window.allFilteredMedia;
      if (!list || !list.length) return;
      const i = list[currentIdx];
      document.getElementById('modalCounter').textContent = `${currentIdx + 1} / ${list.length} (P.${i.page})`;
      document.getElementById('modalBody').innerHTML = `
        ${currentTab === 'video'
          ? `<video class="modal-media" src="${i.url}" controls autoplay playsinline></video>`
          : `<img class="modal-media" src="${i.url}" referrerpolicy="no-referrer">`
        }
        <a href="${i.url}" target="_blank" class="btn btn-red" style="margin-top:12px;text-decoration:none;">Tải gốc (Trang ${i.page})</a>
      `;
    }

    function stepMedia(dir) {
      const list = window.allFilteredMedia;
      if (!list || list.length <= 1) return;
      currentIdx = (currentIdx + dir + list.length) % list.length;
      renderModal();
    }

    let touchStartX = 0, touchStartY = 0;
    const modalEl = document.getElementById('modal');
    modalEl.addEventListener('touchstart', e => {
      touchStartX = e.changedTouches[0].screenX;
      touchStartY = e.changedTouches[0].screenY;
    }, { passive: true });

    modalEl.addEventListener('touchend', e => {
      const dx = e.changedTouches[0].screenX - touchStartX;
      const dy = e.changedTouches[0].screenY - touchStartY;
      if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) {
        if (dx < 0) stepMedia(1);
        else stepMedia(-1);
      }
    }, { passive: true });

    function closeModal(e, force) {
      if (force || e.target.id === 'modal') {
        document.getElementById('modal').classList.remove('open');
        document.getElementById('modalBody').innerHTML = '';
      }
    }
  </script>
</body>
</html>
"""

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/ping":
            try:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        if self.path == "/history":
            try:
                items = list_cached_threads()
                payload = json.dumps(items, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        t0 = time.time()
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_UI.encode("utf-8"))
            ms = round((time.time() - t0) * 1000, 1)
            now = time.strftime("%H:%M:%S")
            print(f"\n[{now}] 🌐 LOAD UI ({ms}ms)")
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        if self.path != "/crawl":
            self.send_response(404)
            self.end_headers()
            return

        t_start = time.time()
        now = time.strftime("%H:%M:%S")
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            url = payload.get("url", "").strip()
            cookie = payload.get("cookie", "").strip()
            max_pages = min(int(payload.get("max_pages", 30)), 200)
            force = bool(payload.get("force", False))

            print(f"\n[{now}] 🔍 CRAWL ({max_pages}p | Force={force}) -> {url}")

            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            for chunk in crawl_fast_stream(url, cookie, max_pages, force):
                if chunk.get("cached"):
                    ms = round((time.time() - t_start) * 1000, 1)
                    print(f"   └── ⚡ CACHE HIT: Nạp xong trong {ms}ms")
                elif chunk.get("progress"):
                    done_p = chunk.get("done_pages", 0)
                    tot_p = chunk.get("total", 0)
                    elapsed = round(time.time() - t_start, 2)
                    print(f"   └── ⏳ Đang quét: {done_p}/{tot_p} trang ({elapsed}s)...", end="\r", flush=True)
                elif chunk.get("done"):
                    total_sec = round(time.time() - t_start, 2)
                    print(f"\r   └── ✅ XONG: {chunk.get('total_crawled')} trang trong {total_sec}s!      ")
                elif chunk.get("error"):
                    print(f"\r   └── ❌ LỖI: {chunk.get('error')}                      ")

                self.wfile.write((json.dumps(chunk, ensure_ascii=False) + "\n").encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            print("\r   └── ⚠️ ABORT: Safari ngắt kết nối ngang chừng.          ")
        except Exception as e:
            print(f"\r   └── ❌ ERR: {e}")
            try:
                err = json.dumps({"error": str(e)}, ensure_ascii=False) + "\n"
                self.wfile.write(err.encode("utf-8"))
            except (BrokenPipeError, ConnectionResetError):
                pass

def heartbeat_ping():
    while True:
        time.sleep(15)
        t0 = time.time()
        try:
            urllib.request.urlopen("http://127.0.0.1:8000/ping", timeout=3).read()
            ping_ms = round((time.time() - t0) * 1000, 1)
            now = time.strftime("%H:%M:%S")
            print(f"\r[{now}] 💓 PING OK: {ping_ms}ms   ", end="", flush=True)
        except Exception as e:
            print(f"\n[PING FAIL] Mất kết nối: {e}")

if __name__ == "__main__":
    print("=" * 44)
    print("🚀 TURBO MEDIA SERVER: http://127.0.0.1:8000")
    print("=" * 44)
    threading.Thread(target=heartbeat_ping, daemon=True).start()
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
