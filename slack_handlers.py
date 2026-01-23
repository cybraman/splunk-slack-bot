import re


def parse_args(text: str):
    """
    Input examples:
      "My Saved Search earliest=-2h latest=now limit=5"
      "failed_logins earliest=-15m"
    Returns: (search_name, params_dict)
    """
    text = (text or "").strip()
    if not text:
        return None, {}

    parts = text.split()
    search_name = parts[0]
    params = {}

    for token in parts[1:]:
        if "=" in token:
            k, v = token.split("=", 1)
            params[k.strip()] = v.strip()

    return search_name, params


def format_results(saved_search_name: str, sid: str, results: list):
    if not results:
        return f"✅ *{saved_search_name}* ran successfully.\n• SID: `{sid}`\n• No results found."

    # Build a compact message
    lines = [f"✅ *{saved_search_name}* results (top {len(results)}):", f"• SID: `{sid}`", ""]
    for i, row in enumerate(results, start=1):
        # show a few common keys if present, else show first few keys
        keys_priority = ["_time", "host", "source", "sourcetype", "user", "src", "dest", "count"]
        show_keys = [k for k in keys_priority if k in row][:4]
        if not show_keys:
            show_keys = list(row.keys())[:4]

        snippet = ", ".join([f"{k}={row.get(k)}" for k in show_keys])
        lines.append(f"{i}. {snippet}")

    return "\n".join(lines)
