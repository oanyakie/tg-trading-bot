import asyncio
from threading import Thread, Timer

import firebase_admin
from firebase_admin import credentials, firestore

from binance import AsyncClient, BinanceSocketManager, Client
from binance.exceptions import BinanceAPIException

import telegram.ext

# ── Firebase init (skip if already initialised by main bot) ──
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ── Telegram bot ──────────────────────────────
with open("botapi.txt", "r") as f:
    TOKEN = f.read().strip()
updater = telegram.ext.Updater(TOKEN, use_context=True)


# ══════════════════════════════════════════════
#  FIREBASE HELPERS
# ══════════════════════════════════════════════

def get_all_users():
    """Return a list of all user dicts from Firestore."""
    return [doc.to_dict() | {"_id": doc.id} for doc in db.collection("users").stream()]


def get_unique_api_params():
    """
    Collect every unique (key, secret) pair across all users.
    Returns (valid_params, invalid_params).
    """
    seen   = set()
    valid  = []
    invalid = []

    for user in get_all_users():
        for acc in user.get("accounts", []):
            key    = acc["key"]
            secret = acc["secret"]
            if (key, secret) in seen:
                continue
            seen.add((key, secret))
            p = {"key": key, "secret": secret}
            client = Client(api_key=key, api_secret=secret)
            try:
                client.get_account_api_permissions()
                valid.append(p)
            except BinanceAPIException:
                invalid.append(p)

    return valid, invalid


# ══════════════════════════════════════════════
#  STREAM LISTENER
# ══════════════════════════════════════════════

def _format_update_text(name, transactions, balances):
    """Build a readable account-update message."""
    tx_lines  = "\n".join(f"  {t}" for t in transactions) or "  —"
    bal_lines = "\n".join(f"  {b}" for b in balances)    or "  —"
    return (
        f"Account Update: {name}\n"
        f"Transaction:\n{tx_lines}\n"
        f"Account Balance:\n{bal_lines}"
    )


async def _listen(params):
    """
    Open a Binance user-data WebSocket for the given API credentials
    and forward account-update events to Telegram.
    """
    api_key    = params["key"]
    api_secret = params["secret"]

    client = await AsyncClient.create(api_key, api_secret, {"timeout": 10})
    bm     = BinanceSocketManager(client)

    async with bm.user_socket() as stream:
        pending = []  # buffer messages until outboundAccountPosition arrives

        while True:
            msg = await stream.recv()
            pending.append(msg)

            if msg["e"] != "outboundAccountPosition":
                continue

            # Parse buffered messages
            transactions = [
                f"{m['d']} {m['a']}"
                for m in pending if m["e"] == "balanceUpdate"
            ]
            balances = [
                f"{b['f']} {b['a']}"
                for m in pending if m["e"] == "outboundAccountPosition"
                for b in m["B"]
            ]
            pending = []  # reset buffer

            # Notify every user who owns this API key
            for user in get_all_users():
                for acc in user.get("accounts", []):
                    if acc["key"] == api_key and acc["secret"] == api_secret:
                        text = _format_update_text(acc["name"], transactions, balances)
                        try:
                            updater.bot.send_message(chat_id=user["_id"], text=text)
                        except Exception as e:
                            print(f"[blisteners] Telegram send error: {e}")

    await client.close_connection()


def _run_listener(params):
    """Run the async listener in a dedicated thread."""
    asyncio.run(_listen(params))


# ══════════════════════════════════════════════
#  FIRESTORE CHANGE WATCHER
# ══════════════════════════════════════════════

# Track which (key, secret) pairs are already being listened to
_active_params: set = set()

def _start_listener(params):
    key = (params["key"], params["secret"])
    if key not in _active_params:
        _active_params.add(key)
        Thread(target=_run_listener, args=[params], daemon=True).start()


def _watch_for_new_accounts():
    """
    Listen for new documents / updates in Firestore and
    start a listener thread for any newly added API keys.
    """
    def on_snapshot(col_snapshot, changes, read_time):
        for change in changes:
            if change.type.name in ("ADDED", "MODIFIED"):
                user = change.document.to_dict()
                for acc in user.get("accounts", []):
                    p = {"key": acc["key"], "secret": acc["secret"]}
                    client = Client(api_key=p["key"], api_secret=p["secret"])
                    try:
                        client.get_account_api_permissions()
                        _start_listener(p)
                    except BinanceAPIException:
                        pass  # will be retried by the timer

    db.collection("users").on_snapshot(on_snapshot)


# ══════════════════════════════════════════════
#  RETRY TIMER  (rechecks failed API keys every 20s)
# ══════════════════════════════════════════════

_invalid_params: list = []

def _retry_invalid():
    timer = Timer(20.0, _retry_invalid)
    timer.daemon = True
    timer.start()

    still_invalid = []
    for p in _invalid_params:
        client = Client(api_key=p["key"], api_secret=p["secret"])
        try:
            client.get_account_api_permissions()
            _start_listener(p)          # now valid — start listening
        except BinanceAPIException:
            still_invalid.append(p)     # still failing — keep retrying

    _invalid_params.clear()
    _invalid_params.extend(still_invalid)


# ══════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════

def main1():
    """Start all listeners, the Firestore watcher, and the retry timer."""
    valid, invalid = get_unique_api_params()
    _invalid_params.extend(invalid)

    # Start a listener thread for every currently-valid API key
    for p in valid:
        _start_listener(p)

    # Watch Firestore for newly added accounts
    Thread(target=_watch_for_new_accounts, daemon=True).start()

    # Periodically retry invalid keys
    _retry_invalid()


if __name__ == "__main__":
    main1()
    # Keep the main thread alive so daemon threads don't die
    import time
    while True:
        time.sleep(60)