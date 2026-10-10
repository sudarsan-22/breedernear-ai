"""Runs the real ADK agent tree (real Gemini) in-process against the sample data, for live evals.

Each case asserts properties rather than an exact tool sequence: which tools must or must not run,
what the code-computed results were, and what the reply must not contain. See
docs/implementation/06-testing-and-evaluation.md.
"""

import asyncio
import io
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from google.genai import types
from PIL import Image, ImageOps

from breedernear_core import deps
from breedernear_core.catalog import seed_listings
from breedernear_core.services.store import MemoryStore
from breedernear_core.services.uploads import MemoryUploads

APP = "breedernear"
WEB = Path(__file__).resolve().parents[2] / "web"


@dataclass
class Transcript:
    calls: list[tuple[str, str, dict]] = field(default_factory=list)  # (agent, tool, args)
    responses: dict[str, list[dict]] = field(default_factory=dict)  # tool -> responses
    text: str = ""

    def called(self, tool: str) -> bool:
        return any(name == tool for _, name, _ in self.calls)

    def last(self, tool: str) -> dict:
        return self.responses.get(tool, [{}])[-1]

    def args(self, tool: str) -> list[dict]:
        return [a for _, name, a in self.calls if name == tool]


class Harness:
    def __init__(self) -> None:
        from google.adk.runners import InMemoryRunner

        from agents.breedernear.agent import root_agent

        self.store, self.uploads = MemoryStore(), MemoryUploads()
        for listing in seed_listings():
            self.store.save_listing(listing["id"], listing)
        deps.set_deps(store=self.store, uploads=self.uploads)  # real Gemini vision
        self.runner = InMemoryRunner(agent=root_agent, app_name=APP)

    def photo(self, guest: str, listing_image: str, fresh: bool = False) -> str:
        """Upload a sample photo; fresh=True mirrors and crops it so it is not a duplicate."""
        img = Image.open(WEB / "img" / "listings" / listing_image).convert("RGB")
        if fresh:
            img = ImageOps.mirror(img).crop((40, 30, img.width - 40, img.height - 30))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=90)
        return self.uploads.put(guest, buf.getvalue(), "image/jpeg", "listing_photo")

    def chat(self, messages: list[str], mode: str = "", guest: str | None = None) -> tuple[Transcript, str]:
        guest = guest or f"eval-{uuid.uuid4().hex[:8]}"
        return asyncio.run(self._chat(messages, mode, guest)), guest

    async def _chat(self, messages: list[str], mode: str, guest: str) -> Transcript:
        session = await self.runner.session_service.create_session(
            app_name=APP, user_id=guest, state={"mode": mode}
        )
        t = Transcript()
        for message in messages:
            content = types.Content(role="user", parts=[types.Part(text=message)])
            texts = []
            async for ev in self.runner.run_async(user_id=guest, session_id=session.id, new_message=content):
                for part in (ev.content.parts if ev.content else []) or []:
                    if part.function_call:
                        t.calls.append(
                            (ev.author, part.function_call.name, dict(part.function_call.args or {}))
                        )
                    elif part.function_response:
                        t.responses.setdefault(part.function_response.name, []).append(
                            dict(part.function_response.response or {})
                        )
                    elif part.text and not part.thought and ev.author != "user":
                        texts.append(part.text)
            t.text = "\n".join(texts)
        return t

    def close(self) -> None:
        deps.set_deps()
