"""Local mock of the Texas Real Estate Commission license search.

Deliberately returns a DIFFERENT expiration date than the CRM has for
Maria Delgado — that's the demo's compliance-mismatch case.
"""
from __future__ import annotations

from flask import Flask, request

from verifier.fixtures import SAMPLE_AGENTS

app = Flask(__name__)


PAGE_HEAD = """
<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>TREC · License Holder Search</title>
<style>
  body { font-family: Arial, sans-serif; background:#F5F5F5; color:#222; margin:0; }
  header { background:#5A0A0A; color:#FFF; padding:14px 28px; }
  header h1 { margin:0; font-size:1.3rem; font-weight:600; }
  .wrap { max-width:780px; margin:30px auto; padding:24px; background:#FFF;
          border:1px solid #DDD; }
  h2 { color:#5A0A0A; font-size:1.15rem; margin-top:0; }
  label { display:block; font-weight:600; margin-top:12px; }
  input[type=text] { width:100%; padding:10px 12px; margin-top:4px; border:1px solid #999; box-sizing:border-box; }
  button { margin-top:18px; padding:10px 24px; background:#5A0A0A; color:white; border:0; cursor:pointer; }
  .detail { background:#FFF8E7; padding:14px 18px; border-left:4px solid #B8860B; margin-top:16px; }
  dt { font-weight:600; color:#5A0A0A; margin-top:8px; }
  dd { margin:0 0 4px 0; }
  .no-results { background:#FFEBEE; padding:12px 16px; border-left:4px solid #B71C1C; }
</style></head><body>
<header><h1>Texas Real Estate Commission</h1></header>
<div class="wrap">
"""

PAGE_FOOT = "</div></body></html>"


@app.route("/")
@app.route("/Public/LicenseeNameSearch.aspx", methods=["GET", "POST"])
def lookup():
    license_no = (request.values.get("licNumber") or "").strip()
    if request.method == "GET" and not license_no:
        return PAGE_HEAD + """
        <h2>License Holder Search</h2>
        <form method="post">
          <label for="licNumber">License Number</label>
          <input type="text" id="licNumber" name="licNumber" autofocus>
          <button type="submit">Search</button>
        </form>
        """ + PAGE_FOOT

    agent = next(
        (a for a in SAMPLE_AGENTS if a["state"] == "TX" and a["license_no"] == license_no),
        None,
    )
    if not agent:
        return PAGE_HEAD + f"""
        <h2>License Holder Search</h2>
        <div class="no-results" data-no-results>No license found for <strong>{license_no}</strong>.</div>
        """ + PAGE_FOOT

    # Deliberately different expiration to drive the mismatch scenario
    crm_exp = agent["expires_at"]
    dre_exp = "2027-11-22"  # vs CRM's 2026-11-22 — looks like a renewal we don't know about

    return PAGE_HEAD + f"""
    <h2>License Holder Detail</h2>
    <div class="detail">
      <dl>
        <dt>Name</dt><dd data-field="name">{agent["name"]}</dd>
        <dt>License Number</dt><dd data-field="license-number">{agent["license_no"]}</dd>
        <dt>License Type</dt><dd>Sales Agent</dd>
        <dt>Status</dt><dd>Active</dd>
        <dt>License Expiration Date</dt><dd data-field="expiration">{dre_exp}</dd>
      </dl>
    </div>
    """ + PAGE_FOOT


def create_app() -> Flask:
    return app
