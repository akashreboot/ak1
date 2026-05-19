"""Mermaid diagram renderer for Streamlit with full-window + pan/zoom.

Each diagram gets a ⛶ button in the top-right corner. When expanded:
  * Mouse wheel → zoom in / out (centered on cursor)
  * Click + drag → pan
  * '↻ Reset' button → restore default zoom and position
  * ESC or close button → exit full-window

When NOT expanded, the diagram behaves normally (page scroll passes through).

Mermaid + svg-pan-zoom both CDN-loaded — no extra Python deps.
"""
from __future__ import annotations

import streamlit.components.v1 as components


_MERMAID_TPL = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
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

    .toolbar {{
      position:absolute; top:8px; right:8px;
      display:flex; gap:6px; z-index:10;
    }}
    .tb-btn {{
      background:rgba(34,211,238,0.12);
      border:1px solid rgba(34,211,238,0.5);
      color:#22D3EE;
      padding:5px 12px; border-radius:7px;
      font-size:0.78rem; font-weight:600;
      font-family:inherit; cursor:pointer;
      transition:background 0.15s ease;
    }}
    .tb-btn:hover {{ background:rgba(34,211,238,0.25); }}
    .tb-btn.reset {{ display:none; }}
    .frame.expanded .tb-btn.reset,
    :fullscreen .tb-btn.reset,
    :-webkit-full-screen .tb-btn.reset {{ display:inline-block; }}

    .fs-hint {{ position:absolute; bottom:10px; right:16px;
                color:#64748B; font-size:0.72rem;
                font-family:JetBrains Mono, monospace; opacity:0;
                transition:opacity 0.2s; pointer-events:none; }}
    .frame.expanded .fs-hint,
    :fullscreen .fs-hint,
    :-webkit-full-screen .fs-hint {{ opacity:1; }}

    /* Native fullscreen styling */
    :fullscreen .frame,
    :-webkit-full-screen .frame {{
      width:100vw; height:100vh;
      border:none; border-radius:0; padding:24px;
      display:flex; flex-direction:column;
    }}
    :fullscreen .mermaid,
    :-webkit-full-screen .mermaid {{
      flex:1; align-items:stretch;
      cursor:grab;
    }}
    :fullscreen .mermaid:active,
    :-webkit-full-screen .mermaid:active {{ cursor:grabbing; }}
    :fullscreen .mermaid svg,
    :-webkit-full-screen .mermaid svg {{
      width:100% !important; height:100% !important;
      max-width:none !important;
    }}

    /* CSS fallback expand */
    .frame.expanded {{
      position:fixed; inset:0; z-index:9999;
      border:none; border-radius:0; padding:24px;
      display:flex; flex-direction:column;
    }}
    .frame.expanded .mermaid {{
      flex:1; align-items:stretch; cursor:grab;
    }}
    .frame.expanded .mermaid:active {{ cursor:grabbing; }}
    .frame.expanded .mermaid svg {{
      width:100% !important; height:100% !important;
      max-width:none !important;
    }}
  </style>
</head>
<body>
  <div class="frame" id="frame">
    <div class="toolbar">
      <button class="tb-btn reset" id="resetBtn" onclick="resetZoom()" title="Reset zoom and position">↻  Reset</button>
      <button class="tb-btn" id="fsBtn" onclick="toggleFullscreen()">⛶  Full-window</button>
    </div>
    <div class="mermaid">{graph}</div>
    <div class="fs-hint">scroll to zoom · drag to pan · ESC to close</div>
  </div>

  <script>
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

    let panZoom = null;

    function _activatePanZoom() {{
      const svg = document.querySelector('.mermaid svg');
      if (!svg) {{ setTimeout(_activatePanZoom, 80); return; }}
      // Remove Mermaid's max-width:100% so svg-pan-zoom can size freely
      svg.style.maxWidth = 'none';
      svg.style.width = '100%';
      svg.style.height = '100%';
      try {{
        panZoom = svgPanZoom(svg, {{
          zoomEnabled:        true,
          controlIconsEnabled:false,
          mouseWheelZoomEnabled: true,
          panEnabled:         true,
          fit:                true,
          center:             true,
          minZoom:            0.4,
          maxZoom:            10,
          zoomScaleSensitivity: 0.35,
          dblClickZoomEnabled:true,
          contain:            false,
        }});
      }} catch (e) {{ /* svg-pan-zoom failed silently — fullscreen still works */ }}
    }}

    function _destroyPanZoom() {{
      if (panZoom) {{
        try {{ panZoom.destroy(); }} catch (e) {{}}
        panZoom = null;
        // Reset SVG styles so it returns to inline size
        const svg = document.querySelector('.mermaid svg');
        if (svg) {{
          svg.style.maxWidth = '100%';
          svg.style.width = '';
          svg.style.height = 'auto';
        }}
      }}
    }}

    function resetZoom() {{
      if (panZoom) {{ panZoom.reset(); }}
    }}

    function _setBtn(expanded) {{
      document.getElementById('fsBtn').textContent =
        expanded ? '✕  Close (ESC)' : '⛶  Full-window';
    }}

    function toggleFullscreen() {{
      const frame = document.getElementById('frame');
      if (document.fullscreenElement) {{
        document.exitFullscreen();
        return;
      }}
      if (frame.classList.contains('expanded')) {{
        _destroyPanZoom();
        frame.classList.remove('expanded');
        _setBtn(false);
        return;
      }}
      const req = frame.requestFullscreen
                || frame.webkitRequestFullscreen;
      if (req) {{
        Promise.resolve(req.call(frame))
          .then(() => {{ _setBtn(true); setTimeout(_activatePanZoom, 120); }})
          .catch(() => {{
            frame.classList.add('expanded');
            _setBtn(true);
            setTimeout(_activatePanZoom, 120);
          }});
      }} else {{
        frame.classList.add('expanded');
        _setBtn(true);
        setTimeout(_activatePanZoom, 120);
      }}
    }}

    document.addEventListener('fullscreenchange', () => {{
      const inFs = !!document.fullscreenElement;
      _setBtn(inFs);
      if (!inFs) _destroyPanZoom();
    }});

    document.addEventListener('keydown', (e) => {{
      if (e.key === 'Escape') {{
        const frame = document.getElementById('frame');
        if (frame.classList.contains('expanded')) {{
          _destroyPanZoom();
          frame.classList.remove('expanded');
          _setBtn(false);
        }}
      }} else if (e.key === '0' && (document.fullscreenElement
                  || document.getElementById('frame').classList.contains('expanded'))) {{
        // '0' resets zoom — quick keyboard shortcut
        resetZoom();
      }}
    }});
  </script>
</body>
</html>
"""


def mermaid(graph: str, height: int = 480) -> None:
    """Render a Mermaid diagram inside a Streamlit page.

    Each diagram gets a ⛶ Full-window button. When expanded:
      * mouse-wheel zoom in/out
      * click + drag to pan
      * ↻ Reset button (or '0' key) restores default
      * ESC closes
    Inline view behaves normally — no zoom hijacking the page scroll.
    """
    components.html(_MERMAID_TPL.format(graph=graph), height=height, scrolling=True)
