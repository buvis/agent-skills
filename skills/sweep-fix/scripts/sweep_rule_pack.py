"""Render the ast-grep rule-pack YAML block of a sweep report."""
import json


def _yaml_quote(value):
    """Render `value` as a YAML double-quoted scalar. A JSON string is a
    valid YAML double-quoted scalar; characters JSON leaves raw that YAML
    forbids or folds (DEL, C1 incl. U+0085, U+2028/2029, BOM, other
    non-printables) are escaped as \\uXXXX / \\UXXXXXXXX."""
    return "".join(
        ch if ch.isprintable()
        else f"\\u{ord(ch):04x}" if ord(ch) <= 0xFFFF
        else f"\\U{ord(ch):08x}"
        for ch in json.dumps(value, ensure_ascii=False)
    )


def _render_astgrep_rule_block(derivation, hits):
    lines = []
    if derivation["kind"] != "astgrep":
        return lines

    seen_langs = list(dict.fromkeys(hit["lang"] for hit in hits if hit["lang"]))
    if not seen_langs:
        return lines

    message = _yaml_quote(derivation["reason"])
    pattern = _yaml_quote(derivation["pattern"])
    rule_docs = [
        "\n".join(
            [
                f"id: sweep-{lang}",
                f"language: {lang}",
                "severity: warning",
                f"message: {message}",
                "rule:",
                f"  pattern: {pattern}",
            ]
        )
        for lang in seen_langs
    ]
    lines.append("```yaml")
    lines.append("\n---\n".join(rule_docs))
    lines.append("```")
    lines.append("")
    return lines
