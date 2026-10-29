#!/usr/bin/env python3
"""Embed attached images into a Confluence page by replacing placeholder macros.

Usage:
    python3 confluence_embed_images.py PAGE_ID image1.png [image2.png ...] [--token TOKEN] [--width WIDTH]

For each image, finds a Confluence 'note' macro whose body mentions the image
filename (without extension) and replaces it with an ac:image tag referencing
the attachment. If no matching note macro is found, appends the image at the
end of the page.

Set CONFLUENCE_BASE_URL and CONFLUENCE_SPACE_KEY explicitly.
Token resolution: --token arg > CONFLUENCE_TOKEN environment variable.
"""
import argparse, json, os, re, sys, urllib.request

BASE_URL = os.environ.get("CONFLUENCE_BASE_URL", "").rstrip("/")
SPACE_KEY = os.environ.get("CONFLUENCE_SPACE_KEY", "")

def get_token(explicit=None):
    if explicit:
        return explicit
    return os.environ.get("CONFLUENCE_TOKEN")

def get_page(page_id, token):
    req = urllib.request.Request(
        f"{BASE_URL}/rest/api/content/{page_id}?expand=body.storage,version",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)

def update_page(page_id, title, content, version, token):
    payload = json.dumps({
        "id": page_id, "type": "page", "title": title,
        "space": {"key": SPACE_KEY},
        "body": {"storage": {"value": content, "representation": "storage"}},
        "version": {"number": version}
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/rest/api/content/{page_id}", data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="PUT"
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)

def image_tag(filename, width):
    return f'<p><ac:image ac:width="{width}"><ri:attachment ri:filename="{filename}" /></ac:image></p>'

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("page_id", help="Confluence page ID")
    p.add_argument("images", nargs="+", help="Image filenames (must be already attached)")
    p.add_argument("--token", default=None)
    p.add_argument("--width", type=int, default=900, help="Display width (default: 900)")
    args = p.parse_args()

    if not BASE_URL:
        p.error("Set CONFLUENCE_BASE_URL to the selected Confluence instance.")
    if not SPACE_KEY:
        p.error("Set CONFLUENCE_SPACE_KEY to the page's existing space.")

    token = get_token(args.token)
    if not token:
        print("ERROR: No token.", file=sys.stderr); sys.exit(1)

    page = get_page(args.page_id, token)
    content = page["body"]["storage"]["value"]
    ver = page["version"]["number"]

    for img in args.images:
        tag = image_tag(img, args.width)
        stem = os.path.splitext(img)[0]
        # Try to replace a note macro mentioning this image
        pattern = rf'<ac:structured-macro ac:name="note"[^>]*>.*?{re.escape(stem)}.*?</ac:structured-macro>'
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, tag, content, count=1, flags=re.DOTALL)
            print(f"Replaced placeholder for {img}")
        else:
            content += f"\n{tag}"
            print(f"Appended {img} at end of page")

    result = update_page(args.page_id, page["title"], content, ver + 1, token)
    print(f"Updated to version {result['version']['number']}")
