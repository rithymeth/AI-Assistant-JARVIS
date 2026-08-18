import socket

import uvicorn

from config.settings import PORT


def _lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # no data sent — just resolves the outbound-facing local IP
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    lan_ip = _lan_ip()
    lan_url = f"http://{lan_ip}:{PORT}"
    print("=" * 60)
    print(f"  Javi running at http://localhost:{PORT} (this machine)")
    print(f"  From your phone (same WiFi): {lan_url}")
    print("  LAN access requires a per-user access code (see /auth/me, /auth/users)")
    print("  -> the bootstrap admin's code is the one in .access_code / ACCESS_CODE")
    print("=" * 60)
    uvicorn.run("api.server:app", host="0.0.0.0", port=PORT, reload=False)
