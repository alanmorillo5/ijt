import httpx
import asyncio

async def main():
    payload = {
        "model": "qwen3.6:27b-q8_0",
        "messages": [
            {"role": "user", "content": "Return the JSON {'test': 'hello'}"}
        ],
        "stream": False,
        "format": "json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post("http://localhost:11434/api/chat", json=payload, timeout=20)
            print("Success:", res.json()["message"]["content"])
        except Exception as e:
            print("Error:", e)

asyncio.run(main())
