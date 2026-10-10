"""ASGI gatekeeper in front of the ADK runtime.

The ADK server registers many routes (memory, artifacts, live WebSocket, API docs…). Only the ones the web
app uses are allowed, each behind login, and the request's user must be the signed-in user. The user's
role is written into new agent sessions server-side, so the browser can't claim a different role.
"""

import json
import re

from anyio import to_thread

from breedernear_core import accounts

APP = "breedernear"
SESSION_PATH = re.compile(rf"^/apps/{APP}/users/([^/]+)/sessions(?:/([^/]+))?$")
RUN_PATH = re.compile(r"^/run(_sse)?$")
CLOSED_PREFIXES = ("/apps/", "/run", "/agent-identity", "/list-apps", "/version", "/docs", "/redoc",
                   "/openapi.json", "/health", "/debug", "/dev-ui", "/builder")
MAX_BODY = 1_000_000


async def _respond(send, status: int, detail: str) -> None:
    body = json.dumps({"detail": detail}).encode()
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


async def _read_body(receive) -> bytes:
    chunks, size = [], 0
    while True:
        message = await receive()
        chunks.append(message.get("body", b""))
        size += len(chunks[-1])
        if size > MAX_BODY:
            raise ValueError("body too large")
        if not message.get("more_body"):
            return b"".join(chunks)


def _replay(body: bytes, original_receive):
    """Hand the already-read body to the app, then pass through the client's real events.

    Returning http.disconnect here would make streaming responses (the AI chat) stop immediately.
    """
    sent = False

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return await original_receive()

    return receive


class Gatekeeper:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":                       # /run_live and any other socket: refused
            await receive()
            await send({"type": "websocket.close", "code": 1008})
            return
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path, method = scope["path"], scope["method"]
        session_match, run_match = SESSION_PATH.match(path), RUN_PATH.match(path)
        if not (session_match or run_match):
            if path.startswith(CLOSED_PREFIXES):
                await _respond(send, 404, "Not found.")
                return
            await self.app(scope, receive, send)               # /api/* and static files
            return
        if (run_match and method != "POST") or (session_match and method not in ("GET", "POST")):
            await _respond(send, 404, "Not found.")
            return

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        auth = headers.get("authorization", "")
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else None
        try:
            user = await to_thread.run_sync(accounts.authenticate, token)
        except accounts.AccountError as e:
            await _respond(send, e.status, str(e))
            return

        try:
            body = await _read_body(receive)
        except ValueError:
            await _respond(send, 413, "Request too large.")
            return
        if session_match:
            if session_match.group(1) != user["id"]:
                await _respond(send, 403, "Not your session.")
                return
            if method == "POST" and not session_match.group(2):
                data = json.loads(body or b"{}")
                data["state"] = {**(data.get("state") or {}), "role": user["role"], "user_name": user["name"],
                                 "device_id": user.get("session_device_id")}
                body = json.dumps(data).encode()
                kept = [(k, v) for k, v in scope["headers"] if k.lower() != b"content-length"]
                scope = {**scope, "headers": kept + [(b"content-length", str(len(body)).encode())]}
        else:
            try:
                data = json.loads(body or b"{}")
            except json.JSONDecodeError:
                await _respond(send, 400, "Invalid request.")
                return
            if data.get("user_id") != user["id"] or data.get("app_name") != APP:
                await _respond(send, 403, "Not your session.")
                return
        await self.app(scope, _replay(body, receive), send)
