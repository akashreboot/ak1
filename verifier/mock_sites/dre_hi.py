"""Local mock of the Hawaii DRE — returns a CAPTCHA wall to demonstrate
the HITL routing path in the demo.
"""
from __future__ import annotations

from flask import Flask, request

app = Flask(__name__)


@app.route("/")
@app.route("/license_search", methods=["GET", "POST"])
def captcha_wall():
    return (
        """
        <!doctype html>
        <html><head><meta charset="utf-8"><title>Hawaii DCCA · License Search</title>
        <style>
          body { font-family: system-ui, sans-serif; background:#FAFAFA; padding:48px 20px; }
          .wrap { max-width:520px; margin:0 auto; background:white; padding:32px;
                  border:1px solid #DDD; border-radius:6px; text-align:center; }
          .captcha { padding:32px 18px; background:#F2F2F2; border:1px dashed #888;
                     border-radius:6px; margin-top:24px; }
          .lock { font-size:2.4rem; }
        </style></head><body>
        <div class="wrap" data-captcha-wall>
          <div class="lock">🔒</div>
          <h2>Please verify you are not a robot</h2>
          <p style="color:#555;">To protect our records, the Hawaii license search requires CAPTCHA verification.</p>
          <div class="captcha">
            <input type="checkbox" disabled> I'm not a robot
            <div style="font-size:0.8rem; color:#888; margin-top:6px;">reCAPTCHA</div>
          </div>
        </div></body></html>
        """
    )


def create_app() -> Flask:
    return app
