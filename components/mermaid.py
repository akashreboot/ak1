"""Mermaid diagram renderer for Streamlit.

Inline view: a normal embedded diagram with scrolling for tall diagrams.

⛶ Full-window button: opens the diagram in a real browser window via a
Blob URL (escapes the Streamlit iframe entirely, and unlike about:blank
+ document.write, Blob-URL pages execute external <script src> tags
reliably). In the popup:
  * mouse wheel → zoom in / out (centered on cursor)
  * click + drag → pan
  * '↻ Reset' or '0' key → restore default
  * '✕ Close' or ESC → close the popup
  * '+' / '-' keys → step zoom
"""
from __future__ import annotations

import json

import streamlit.components.v1 as components


# ── Popup HTML (rendered server-side, graph baked in as text) ────────────
_POPUP_TPL = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Diagram · Full window</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
  <style>
    html, body {{
      margin:0; padding:0; background:#0F172A; color:#E2E8F0;
      font-family:Inter, -apple-system, sans-serif;
      overflow:hidden; height:100vh;
    }}
    #canvas {{
      width:100vw; height:100vh; display:block; cursor:grab;
    }}
    #canvas:active {{ cursor:grabbing; }}
    .mermaid {{
      width:100%; height:100%;
      display:flex; justify-content:center; align-items:center;
    }}
    .mermaid svg {{
      width:100% !important; height:100% !important;
      max-width:none !important;
    }}
    .toolbar {{
      position:fixed; top:14px; right:18px;
      display:flex; gap:8px; z-index:100;
    }}
    .btn {{
      background:rgba(34,211,238,0.12);
      border:1px solid rgba(34,211,238,0.5);
      color:#22D3EE;
      padding:8px 16px; border-radius:8px;
      font-size:0.88rem; font-weight:600;
      cursor:pointer; font-family:inherit;
      transition:background 0.15s ease;
    }}
    .btn:hover {{ background:rgba(34,211,238,0.25); }}
    .btn.danger {{
      background:rgba(239,68,68,0.12);
      border-color:rgba(239,68,68,0.5);
      color:#FCA5A5;
    }}
    .btn.danger:hover {{ background:rgba(239,68,68,0.25); }}
    .hint {{
      position:fixed; bottom:16px; left:50%;
      transform:translateX(-50%);
      color:#94A3B8; font-size:0.78rem;
      font-family:JetBrains Mono, monospace;
      background:rgba(15,23,42,0.85);
      padding:7px 16px; border-radius:999px;
      border:1px solid rgba(99,102,241,0.18);
      pointer-events:none;
    }}
    .error {{
      position:fixed; top:50%; left:50%; transform:translate(-50%,-50%);
      color:#FCA5A5; background:rgba(15,23,42,0.95);
      padding:18px 26px; border-radius:10px;
      border:1px solid rgba(239,68,68,0.4);
      max-width:80vw; font-size:0.9rem; display:none;
    }}
  </style>
</head>
<body>
  <div class="toolbar">
    <button class="btn" onclick="resetView()">↻  Reset (0)</button>
    <button class="btn danger" onclick="window.close()">✕  Close (ESC)</button>
  </div>
  <div id="canvas">
    <div class="mermaid" id="mer">{graph}</div>
  </div>
  <div class="hint">scroll to zoom · drag to pan · ESC close · 0 reset · + / − step zoom</div>
  <div class="error" id="err"></div>
  <script>
    let pz = null;

    function showError(msg) {{
      const e = document.getElementById('err');
      e.textContent = msg;
      e.style.display = 'block';
    }}

    function resetView() {{
      if (!pz) return;
      pz.resetZoom();
      pz.resetPan();
      pz.center();
      pz.fit();
    }}

    function init() {{
      if (typeof mermaid === 'undefined') {{
        showError('Mermaid failed to load from CDN. Check your network.');
        return;
      }}
      mermaid.initialize({{
        startOnLoad: false,
        theme: 'base',
        themeVariables: {{
          fontFamily: 'Inter, -apple-system, sans-serif',
          fontSize: '16px',
          background: '#0F172A',
          primaryColor: '#0F172A',
          primaryTextColor: '#E2E8F0',
          primaryBorderColor: '#22D3EE',
          lineColor: '#94A3B8',
          secondaryColor: '#1E293B',
          tertiaryColor: '#0F172A',
          clusterBkg: '#1E293B',
          clusterBorder: 'rgba(139,92,246,0.4)',
        }},
        flowchart: {{ curve: 'basis', padding: 18, useMaxWidth: false }},
      }});

      const host = document.getElementById('mer');
      const def = host.textContent.trim();
      mermaid.render('rendered', def).then(({{ svg }}) => {{
        host.innerHTML = svg;
        const svgEl = host.querySelector('svg');
        if (!svgEl) {{ showError('Mermaid produced no SVG.'); return; }}
        if (typeof svgPanZoom === 'undefined') {{
          // No pan/zoom but at least show the diagram
          return;
        }}
        pz = svgPanZoom(svgEl, {{
          zoomEnabled: true,
          mouseWheelZoomEnabled: true,
          panEnabled: true,
          controlIconsEnabled: false,
          dblClickZoomEnabled: true,
          fit: true,
          center: true,
          contain: false,
          minZoom: 0.3,
          maxZoom: 15,
          zoomScaleSensitivity: 0.35,
        }});
      }}).catch((err) => {{
        showError('Mermaid render error: ' + (err.message || err));
      }});
    }}

    document.addEventListener('keydown', (e) => {{
      if (e.key === 'Escape') window.close();
      else if (e.key === '0') resetView();
      else if ((e.key === '+' || e.key === '=') && pz) pz.zoomIn();
      else if ((e.key === '-' || e.key === '_') && pz) pz.zoomOut();
    }});

    if (document.readyState === 'loading') {{
      document.addEventListener('DOMContentLoaded', init);
    }} else {{
      init();
    }}
  </script>
