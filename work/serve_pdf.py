#!/usr/bin/env python3
"""Petit serveur de téléchargement du manuel PEB (aucune dépendance externe)."""
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = "/home/user/scaling-guacamole"
PDF = os.path.join(ROOT, "Manuel_PEB_Bruxelles_Etude_Intensive.pdf")
NAME = os.path.basename(PDF)
PORT = int(os.environ.get("PDF_PORT", "8123"))

HTML = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Manuel PEB — téléchargement</title>
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body { margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
         background:#eef4f8; font-family: system-ui, -apple-system, "Segoe UI", DejaVu Sans, sans-serif;
         color:#1e2830; padding:24px; }
  .card { width:min(680px,100%); background:#fff; border-radius:16px; padding:36px 38px;
          box-shadow:0 14px 40px rgba(18,48,74,.14); border-top:6px solid #12304a; }
  .tag { font-size:12px; letter-spacing:.14em; text-transform:uppercase; color:#1b5e8c; font-weight:700; }
  h1 { font-size:27px; line-height:1.2; margin:12px 0 8px; color:#12304a; }
  p { line-height:1.6; margin:10px 0; }
  .meta { font-size:13px; color:#5a6672; margin:16px 0 26px; }
  .btns { display:flex; flex-wrap:wrap; gap:12px; }
  a.btn { display:inline-block; text-decoration:none; padding:14px 22px; border-radius:9px;
          font-weight:700; font-size:15px; background:#12304a; color:#fff; }
  a.btn:hover { background:#1b5e8c; }
  a.btn.ghost { background:#fff; color:#12304a; border:2px solid #12304a; }
  a.btn.ghost:hover { background:#eef4f8; }
  .hint { margin-top:26px; padding-top:18px; border-top:1px solid #dfe7ee; font-size:13px; color:#5a6672; }
  code { background:#f2f6f9; padding:2px 6px; border-radius:4px; font-size:12px; word-break:break-all; }
</style>
</head>
<body>
<div class="card">
  <div class="tag">Préparation à l'examen · Bruxelles</div>
  <h1>Manuel d'étude intensif<br>Certificateur PEB résidentiel</h1>
  <p>Synthèse des trois livres du Protocole de certification PEB (version 2.7 – novembre 2024),
     avec 184 questions de rappel et leurs corrigés, deux examens blancs et la table de rappel anti-oubli.</p>
  <div class="meta" id="meta">Chargement des informations…</div>
  <div class="btns">
    <a class="btn" href="/Manuel_PEB_Bruxelles_Etude_Intensive.pdf?dl=1"
       download="Manuel_PEB_Bruxelles_Etude_Intensive.pdf">⬇ Télécharger le PDF</a>
    <a class="btn ghost" href="/Manuel_PEB_Bruxelles_Etude_Intensive.pdf" target="_blank" rel="noopener">Ouvrir le PDF ↗</a>
  </div>
  <div class="hint">
    Si le bouton ne réagit pas dans l'aperçu, ouvrez cette page dans un nouvel onglet, ou copiez ce lien :<br>
    <code id="direct"></code>
  </div>
</div>
<script>
  const base = location.origin;
  document.getElementById('direct').textContent = base + '/Manuel_PEB_Bruxelles_Etude_Intensive.pdf?dl=1';
  fetch('/meta').then(r => r.json()).then(m => {
    document.getElementById('meta').textContent =
      'PDF · ' + m.pages + ' pages · ' + m.size_kb + ' Ko · ' + m.name;
  }).catch(() => { document.getElementById('meta').textContent = 'Fichier PDF prêt à télécharger.'; });
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "PEBManual/1.0"

    def _send(self, code, body, ctype, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        for key, value in (extra or []):
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        u = urlparse(self.path)
        path, query = u.path, parse_qs(u.query)
        if path in ("/", "/index.html"):
            self._send(200, HTML.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/meta":
            import json
            data = {"name": NAME, "size_kb": round(os.path.getsize(PDF) / 1024),
                    "pages": 79}
            self._send(200, json.dumps(data).encode("utf-8"), "application/json; charset=utf-8")
        elif path in ("/" + NAME, "/download", "/pdf"):
            with open(PDF, "rb") as fh:
                payload = fh.read()
            force = path != ("/" + NAME) or query.get("dl") == ["1"]
            disp = "attachment" if force else "inline"
            self._send(200, payload, "application/pdf",
                       [("Content-Disposition", '%s; filename="%s"' % (disp, NAME))])
        else:
            self._send(404, b"Introuvable", "text/plain; charset=utf-8")

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    print("Serveur PDF sur 0.0.0.0:%d -> %s" % (PORT, PDF), flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
