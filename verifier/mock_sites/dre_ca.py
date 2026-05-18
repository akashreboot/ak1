"""Local mock of the California DRE (eLicensing) public license-status site.

Mirrors the shape of www2.dre.ca.gov's public lookup: a search form taking
the license number, a result page with name + expiration.
"""
from __future__ import annotations

from flask import Flask, request

from verifier.fixtures import SAMPLE_AGENTS

app = Flask(__name__)

PAGE_HEAD = """
<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>California DRE · License Status</title>
<style>
  body { font-family: Georgia, "Times New Roman", serif; background:#FFFFFF; color:#222;
         margin:0; padding:0; }
  header { background:#003366; color:white; padding:18px 30px; }
  header h1 { margin:0; font-size:1.4rem; font-weight:600; letter-spacing:0; }
  header .sub { font-size:0.85rem; opacity:0.85; margin-top:4px; }
  .wrap { max-width:760px; margin:36px auto; padding:0 18px; }
  h2 { color:#003366; border-bottom:2px solid #003366; padding-bottom:6px; }
  label { display:block; font-weight:600; margin-top:14px; color:#333; }
  input[type=text] { width:100%; padding:10px 12px; margin-top:6px;
                     border:1px solid #888; font-size:1rem; box-sizing:border-box; }
  button { margin-top:18px; padding:10px 24px; background:#003366; color:white;
           border:0; font-size:1rem; cursor:pointer; }
  table { width:100%; border-collapse:collapse; margin-top:16px; }
  td, th { padding:8px 10px; border-bottom:1px solid #DDD; text-align:left; vertical-align:top; }
  th { color:#003366; background:#F4F4F4; width:38%; }
  .no-results { padding:14px 16px; background:#FFF4CE; border-left:4px solid #C8A800;
                margin-top:18px; color:#665300; }
</style></head><body>
<header>
  <h1>California Department of Real Estate</h1>
  <div class="sub">Public License Status Inquiry · eLicensing</div>
</header>
<div class="wrap">
"""

PAGE_FOOT = "</div></body></html>"


@app.route("/")
@app.route("/PublicASP/pplinfo.asp", methods=["GET", "POST"])
def lookup():
    license_no = (request.values.get("sel_LicID") or request.values.get("license_no") or "").strip()

    if request.method == "GET" and not license_no:
        return PAGE_HEAD + """
        <h2>Public License Status Inquiry</h2>
        <p>Enter a real estate license identification number below to view current status.</p>
        <form method="post" action="/PublicASP/pplinfo.asp">
          <label for="sel_LicID">License Identification Number</label>
          <input type="text" id="sel_LicID" name="sel_LicID" maxlength="16" autofocus>
          <button type="submit">Find</button>
        </form>
        """ + PAGE_FOOT

    agent = next(
        (a for a in SAMPLE_AGENTS if a["state"] == "CA" and a["license_no"] == license_no),
        None,
    )
    if not agent:
        return PAGE_HEAD + f"""
        <h2>Public License Status Inquiry</h2>
        <div class="no-results" data-no-results>No active license found for ID <strong>{license_no}</strong>.</div>
        <p><a href="/PublicASP/pplinfo.asp">&larr; Back to search</a></p>
        """ + PAGE_FOOT

    return PAGE_HEAD + f"""
    <h2>License Status</h2>
    <table>
      <tr><th>Licensee Name</th><td data-field="name">{agent["name"]}</td></tr>
      <tr><th>License Identification Number</th><td data-field="license-number">{agent["license_no"]}</td></tr>
      <tr><th>License Type</th><td>Salesperson</td></tr>
      <tr><th>License Status</th><td>Licensed</td></tr>
      <tr><th>License Expiration Date</th><td data-field="expiration">{agent["expires_at"]}</td></tr>
      <tr><th>State</th><td data-field="state">California</td></tr>
    </table>
    """ + PAGE_FOOT


def create_app() -> Flask:
    return app
