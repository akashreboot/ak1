"""Mermaid diagram renderer for Streamlit.

Inline view: a normal embedded diagram with scrolling for tall diagrams.

⛶ Full-window button: opens the diagram in a NEW browser window (escapes
the Streamlit iframe entirely so the visible canvas is the whole
viewport, not just the iframe's allocated height). In the popup:
  * mouse wheel → zoom in / out
  * click + drag → pan
  * '↻ Reset' button or '0' key → restore default
  * '✕ Close' button or ESC → close the window
"""
from __future__ import annotations

import json

import streamlit.components.v1 as components


_MERMAID_TPL = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    html, body {{ margin:0; padding:0; background:transparent;
                  font-family:Inter, -apple-system, sans-serif;
                  color:#E2E8F0; }}
    .frame {{ position:relative; background:#0F172A;
              border:1px solid rgba(99,102,241,0.18);
              border-radius:12px; padding:14px; overflow:auto; }}
    .mermaid {{ display:flex; justify-content:center;
                align-items:flex-start; min-height:200px; }}
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
  <div class="frame" id="frame">
    <button class="fs-btn" onclick="openFullWindow()">⛶  Full-window</button>
    <div class="mermaid">{graph}</div>
  </div>

  <script>
    const GRAPH_DEF = {graph_json};

    mermaid.initialize({{
      startOnLoad:true,
      theme:'base',
      themeVariables:{{
        fontFamily:'Inter, -apple-system, sans-serif',
        fontSize:'14px',
        background:'#0F172A',
        primaryColor:'#0F172A',
        primaryTextColor:'#E2E8F0',
        primaryBorderColor:'#22D3EE',
        lineColor:'#94A3B8',
        secondaryColor:'#1E293B',
        tertiaryColor:'#0F172A',
        clusterBkg:'#1E293B',
        clusterBorder:'rgba(139,92,246,0.4)',
      }},
      flowchart:{{ curve:'basis', padding:14, useMaxWidth:true }},
    }});

    function openFullWindow() {{
      const w = screen.availWidth || 1400;
      const h = screen.availHeight || 900;
      const popup = window.open('', '_blank',
        `width=${{w}},height=${{h}},top=0,left=0,resizable=yes,scrollbars=no`);
      if (!popup) {{
        alert('Popup blocked.\\n\\nAllow popups for this site to open the full-window view.');
        return;
      }}
      popup.document.open();
      popup.document.write(FULL_WINDOW_HTML);
      popup.document.close();
    }}

    const FULL_WINDOW_HTML = `
<!doctype html>
<html><head>
<title>Diagram · Full window</title>
<meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"><\\/script>
<script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"><\\/script>
<style>
  html, body {{ margin:0; padding:0; background:#0F172A; color:#E2E8F0;
                font-family:Inter,-apple-system,sans-serif; overflow:hidden;
                height:100vh; }}
  .toolbar {{ position:fixed; top:14px; right:18px; display:flex; gap:8px; z-index:100; }}
  .btn {{ background:rgba(34,211,238,0.12); border:1px solid rgba(34,211,238,0.5);
          color:#22D3EE; padding:8px 16px; border-radius:8px; font-size:0.88rem;
          font-weight:600; cursor:pointer; font-family:inherit;
          transition:background 0.15s ease; }}
  .btn:hover {{ background:rgba(34,211,238,0.25); }}
  .btn.danger {{ background:rgba(239,68,68,0.12); border-color:rgba(239,68,68,0.5);
                 color:#FCA5A5; }}
  .btn.danger:hover {{ background:rgba(239,68,68,0.25); }}
  .hint {{ position:fixed; bottom:16px; left:50%; transform:translateX(-50%);
           color:#64748B; font-size:0.78rem; font-family:JetBrains Mono,monospace;
           background:rgba(15,23,42,0.85); padding:6px 14px; border-radius:999px;
           border:1px solid rgba(99,102,241,0.18); pointer-events:none; }}
  #canvas {{ width:100vw; height:100vh; display:block; cursor:grab; }}
  #canvas:active {{ cursor:grabbing; }}
  #canvas .mermaid {{ width:100%; height:100%; display:flex;
                       justify-content:center; align-items:center; }}
  #canvas .mermaid svg {{ width:100% !important; height:100% !important;
                           max-width:none !important; }}
</style>
</head><body>
<div class="toolbar">
  <button class="btn" onclick="reset()">↻  Reset (0)</button>
  <button class="btn danger" onclick="window.close()">✕  Close (ESC)</button>
</div>
<div id="canvas"><div class="mermaid" id="mer">${{escapeHtml(GRAPH_DEF)}}</div></div>
<div class="hint">scroll to zoom · drag to pan · ESC close · 0 reset</div>
<script>
  function escapeHtml(s) {{ return s; }}
  mermaid.initialize({{
    startOnLoad:false,
    theme:'base',
    themeVariables:{{
      fontFamily:'Inter,-apple-system,sans-serif', fontSize:'16px',
      background:'#0F172A', primaryColor:'#0F172A',
      primaryTextColor:'#E2E8F0', primaryBorderColor:'#22D3EE',
      lineColor:'#94A3B8', secondaryColor:'#1E293B',
      tertiaryColor:'#0F172A', clusterBkg:'#1E293B',
      clusterBorder:'rgba(139,92,246,0.4)',
    }},
    flowchart:{{ curve:'basis', padding:18, useMaxWidth:false }},
  }});
  let pz = null;
  (async () => {{
    const el = document.getElementById('mer');
    const def = el.textContent;
    const {{ svg }} = await mermaid.render('rendered', def);
    el.innerHTML = svg;
    const svgEl = el.querySelector('svg');
    pz = svgPanZoom(svgEl, {{
      zoomEnabled:true, mouseWheelZoomEnabled:true, panEnabled:true,
      controlIconsEnabled:false, dblClickZoomEnabled:true,
      fit:true, center:true, contain:false,
      minZoom:0.3, maxZoom:15, zoomScaleSensitivity:0.35,
    }});
  }})();
  function reset() {{ if (pz) {{ pz.resetZoom(); pz.resetPan(); pz.center(); pz.fit(); }} }}
  document.addEventListener('keydown', (e) => {{
    if (e.key === 'Escape') window.close();
    else if (e.key === '0') reset();
    else if (e.key === '+' || e.key === '=') {{ if (pz) pz.zoomIn(); }}
    else if (e.key === '-' || e.key === '_') {{ if (pz) pz.zoomOut(); }}
  }});
<\\/script>
</body></html>
    `;
  </script>
</body>
</html>
"""


def mermaid(graph: str, height: int = 480) -> None:
    """Render a Mermaid diagram inside a Streamlit page.

    The inline view is a normal embedded diagram (page scroll passes through).
    The ⛶ Full-window button opens a NEW browser window with the diagram
    rendered at full viewport size, with mouse-wheel zoom and click-drag pan.
    """
    payload = _MERMAID_TPL.format(graph=graph, graph_json=json.dumps(graph))
    components.html(payload, height=height, scrolling=True)
