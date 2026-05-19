"""Mermaid diagram renderer for Streamlit with a full-window toggle.

Each diagram gets a ⛶ button in the top-right corner. Clicking it tries
the browser's Fullscreen API; if the iframe sandbox blocks that, it falls
back to a CSS-only expand that covers the iframe's visible area. ESC
closes either mode.

CDN-loaded — no extra Python package required.
"""
from __future__ import annotations

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
    .fs-hint {{ position:absolute; bottom:8px; right:12px;
                color:#475569; font-size:0.7rem;
                font-family:JetBrains Mono, monospace; opacity:0; transition:opacity 0.2s; }}
    .frame.expanded .fs-hint {{ opacity:1; }}

    /* Native fullscreen styling */
    :fullscreen .frame,
    :-webkit-full-screen .frame {{
      width:100vw; height:100vh;
      border:none; border-radius:0; padding:40px;
      display:flex; flex-direction:column;
    }}
    :fullscreen .mermaid,
    :-webkit-full-screen .mermaid {{
      flex:1; align-items:center;
    }}
    :fullscreen .mermaid svg,
    :-webkit-full-screen .mermaid svg {{
      width:auto !important; height:auto !important;
      max-width:95vw !important; max-height:88vh !important;
    }}

    /* CSS fallback expand (covers the iframe area) */
    .frame.expanded {{
      position:fixed; inset:0; z-index:9999;
      border:none; border-radius:0; padding:40px;
      display:flex; flex-direction:column;
    }}
    .frame.expanded .mermaid {{ flex:1; align-items:center; }}
    .frame.expanded .mermaid svg {{
      max-width:95% !important; max-height:88vh !important;
      width:auto !important; height:auto !important;
    }}
  </style>
</head>
<body>
  <div class="frame" id="frame">
    <button class="fs-btn" id="fsBtn" onclick="toggleFullscreen()">⛶  Full-window</button>
    <div class="mermaid">{graph}</div>
    <div class="fs-hint">press ESC to close</div>
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

    function _setBtn(expanded) {{
      const btn = document.getElementById('fsBtn');
      btn.textContent = expanded ? '✕  Close (ESC)' : '⛶  Full-window';
    }}

    function toggleFullscreen() {{
      const frame = document.getElementById('frame');
      // If already expanded in either mode, close it.
      if (document.fullscreenElement) {{
        document.exitFullscreen();
        return;
      }}
      if (frame.classList.contains('expanded')) {{
        frame.classList.remove('expanded');
        _setBtn(false);
        return;
      }}
      // Try native fullscreen first.
      const req = frame.requestFullscreen
                || frame.webkitRequestFullscreen
                || document.documentElement.requestFullscreen;
      if (req) {{
        Promise.resolve(req.call(frame))
          .then(() => _setBtn(true))
          .catch(() => {{
            frame.classList.add('expanded');
            _setBtn(true);
          }});
      }} else {{
        frame.classList.add('expanded');
        _setBtn(true);
      }}
    }}

    document.addEventListener('fullscreenchange', () => {{
      _setBtn(!!document.fullscreenElement);
    }});

    document.addEventListener('keydown', (e) => {{
      if (e.key === 'Escape') {{
        const frame = document.getElementById('frame');
        if (frame.classList.contains('expanded')) {{
          frame.classList.remove('expanded');
          _setBtn(false);
        }}
      }}
    }});
  </script>
</body>
</html>
"""


def mermaid(graph: str, height: int = 480) -> None:
    """Render a Mermaid diagram inside a Streamlit page.

    Each rendered diagram gets a ⛶ Full-window button. Native browser
    fullscreen is tried first; if blocked by the iframe sandbox, a CSS
    fallback covers the iframe's visible area. ESC closes either mode.
    """
    components.html(_MERMAID_TPL.format(graph=graph), height=height, scrolling=True)
