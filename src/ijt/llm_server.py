import asyncio
import subprocess
import atexit
import httpx
from ijt.logging import get_logger

logger = get_logger("ollama_server")

_server_process = None
_start_lock = asyncio.Lock()

async def ensure_ollama_server(config: dict):
    global _server_process
    
    async with _start_lock:
        if _server_process is not None:
            return
            
        host = config.get("ollama_host", "http://localhost:11434")
        if "localhost" not in host and "127.0.0.1" not in host:
            return # Not local
            
        # Check if already running
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(host, timeout=2.0)
                if response.status_code == 200:
                    logger.debug("Ollama server is already running.")
                    return
            except httpx.RequestError:
                pass
                
        logger.info("Starting Ollama server...")
        try:
            import os
            from urllib.parse import urlparse
            
            env = os.environ.copy()
            parsed_url = urlparse(host)
            # Pass the host and port to ollama via OLLAMA_HOST so it binds correctly.
            if parsed_url.netloc:
                env["OLLAMA_HOST"] = parsed_url.netloc

            _server_process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env
            )
            
            # Wait for it to become ready
            for _ in range(30):
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(host, timeout=1.0)
                        if response.status_code == 200:
                            logger.info("Ollama server started successfully.")
                            break
                except httpx.RequestError:
                    pass
                await asyncio.sleep(1)
            else:
                logger.warning("Ollama server did not become ready in time.")
                
        except FileNotFoundError:
            logger.error("Ollama executable not found. Please install Ollama.")

def stop_ollama_server():
    global _server_process
    if _server_process is not None:
        logger.info("Stopping Ollama server...")
        _server_process.terminate()
        try:
            _server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_process.kill()
        _server_process = None

atexit.register(stop_ollama_server)
