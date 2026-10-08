import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

MARKER = "<!-- taskly-unit-test-agent -->"
API = "https://api.github.com"


def upsert_comment(repository: str, number: str, token: str, body: str) -> str:
    comments = _request("GET", f"/repos/{repository}/issues/{number}/comments?per_page=100", token)
    existing = next((comment for comment in comments if MARKER in comment.get("body", "")), None)
    if existing:
        _request("PATCH", f"/repos/{repository}/issues/comments/{existing['id']}", token, {"body": body})
        return "updated"
    _request("POST", f"/repos/{repository}/issues/{number}/comments", token, {"body": body})
    return "created"


def _request(method: str, path: str, token: str, payload: dict | None = None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(f"{API}{path}", data=data, method=method)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("User-Agent", "taskly-unit-test-agent")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"GitHub {method} {path} failed with HTTP {error.code}: {detail}") from error
    if not raw:
        return None
    return json.loads(raw)
