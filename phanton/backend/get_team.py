"""Lista times Linear (Personal API Key via LINEAR_API_KEY no .env — sem Bearer)."""
import asyncio
import os

import httpx
from dotenv import load_dotenv

load_dotenv()


async def fetch_team():
    api_key = (os.getenv("LINEAR_API_KEY") or "").strip()
    if not api_key:
        raise SystemExit("Defina LINEAR_API_KEY no backend/.env")
    if api_key.lower().startswith("bearer "):
        api_key = api_key[7:].strip()

    headers = {"Authorization": api_key}
    query = {"query": "{ teams { nodes { id name key } } }"}

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://api.linear.app/graphql",
            json=query,
            headers=headers,
        )
        print("\n=== RESPOSTA CRUA DA API ===")
        print(res.json())
        print("============================\n")


if __name__ == "__main__":
    asyncio.run(fetch_team())
