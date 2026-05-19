"""Mermaid diagram renderer for Streamlit.

Streamlit doesn't natively support Mermaid; we embed it via the components
API. CDN-loaded so there's no extra Python package to install.
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
                  font-family:Inter, -apple-system, sans-serif; }}
    .frame {{ background:#0F172A; border:1px solid rgba(99,102,241,0.18);
              border-radius:12px; padding:14px; }}
    .mermaid {{ display:flex; justify-content:center; }}
  </style>
</head>
<body>
  <div class="frame"><div class="mermaid">{graph}</div></div>
  <script>
    mermaid.initialize({{
      startOnLoad:true,
      theme:'base',
      themeVariables: {{
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
      flowchart: {{ curve:'basis', padding:14, useMaxWidth:true }},
    }});
  </script>
</body>
</html>
"""


def mermaid(graph: str, height: int = 480) -> None:
    """Render a Mermaid diagram inside a Streamlit page.

    Scrolling is enabled so a diagram taller than the iframe never gets clipped —
    the user can scroll within the embedded frame instead.
    """
    components.html(_MERMAID_TPL.format(graph=graph), height=height, scrolling=True)
