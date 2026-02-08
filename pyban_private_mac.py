import os
import time
import requests
import urllib3
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning

def log(msg):
    """Print with timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")

# --- CONFIGURATION ---
UNIFI_IP = os.getenv("UNIFI_IP", "192.168.3.1")
USERNAME = os.getenv("UNIFI_USERNAME", "ton_user")
PASSWORD = os.getenv("UNIFI_PASSWORD", "ton_password")
SITE_ID = os.getenv("UNIFI_SITE_ID", "default")
UNIFI_OS = os.getenv("UNIFI_OS", "false").lower() in ["1", "true", "yes"]
UNIFI_VERSION = os.getenv("UNIFI_VERSION", "v5")
PORT_ENV = os.getenv("UNIFI_PORT", "").strip()
if PORT_ENV:
    try:
        UNIFI_PORT = int(PORT_ENV)
    except ValueError:
        UNIFI_PORT = 443 if UNIFI_OS else 8443
else:
    UNIFI_PORT = 443 if UNIFI_OS else 8443
UNIFI_SSL_VERIFY = os.getenv("UNIFI_SSL_VERIFY", "false").lower() in ["1", "true", "yes"]

# Home Assistant notifications
HA_URL = os.getenv("HA_URL", "").strip()
HA_TOKEN = os.getenv("HA_TOKEN", "").strip()
HA_NOTIFY_SERVICE = os.getenv("HA_NOTIFY_SERVICE", "").strip()
HA_VERIFY = os.getenv("HA_VERIFY", "true").lower() in ["1", "true", "yes"]

# ⚠️ CRITICAL WHITELIST ⚠️
# Add your own device MACs here (iPhone, Laptop, Watch)
# Otherwise you'll get kicked if your phone enables private MAC by default.
DEFAULT_WHITELIST = [
    "ac:xx:xx:xx:xx:xx", # My iPhone
    "e4:xx:xx:xx:xx:xx", # Laptop
]

# Check frequency (in seconds)
WHITELIST_ENV = os.getenv("WHITELIST", "").strip()
if WHITELIST_ENV:
    WHITELIST = [mac.strip() for mac in WHITELIST_ENV.split(",") if mac.strip()]
else:
    WHITELIST = DEFAULT_WHITELIST

# Scan interval (in seconds)
try:
    SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "10"))
except ValueError:
    SCAN_INTERVAL = 10

def is_private_mac(mac):
    """
    Detects if a MAC is random/private.
    The 2nd character must be 2, 6, A or E.
    """
    try:
        second_char = mac[1].lower()
        return second_char in ['2', '6', 'a', 'e']
    except IndexError:
        return False

def _set_csrf_token(session, response, base_url):
    token = None
    for k, v in response.headers.items():
        if k.lower() == "x-csrf-token":
            token = v
            break
    if not token:
        try:
            csrf_resp = session.get(f"{base_url}/api/auth/csrf", timeout=10)
            if csrf_resp.ok:
                token = csrf_resp.json().get("csrfToken")
        except Exception:
            token = None
    if token:
        session.headers.update({"X-CSRF-Token": token})


def _login_unifi_os(session, base_url):
    payload = {"username": USERNAME, "password": PASSWORD}
    r = session.post(f"{base_url}/api/auth/login", json=payload, timeout=10)
    if r.status_code == 200:
        _set_csrf_token(session, r, base_url)
        return "/proxy/network"
    if r.status_code == 404:
        return None
    raise Exception(f"Login failed - status code: {r.status_code}")


def _login_legacy(session, base_url):
    payload = {"username": USERNAME, "password": PASSWORD}
    r = session.post(f"{base_url}/api/login", json=payload, timeout=10)
    if r.status_code == 200:
        _set_csrf_token(session, r, base_url)
        return ""
    if r.status_code == 404:
        return None
    raise Exception(f"Login failed - status code: {r.status_code}")


def _notify_home_assistant(title, message):
    if not (HA_URL and HA_TOKEN and HA_NOTIFY_SERVICE):
        log("⚠️ Home Assistant notification disabled (HA_URL/HA_TOKEN/HA_NOTIFY_SERVICE missing).")
        return
    try:
        service = HA_NOTIFY_SERVICE.strip()
        if service.startswith("notify."):
            service = service.split(".", 1)[1]
        url = f"{HA_URL.rstrip('/')}/api/services/notify/{service}"
        log(f"📣 Sending Home Assistant notification to {url} ...")
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {HA_TOKEN}"},
            json={"title": title, "message": message},
            timeout=30,
            verify=HA_VERIFY,
        )
        log(f"📣 Home Assistant response: {resp.status_code} {resp.text[:500]}")
        resp.raise_for_status()
    except Exception as e:
        log(f"⚠️ Home Assistant notification failed: {e}")


def main():
    log(f"🔌 Connecting to UniFi controller ({UNIFI_IP}:{UNIFI_PORT})...")

    if not UNIFI_SSL_VERIFY:
        urllib3.disable_warnings(InsecureRequestWarning)

    session = requests.Session()
    session.verify = UNIFI_SSL_VERIFY
    session.headers.update({"Content-Type": "application/json", "Referer": f"https://{UNIFI_IP}"})
    base_url = f"https://{UNIFI_IP}:{UNIFI_PORT}"

    try:
        base_path = None
        if UNIFI_OS:
            base_path = _login_unifi_os(session, base_url)
        if base_path is None:
            base_path = _login_legacy(session, base_url)
        if base_path is None:
            raise Exception("Login failed - status code: 404")
        log("✅ Connected successfully.")
    except Exception as e:
        log(f"❌ Connection error: {e}")
        return

    log("🚀 Monitoring active. Press Ctrl+C to stop.")

    try:
        while True:
            # Fetch all clients (connected and recently disconnected)
            clients_resp = session.get(
                f"{base_url}{base_path}/api/s/{SITE_ID}/stat/sta",
                timeout=10,
            )
            clients_resp.raise_for_status()
            try:
                clients = clients_resp.json().get("data", [])
            except Exception as e:
                log(f"⚠️ Invalid UniFi JSON response: {e}")
                log(f"⚠️ Raw content (first 500 chars): {clients_resp.text[:500]}")
                time.sleep(SCAN_INTERVAL)
                continue

            for client in clients:
                mac = client.get('mac', '').lower()
                name = client.get('name') or client.get('hostname') or 'Unknown'
                is_blocked = client.get('blocked', False)

                # If device is already blocked, skip it
                if is_blocked:
                    continue

                # MAC analysis
                if is_private_mac(mac):
                    
                    # Whitelist check
                    if mac in [w.lower() for w in WHITELIST]:
                        # print(f"🛡️ {name} ({mac}) is whitelisted.")
                        continue
                    
                    # ACTION: BLOCK
                    log(f"🚨 DETECTION: {name} uses private MAC ({mac})")
                    log(f"🔨 Blocking...")
                    
                    try:
                        block_resp = session.post(
                            f"{base_url}{base_path}/api/s/{SITE_ID}/cmd/stamgr",
                            json={"cmd": "block-sta", "mac": mac},
                            timeout=10,
                        )
                        block_resp.raise_for_status()
                        log(f"💀 {name} blocked successfully.")
                        _notify_home_assistant(
                            "Private MAC blocked",
                            f"{name} ({mac}) was blocked on UniFi.",
                        )
                    except Exception as e:
                        log(f"❌ Block failed for {name}: {e}")

            time.sleep(SCAN_INTERVAL)

    except KeyboardInterrupt:
        log("Script stopped.")
    except Exception as e:
        log(f"Unexpected error: {e}")
    finally:
        pass

if __name__ == "__main__":
    main()