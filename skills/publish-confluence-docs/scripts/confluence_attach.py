#!/usr/bin/env python3
"""Upload or update file attachments on a Confluence page.

Usage:
    python3 confluence_attach.py PAGE_ID file1.png [file2.png ...] [--token TOKEN]

Uploads files as attachments. If an attachment with the same filename already
exists, it updates the existing attachment data.

Set CONFLUENCE_BASE_URL explicitly. Token comes from --token or CONFLUENCE_TOKEN.
No agent configuration files are read.
"""
import argparse, json, os, subprocess, sys, urllib.request

BASE_URL = os.environ.get("CONFLUENCE_BASE_URL", "").rstrip("/")

def get_token(explicit=None):
    if explicit:
        return explicit
    return os.environ.get("CONFLUENCE_TOKEN")

def get_existing_attachments(page_id, token):
    req = urllib.request.Request(
        f"{BASE_URL}/rest/api/content/{page_id}/child/attachment",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    return {a["title"]: a["id"] for a in data.get("results", [])}

def upload(page_id, filepath, token, existing):
    filename = os.path.basename(filepath)
    att_id = existing.get(filename)
    if att_id:
        url = f"{BASE_URL}/rest/api/content/{page_id}/child/attachment/{att_id}/data"
        action = "Updated"
    else:
        url = f"{BASE_URL}/rest/api/content/{page_id}/child/attachment"
        action = "Uploaded"

    r = subprocess.run([
        "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
        "-H", f"Authorization: Bearer {token}",
        "-H", "X-Atlassian-Token: nocheck",
        "-X", "POST", "-F", f"file=@{filepath}", url
    ], capture_output=True, text=True)

    code = r.stdout.strip()
    ok = code.startswith("2")
    print(f"{'OK' if ok else 'FAIL'}: {action} {filename} (HTTP {code})")
    return ok

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("page_id", help="Confluence page ID")
    p.add_argument("files", nargs="+", help="Files to attach")
    p.add_argument("--token", default=None, help="Bearer token")
    args = p.parse_args()

    if not BASE_URL:
        p.error("Set CONFLUENCE_BASE_URL to the selected Confluence instance.")

    token = get_token(args.token)
    if not token:
        print("ERROR: No token found. Set CONFLUENCE_TOKEN or pass --token.", file=sys.stderr)
        sys.exit(1)

    existing = get_existing_attachments(args.page_id, token)
    for f in args.files:
        upload(args.page_id, f, token, existing)
