"""Local mock of the JoinReal.com agent directory.

In production, Playwright navigates joinreal.com; here it navigates this
tiny Flask app. The HTML structure is intentionally simple but realistic
so Stagehand-style 'find the search field' / 'click the matching listing'
flows demonstrate the same pattern.
"""
from __future__ import annotations

from flask import Flask, request, abort

from verifier.fixtures import SAMPLE_AGENTS

app = Flask(__name__)


PAGE_HEAD = """
<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>JoinReal · Find an Agent</title>
<style>
  body { font-family: -apple-system, Segoe UI, Inter, Helvetica, Arial, sans-serif;
         background:#0F172A; color:#E2E8F0; margin:0; padding:40px 20px; }
  .wrap { max-width: 920px; margin:0 auto; }
  header { display:flex; align-items:center; gap:14px; margin-bottom:28px; }
  .logo { font-size:1.9rem; font-weight:900; letter-spacing:-0.04em; }
  .logo span { color:#22D3EE; }
  h1 { font-weight:800; letter-spacing:-0.02em; }
  .card { background:#1E293B; border:1px solid #334155; border-radius:12px; padding:18px 22px; }
  input[type=text] { width:100%; padding:14px 16px; border-radius:10px; border:1px solid #334155;
                     background:#0B1220; color:#E2E8F0; font-size:1rem; }
  button { margin-top:12px; padding:12px 22px; background:linear-gradient(90deg,#3B82F6,#6366F1);
           color:white; border:0; border-radius:10px; font-weight:600; cursor:pointer; }
  .listing { padding:14px 18px; margin-top:10px; border:1px solid #334155; border-radius:10px;
             background:#0F1E33; cursor:pointer; }
  .listing:hover { border-color:#6366F1; }
  .pill { display:inline-block; padding:3px 10px; border-radius:99px; font-size:0.78rem;
          background:rgba(99,102,241,0.18); color:#A5B4FC; border:1px solid rgba(99,102,241,0.4); }
  .muted { color:#94A3B8; font-size:0.88rem; }
</style></head><body><div class="wrap">
<header><div class="logo">join<span>real</span></div></header>
"""

PAGE_FOOT = "</div></body></html>"


@app.route("/")
@app.route("/directory")
def directory():
    return PAGE_HEAD + """
    <h1>Find an Agent</h1>
    <div class="card">
      <form method="get" action="/search">
        <label for="q" class="muted">Find Agent by Name</label>
        <input type="text" id="q" name="q" placeholder="e.g. Jordan Rivera" autofocus
               data-field="search-name">
        <button type="submit" data-field="search-submit">Search</button>
      </form>
    </div>
    """ + PAGE_FOOT


@app.route("/search")
def search():
    q = (request.args.get("q") or "").strip().lower()
    if not q:
        return PAGE_HEAD + "<h1>No query</h1>" + PAGE_FOOT

    matches = [
        a for a in SAMPLE_AGENTS
        if q in a["name"].lower()
        or any(tok and tok in a["name"].lower() for tok in q.split())
    ]
    items = ""
    if not matches:
        items = '<div class="card" data-no-results>No agents found for that name.</div>'
    else:
        for a in matches:
            items += (
                f'<a href="/profile/{a["agent_id"]}" style="text-decoration:none; color:inherit;">'
                f'  <div class="listing" data-agent-id="{a["agent_id"]}">'
                f'    <div style="font-weight:700; font-size:1.05rem;" data-field="result-name">{a["name"]}</div>'
                f'    <div class="muted" style="margin-top:4px;">'
                f'      <span class="pill" data-field="result-state">{a["state"]}</span>'
                f'      &nbsp;Licensing state · Real agent'
                f'    </div>'
                f'  </div>'
                f'</a>'
            )

    return PAGE_HEAD + f"<h1>Results for &ldquo;{request.args.get('q')}&rdquo;</h1>{items}" + PAGE_FOOT


@app.route("/profile/<agent_id>")
def profile(agent_id: str):
    agent = next((a for a in SAMPLE_AGENTS if a["agent_id"] == agent_id), None)
    if not agent:
        abort(404)
    return PAGE_HEAD + f"""
    <h1 data-field="name">{agent["name"]}</h1>
    <div class="card">
      <div class="muted">Licensing state</div>
      <div style="font-size:1.6rem; font-weight:800; margin-top:4px;" data-field="state">{agent["state"]}</div>
      <hr style="border:0; border-top:1px solid #334155; margin:18px 0;">
      <div class="muted">Agent ID</div>
      <div data-field="agent-id">{agent["agent_id"]}</div>
      <div class="muted" style="margin-top:14px;">License number</div>
      <div data-field="license-number">{agent["license_no"]}</div>
    </div>
    """ + PAGE_FOOT


def create_app() -> Flask:
    return app