</body>
</html>
"""


# ── Inline view + button that opens the popup via Blob URL ────────────────
_INLINE_TPL = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    html, body {{
      margin:0; padding:0; background:transparent;
      font-family:Inter, -apple-system, sans-serif;
      color:#E2E8F0;
    }}
    .frame {{
      position:relative; background:#0F172A;
      border:1px solid rgba(99,102,241,0.18);
      border-radius:12px; padding:14px; overflow:auto;
    }}
    .mermaid {{
      display:flex; justify-content:center;
      align-items:flex-start; min-height:200px;
    }}
    .mermaid svg {{ max-width:100% !important; height:auto !important; }}
    .fs-btn {{
      position:absolute; top:8px; right:8px;
      background:rgba(34,211,238,0.12);
      border:1px solid rgba(34,211,238,0.5);
      color:#22D3EE;
      padding:5px 12px; border-radius:7px;
      font-size:0.78rem; font-weight:600;
      font-family:inherit; cursor:pointer;
      z-index:10; transition:background 0.15s ease;
    }}
    .fs-btn:hover {{ background:rgba(34,211,238,0.25); }}
  </style>
</head>
<body>
  <div class="frame">
    <button class="fs-btn" onclick="openFullWindow()">⛶  Full-window</button>
    <div class="mermaid">{graph}</div>
  </div>

  <script>
    // The full popup HTML is delivered as JSON to avoid any escaping
    // headaches with backticks / interpolation. We build a Blob from it
    // and use the resulting blob: URL — pages loaded from a blob: URL
    // run external <script src> tags reliably, unlike about:blank.
    const POPUP_HTML = {popup_html_json};

    mermaid.initialize({{
      startOnLoad: true,
      theme: 'base',
      themeVariables: {{
        fontFamily: 'Inter, -apple-system, sans-serif',
        fontSize: '14px',
        background: '#0F172A',
        primaryColor: '#0F172A',
        primaryTextColor: '#E2E8F0',
        primaryBorderColor: '#22D3EE',
        lineColor: '#94A3B8',
        secondaryColor: '#1E293B',
        tertiaryColor: '#0F172A',
        clusterBkg: '#1E293B',
        clusterBorder: 'rgba(139,92,246,0.4)',
      }},
      flowchart: {{ curve: 'basis', padding: 14, useMaxWidth: true }},
    }});

    function openFullWindow() {{
      const blob = new Blob([POPUP_HTML], {{ type: 'text/html' }});
      const url = URL.createObjectURL(blob);
      const w = screen.availWidth || 1400;
      const h = screen.availHeight || 900;
      const popup = window.open(
        url, '_blank',
        'width=' + w + ',height=' + h + ',top=0,left=0,resizable=yes,scrollbars=no'
      );
      if (!popup) {{
        alert('Popup blocked.\\n\\nAllow popups for this site to open the full-window view.');
        URL.revokeObjectURL(url);
        return;
      }}
      // Revoke the blob URL after a delay (popup has loaded it by then)
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    }}
  </script>
</body>
</html>
"""


def mermaid(graph: str, height: int = 480) -> None:
    """Render a Mermaid diagram inside a Streamlit page.

    Inline: normal embedded diagram. Page scroll passes through.
    ⛶ Full-window: opens a real browser window via Blob URL with the
    diagram filling the viewport plus mouse-wheel zoom and drag-pan.
    """
    popup_html = _POPUP_TPL.format(graph=graph)
    inline_html = _INLINE_TPL.format(
        graph=graph,
        popup_html_json=json.dumps(popup_html),
    )
    components.html(inline_html, height=height, scrolling=True)
