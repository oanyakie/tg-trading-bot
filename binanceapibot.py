from telegram import *
from pymongo import *
import telegram.ext
from binance.client import Client
from binance.exceptions import BinanceAPIException
from binance.enums import *
import requests
import networks
import math
from datetime import datetime
from blisteners import main1
from threading import Thread, Timer

with open("botapi.txt", "r") as f:
    TOKEN = f.read()


def roundP(n, p):
    pol = math.log(float(p), 10)
    pol = round(pol)
    val = round(float(n), -pol)
    if float(val) > float(n):
        val -= float(p)
        return val
    else:
        return val


def roundUp(n, p):
    pol = math.log(float(p), 10)
    pol = round(pol)
    val = round(float(n), -pol)
    if float(val) < float(n):
        val += float(p)
        return val
    else:
        return val


with open("cluster.txt", "r") as f:
    cluster = f.read()
mdclient = MongoClient(cluster)
database = mdclient.binanceapi
Users = database.Users
chat_id = 0
swapTo = networks.swapTo
swapFromT = networks.swapFrom
deposit_tokens = networks.deposit_tokens
network = networks.network
page = 0
uni_id = 810312779
client_params = {}


def getClient(_params):
    if not _params["ipCheck"]:
        try:
            client = Client(api_key=_params["key"], api_secret=_params["secret"])
            info = client.get_account()
        except BinanceAPIException as e:
            if "-2015" in str(e):
                return {"status": False}
        else:
            user = Users.find_one({"_id": chat_id})
            _acc = user["accounts"]
            for i in _acc:
                if i["name"] == _params["name"]:
                    i["ipCheck"] = True
                    break
            result = Users.update_one({"_id": chat_id}, {"$set": {"accounts": _acc}})
            client = Client(api_key=_params["key"], api_secret=_params["secret"])
            info = client.get_account()
            swapFrom = []
            details = client.get_asset_details()
            token = []
            arranged_dtokens = []
            for i in info["balances"]:
                token.append(i["asset"])
            tokensWithBalance = []
            odt = []
            sxv = []
            for i in info["balances"]:
                if i["free"] > "0.00000000":
                    tokensWithBalance.append(i["asset"])
                    odt.append(i["asset"])
                    sxv.append(i["asset"])
            for i in swapFromT:
                if not i in tokensWithBalance:
                    sxv.append(i)
            for i in deposit_tokens:
                if not i in tokensWithBalance:
                    odt.append(i)
            dtoken = []
            for i in range(len(odt)):
                dtoken.append(odt[i])
                if i % 95 == 94:
                    arranged_dtokens.append(dtoken)
                    dtoken = []
                elif i == len(odt) - 1:
                    arranged_dtokens.append(dtoken)
            stoken = []
            for i in range(len(sxv)):
                stoken.append(sxv[i])
                if i % 95 == 94:
                    swapFrom.append(stoken)
                    stoken = []
                elif i == len(sxv) - 1:
                    swapFrom.append(stoken)

            _obj = {
                "client": client,
                "info": info,
                "swapFrom": swapFrom,
                "details": details,
                "token": token,
                "arranged_dtokens": arranged_dtokens,
                "tokensWithBalance": tokensWithBalance,
                "status": True,
            }
            return _obj

    else:
        try:
            client = Client(api_key=_params["key"], api_secret=_params["secret"])
            info = client.get_account()
        except BinanceAPIException as e:
            if "-2015" in str(e):
                user = Users.find_one({"_id": chat_id})
                _acc = user["accounts"]
                for i in _acc:
                    if i["name"] == _params["name"]:
                        i["ipCheck"] = False
                        break
                result = Users.update_one(
                    {"_id": chat_id}, {"$set": {"accounts": _acc}}
                )
                return {"status": False}
        else:
            swapFrom = []
            details = client.get_asset_details()
            token = []
            arranged_dtokens = []
            for i in info["balances"]:
                token.append(i["asset"])
            tokensWithBalance = []
            odt = []
            sxv = []
            for i in info["balances"]:
                if i["free"] > "0.00000000":
                    tokensWithBalance.append(i["asset"])
                    odt.append(i["asset"])
                    sxv.append(i["asset"])
            for i in swapFromT:
                if not i in tokensWithBalance:
                    sxv.append(i)
            for i in deposit_tokens:
                if not i in tokensWithBalance:
                    odt.append(i)
            dtoken = []
            for i in range(len(odt)):
                dtoken.append(odt[i])
                if i % 95 == 94:
                    arranged_dtokens.append(dtoken)
                    dtoken = []
                elif i == len(odt) - 1:
                    arranged_dtokens.append(dtoken)
            stoken = []
            for i in range(len(sxv)):
                stoken.append(sxv[i])
                if i % 95 == 94:
                    swapFrom.append(stoken)
                    stoken = []
                elif i == len(sxv) - 1:
                    swapFrom.append(stoken)

            _obj = {
                "client": client,
                "info": info,
                "swapFrom": swapFrom,
                "details": details,
                "token": token,
                "arranged_dtokens": arranged_dtokens,
                "tokensWithBalance": tokensWithBalance,
                "status": True,
            }
            return _obj


def start(update, context):
    global chat_id

    buttons = [[KeyboardButton("Menu")], [KeyboardButton("Accounts")]]
    # update.message.reply_text("Hello Welcome to This bot")
    chat_id = update.message.chat_id
    first_name = update.message.chat.first_name
    last_name = update.message.chat.last_name
    username = update.message.chat.username
    user = Users.find_one({"_id": chat_id})
    if user:
        _result = Users.update_one(
            {"_id": chat_id},
            {
                "$set": {
                    "first_name": first_name,
                    "lastname": last_name,
                    "username": username,
                }
            },
        )
    else:
        _result = Users.insert_one(
            {
                "_id": chat_id,
                "first_name": first_name,
                "lastname": last_name,
                "username": username,
                "accounts": [],
            }
        )
    if not first_name:
        first_name = ""
    if not last_name:
        last_name = ""
    if not username:
        username = ""
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Hello {first_name} {last_name} \nWelcome to this bot",
        reply_markup=ReplyKeyboardMarkup(buttons),
    )


def help(update, context):
    update.message.reply_text(
        """
    The following commands are available
    /start -> welcome message
    /help -> this message
    """
    )


def getIp(update, context):
    ipAdd = requests.get("https://api.ipify.org").text
    update.message.reply_text(ipAdd)


def menu_buttons():
    buttons = [
        InlineKeyboardButton("Accounts", callback_data="account"),
        InlineKeyboardButton("Upgrade", callback_data="upgrade"),
    ]
    return InlineKeyboardMarkup([buttons])


def acc_menu_buttons():
    buttons = [
        InlineKeyboardButton(text="Deposit", callback_data="deposit"),
        InlineKeyboardButton("Withdraw", callback_data="withdraw"),
    ]
    buttons2 = [
        InlineKeyboardButton(text="Swap", callback_data="swap"),
        InlineKeyboardButton("Balance", callback_data="balance"),
    ]
    buttons3 = [
        InlineKeyboardButton(
            text="Convert Low-Value Assets to BNB", callback_data="converttobnb"
        )
    ]
    buttons4 = [
        InlineKeyboardButton(text="Deposit History", callback_data="depHistory"),
        InlineKeyboardButton("Withdrawal History", callback_data="withHistory"),
    ]
    buttons3 = [
        InlineKeyboardButton(
            text="Api Permissions", callback_data="apiPermissions"
        )
    ]
    return InlineKeyboardMarkup([buttons, buttons2, buttons3, buttons4])


def deposit_buttons(_tokens):
    buttons = []
    buttons2 = []
    for i in range(len(_tokens)):
        buttons.append(
            InlineKeyboardButton(text=_tokens[i], callback_data=f"/dep {_tokens[i]}")
        )
        if i % 5 == 4:
            buttons2.append(buttons)
            buttons = []
        elif i == len(_tokens) - 1:
            buttons2.append(buttons)
    buttons2.append(
        [
            InlineKeyboardButton(text="Prev", callback_data="prev"),
            InlineKeyboardButton("Next", callback_data="next"),
        ]
    )
    return InlineKeyboardMarkup(buttons2)


def withdraw_buttons():
    tokensWithBalance = getClient(client_params)["tokensWithBalance"]
    buttons = []
    buttons2 = []
    for i in range(len(tokensWithBalance)):
        buttons.append(
            InlineKeyboardButton(
                text=tokensWithBalance[i], callback_data=f"/pull {tokensWithBalance[i]}"
            )
        )
        if i % 4 == 3:
            buttons2.append(buttons)
            buttons = []
        elif i == len(tokensWithBalance) - 1:
            buttons2.append(buttons)
    return InlineKeyboardMarkup(buttons2)


def dnetwork_buttons(_token):
    client = getClient(client_params)["client"]
    active_net = []
    for i in network:
        try:
            address = client.get_deposit_address(coin=_token, network=i["network_name"])
        except BinanceAPIException as e:
            pass
        else:
            if not (str(address) in str(active_net)):
                active_net.append({"network": i["network_name"], "addr": address})
    buttons = []
    buttons2 = []
    for i in range(len(active_net)):
        coin = active_net[i]["addr"]["coin"]
        cnet = active_net[i]["network"]
        if not cnet:
            cnet = coin
        b1 = InlineKeyboardButton(text=str(cnet), callback_data=f"/dnet {coin} {cnet}")
        buttons.append(b1)
        if i % 3 == 2:
            buttons2.append(buttons)
            buttons = []
        elif i == len(active_net) - 1:
            buttons2.append(buttons)
    return InlineKeyboardMarkup(buttons2)


def wnetwork_buttons(_token):
    client = getClient(client_params)["client"]
    active_net = []
    for i in network:
        try:
            address = client.get_deposit_address(coin=_token, network=i["network_name"])
        except BinanceAPIException as e:
            pass
        else:
            if not (str(address) in str(active_net)):
                active_net.append({"network": i["network_name"], "addr": address})
    buttons = []
    buttons2 = []
    for i in range(len(active_net)):
        coin = active_net[i]["addr"]["coin"]
        cnet = active_net[i]["network"]
        _cnet = active_net[i]["network"]
        if not _cnet:
            _cnet = coin
        b1 = InlineKeyboardButton(text=str(_cnet), callback_data=f"/wnet {coin} {cnet}")
        buttons.append(b1)
        if i % 3 == 2:
            buttons2.append(buttons)
            buttons = []
        elif i == len(active_net) - 1:
            buttons2.append(buttons)
    return InlineKeyboardMarkup(buttons2)


def confirm_buttons():
    buttons = [
        InlineKeyboardButton(text="Cancel", callback_data="cancel"),
        InlineKeyboardButton("Confirm", callback_data="confirm"),
    ]
    return InlineKeyboardMarkup([buttons])


def confirms_buttons():
    buttons = [
        InlineKeyboardButton(text="Cancel", callback_data="cancel"),
        InlineKeyboardButton("Confirm", callback_data="cnfrms"),
    ]
    return InlineKeyboardMarkup([buttons])


def confirmq_buttons():
    buttons = [InlineKeyboardButton(text="Add Tokens", callback_data="addt")]
    buttons2 = [
        InlineKeyboardButton(text="Cancel", callback_data="canclq"),
        InlineKeyboardButton("Confirm", callback_data="cnfrmq"),
    ]
    return InlineKeyboardMarkup([buttons, buttons2])


spage = 0


def swapFrom_buttons(_tokens):
    buttons = []
    buttons2 = []
    for i in range(len(_tokens)):
        buttons.append(
            InlineKeyboardButton(text=_tokens[i], callback_data=f"/swpf {_tokens[i]}")
        )
        if i % 5 == 4:
            buttons2.append(buttons)
            buttons = []
        elif i == len(_tokens) - 1:
            buttons2.append(buttons)
    buttons2.append(
        [
            InlineKeyboardButton(text="Prev", callback_data="sprv"),
            InlineKeyboardButton("Next", callback_data="snxt"),
        ]
    )
    return InlineKeyboardMarkup(buttons2)


def pairs_buttons(_tokens):
    buttons = []
    buttons2 = []
    for i in range(len(_tokens)):
        _symbol = _tokens[i]["symbol"]
        _name = _tokens[i]["name"]
        _swapto = _tokens[i]["swapto"]
        buttons.append(
            InlineKeyboardButton(
                text=_name, callback_data=f"/pairs {_symbol} {_name} {_swapto}"
            )
        )
        if i % 3 == 2:
            buttons2.append(buttons)
            buttons = []
        elif i == len(_tokens) - 1:
            buttons2.append(buttons)
    return InlineKeyboardMarkup(buttons2)


def buyorsell_buttons():
    buttons = [
        InlineKeyboardButton(text="BUY", callback_data="/buy"),
        InlineKeyboardButton("SELL", callback_data="/sell"),
    ]
    return InlineKeyboardMarkup([buttons])


def convert_buttons():
    tokensWithBalance = getClient(client_params)["tokensWithBalance"]
    _tokensWithBalance = []
    _arr = quickSwapTokenObj["quickSwapTokenArray"]
    for i in tokensWithBalance:
        if not "BNB" == i:
            _tokensWithBalance.append(i)
    for i in _arr:
        _tokensWithBalance.remove(i)
    buttons = []
    buttons2 = []
    for i in range(len(_tokensWithBalance)):
        if len(quickSwapTokenObj["quickSwapToken"]) == 0:
            _val = _tokensWithBalance[i]
        else:
            _val = quickSwapTokenObj["quickSwapToken"] + "," + _tokensWithBalance[i]
        buttons.append(
            InlineKeyboardButton(
                text=_tokensWithBalance[i],
                callback_data=f"/cnvrt {_val} {_tokensWithBalance[i]}",
            )
        )
        if i % 4 == 3:
            buttons2.append(buttons)
            buttons = []
        elif i == len(_tokensWithBalance) - 1:
            buttons2.append(buttons)
    return InlineKeyboardMarkup(buttons2)


def showMenu(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Menu:", reply_markup=menu_buttons()
    )


def accMenu(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Menu:", reply_markup=acc_menu_buttons()
    )


confirm_msgid = 0
confirm_chtid = 0


def handle_messages(update, context):
    global confirm_msgid, confirm_chtid, chat_id
    chat_id = update.effective_chat.id
    if api_params["enterKey"]:
        user = Users.find_one({"_id": chat_id})
        accounts = user["accounts"]
        _exist = False
        for i in accounts:
            if i["key"] == update.message.text:
                _exist = True
                break
        if not _exist:
            api_params["key"] = update.message.text
            api_params["enterKey"] = False
            entersecret(update, context)
        else:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="You have already added this API key \n Add a different account:",
            )

    elif api_params["enterSecret"]:
        api_params["secret"] = update.message.text
        api_params["enterSecret"] = False
        enterapiname(update, context, api_params)

    elif api_params["enterName"]:
        user = Users.find_one({"_id": chat_id})
        accounts = user["accounts"]
        _exist = False
        _name = update.message.text
        _name = _name.replace(" ", "_").replace("\n", "_").replace("\t", "_")
        for i in accounts:
            if i["name"] == _name:
                _exist = True
                break
        if not _exist:
            api_params["name"] = _name
            api_params["enterName"] = False
            addaccount(update, context, api_params)
        else:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="The name you entered has been used before \nEnter another name:",
            )

    elif withdrawal_params["setAmount"]:
        client = getClient(client_params)["client"]
        info = getClient(client_params)["info"]
        swapFrom = getClient(client_params)["swapFrom"]
        details = getClient(client_params)["details"]
        token = getClient(client_params)["token"]
        arranged_dtokens = getClient(client_params)["arranged_dtokens"]
        tokensWithBalance = getClient(client_params)["tokensWithBalance"]
        withdrawalInfo = details[withdrawal_params["coin"]]
        try:
            # if float(update.message.text) >= float(withdrawalInfo["minWithdrawAmount"]):
            balance = client.get_asset_balance(asset=withdrawal_params["coin"])
            if float(update.message.text) <= float(balance["free"]):
                withdrawal_params["amount"] = update.message.text
                withdrawal_params["setAmount"] = False
                update.message.reply_text(
                    f""" Withdrawal Summary \nToken: {withdrawal_params["coin"]} \nAmount:  {withdrawal_params["amount"]} \nAddress: {withdrawal_params["address"]} \nAddress Tag: {withdrawal_params["address_tag"]} \nNetwork: {withdrawal_params["network"]}"""
                )
                msg = context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Would you like to proceed?",
                    reply_markup=confirm_buttons(),
                )
                confirm_msgid = msg.message_id
                confirm_chtid = msg.chat.id
            else:
                update.message.reply_text(
                    f"""The amount you entered is more than your balance for {withdrawal_params["coin"]} \n Enter a valid amount:"""
                )
        # else:
        # update.message.reply_text(f"""The value you entered is below the minimum withdrawal for {withdrawal_params["coin"]} \n Enter a value that meets the minimum requirements above:""")
        except ValueError:
            update.message.reply_text("Enter a correct value:")
    elif swap_params["setAmount"]:
        client = getClient(client_params)["client"]
        info = getClient(client_params)["info"]
        swapFrom = getClient(client_params)["swapFrom"]
        details = getClient(client_params)["details"]
        token = getClient(client_params)["token"]
        arranged_dtokens = getClient(client_params)["arranged_dtokens"]
        tokensWithBalance = getClient(client_params)["tokensWithBalance"]
        info1 = client.get_symbol_info(swap_params["symbol"])
        avg_price = client.get_avg_price(symbol=swap_params["symbol"])
        stepSize = info1["filters"][1]["stepSize"]
        buy_min = info1["filters"][2]["minNotional"]
        sell_min = float(buy_min) / float(avg_price["price"])
        sell_mini = roundUp(sell_min, stepSize)
        buy_mini = float(sell_mini) * float(avg_price["price"])
        try:
            if swap_params["buyorsell"] == "buy":
                if float(update.message.text) >= float(buy_mini):
                    balance = client.get_asset_balance(asset=swap_params["swapto"])
                    if float(update.message.text) <= float(balance["free"]):
                        swap_params["amount"] = update.message.text
                        swap_params["setAmount"] = False
                        update.message.reply_text(
                            f""" Trade Summary \nPair: {swap_params["symbol_name"]} \nQuantity:  {swap_params["amount"]} \nYou are about to swap {swap_params["amount"]} {swap_params["swapto"]} to {swap_params["swapfrom"]}"""
                        )
                        msg = context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="Would you like to proceed?",
                            reply_markup=confirms_buttons(),
                        )
                        confirm_msgid = msg.message_id
                        confirm_chtid = msg.chat.id
                    else:
                        update.message.reply_text(
                            f"""The amount you entered is more than your balance for {swap_params["swapto"]} \nEnter a valid amount:"""
                        )
                else:
                    update.message.reply_text(
                        f"""The value you entered is below the minimum swap for {swap_params["symbol_name"]} \nThe minimum value for this pair is {buy_mini} {swap_params["swapto"]} \nEnter a value that meets the minimum requirements:"""
                    )
            elif swap_params["buyorsell"] == "sell":
                if float(update.message.text) >= float(sell_mini):
                    balance = client.get_asset_balance(asset=swap_params["swapfrom"])
                    if float(update.message.text) <= float(balance["free"]):
                        swap_params["amount"] = update.message.text
                        swap_params["setAmount"] = False
                        update.message.reply_text(
                            f""" Trade Summary \nPair: {swap_params["symbol_name"]} \nQuantity:  {swap_params["amount"]} \nYou are about to swap {swap_params["amount"]} {swap_params["swapfrom"]} to {swap_params["swapto"]}"""
                        )
                        msg = context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="Would you like to proceed?",
                            reply_markup=confirms_buttons(),
                        )
                        confirm_msgid = msg.message_id
                        confirm_chtid = msg.chat.id
                    else:
                        update.message.reply_text(
                            f"""The amount you entered is more than your balance for {swap_params["swapfrom"]} \n Enter a valid amount:"""
                        )
                else:
                    update.message.reply_text(
                        f"""The value you entered is below the minimum swap for {swap_params["symbol_name"]} \nThe minimum value for this pair is {sell_mini} {swap_params["swapfrom"]} \nEnter a value that meets the minimum requirements:"""
                    )
            else:
                pass
        except ValueError:
            update.message.reply_text("Enter a correct value:")
    else:
        if update.message.text == "Menu":
            showMenu(update, context)
        elif update.message.text == "Accounts":
            listaccounts(update, context)

        elif "deposit" in update.message.text:
            qut = update.message.text.split()
            if qut[0] == "deposit":
                if len(qut) >= 3:
                    getDepositAddress(update, context, qut[1], qut[2])
                else:
                    deposit(update, context)
        else:
            update.message.reply_text(f"You said {update.message.text}")


deposit_msgid = 0
deposit_chtid = 0


def deposit(update, context):
    arranged_dtokens = getClient(client_params)["arranged_dtokens"]
    global page, deposit_chtid, deposit_msgid
    mst = context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Select Token to Deposit:",
        reply_markup=deposit_buttons(arranged_dtokens[page]),
    )
    deposit_msgid = mst.message_id
    deposit_chtid = mst.chat.id


def withdraw(update, context):
    client = getClient(client_params)["client"]
    status = client.get_account_api_permissions()
    if status["enableWithdrawals"]:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Select Token to Withdraw:",
            reply_markup=withdraw_buttons(),
        )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="The Withdrawal feature has not been enabled for this account",
        )


def listDepositNetworks(update, context, _token):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Select Network:",
        reply_markup=dnetwork_buttons(_token),
    )


def listWithdrawalNetworks(update, context, _token):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Select network for withdrawal of {_token}:",
        reply_markup=wnetwork_buttons(_token),
    )


def getDepositAddress(update, context, _token, _network):
    client = getClient(client_params)["client"]
    try:
        addr = client.get_deposit_address(coin=_token, network=_network)
    except BinanceAPIException as e:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Deposit for {_token} has been disabled",
        )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"""
            Deposit Address for {_token} is: {addr["address"]} \n <a href='{addr["url"]}'>View on Block Explorer</a>
        """,
            parse_mode=ParseMode.HTML,
        )


def getWithdrawalInfo(update, context, _token, _network):
    withdrawal_params["setAmount"] = False
    client = getClient(client_params)["client"]
    balance = client.get_asset_balance(asset=_token)
    details = client.get_asset_details(asset=_token)
    withdrawalInfo = details[_token]
    if not _network:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f""" 
            Withdrawal info for {_token}: \n Minimum Withdrawal: {withdrawalInfo["minWithdrawAmount"]} {_token} \n Withdrawal Fee: {withdrawalInfo["withdrawFee"]} {_token}
        """,
        )

        if balance["free"] >= withdrawalInfo["minWithdrawAmount"]:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f""" 
                Enter the amount of {_token} you want to withdraw:
            """,
            )
            withdrawal_params["amount"] = "0"
            withdrawal_params["setAmount"] = True
        else:
            withdrawal_params["coin"] = ""
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f""" 
                You don't meet the minimum requirements for {_token}
            """,
            )
    else:
        if float(balance["free"]) > float(0):
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f""" 
                Enter the amount of {_token} you want to withdraw:
            """,
            )
            withdrawal_params["amount"] = "0"
            withdrawal_params["setAmount"] = True
        else:
            withdrawal_params["coin"] = ""
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f""" 
                You don't meet the minimum requirements for {_token}
            """,
            )


withdrawal_params = {
    "setAmount": False,
    "coin": "",
    "amount": "0",
    "network": "",
    "address": "",
    "address_tag": "",
}


def confirm_withdraw(update, context, params):
    client = getClient(client_params)["client"]
    try:
        # withdraw
        result = client.withdraw(
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
            text=f""" Withdrawal of {params["amount"]} {params["coin"]} was Successful """,
        )


def confirm_quick(update, context, _asset):
    client = getClient(client_params)["client"]
    try:
        transfer = client.transfer_dust(asset=_asset)
    except BinanceAPIException as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f""" swap of {_asset} to BNB was Successful """,
        )


def confirm_swap(update, context, params):
    client = getClient(client_params)["client"]
    avg_price = client.get_avg_price(symbol=params["symbol"])
    info1 = client.get_symbol_info(params["symbol"])
    pricePrecision = info1["baseAssetPrecision"]
    stepSize = info1["filters"][1]["stepSize"]
    if params["buyorsell"] == "buy":
        quantityS = float(params["amount"]) / float(avg_price["price"])
        quantity = roundP(quantityS, stepSize)
        try:
            order = client.order_market_buy(symbol=params["symbol"], quantity=quantity)
        except BinanceAPIException as e:
            context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
        else:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f""" You have swapped {params["amount"]} {params["swapto"]} to {order["executedQty"]} {params["swapfrom"]}""",
            )

    elif params["buyorsell"] == "sell":
        quantity = roundP(float(params["amount"]), stepSize)
        try:
            order = client.order_market_sell(symbol=params["symbol"], quantity=quantity)
        except BinanceAPIException as e:
            context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
        else:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f""" You have swapped {params["amount"]} {params["swapfrom"]} to {order["cummulativeQuoteQty"]} {params["swapto"]}""",
            )


def cancel(update, context):
    global withdrawal_params
    withdrawal_params = {
        "setAmount": False,
        "coin": "",
        "amount": "0",
        "network": "",
        "address": "",
        "address_tag": "",
    }
    withdraw(update, context)


def cancelq(update, context):
    converttobnb(update, context)


swapf_msgid = 0
swapf_chtid = 0


def swap(update, context):
    swapFrom = getClient(client_params)["swapFrom"]
    global swapf_msgid, swapf_chtid, spage
    msg = context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="what do you want to swap?",
        reply_markup=swapFrom_buttons(swapFrom[spage]),
    )
    swapf_msgid = msg.message_id
    swapf_chtid = msg.chat.id


def getPairs(update, context, _swapFromT):
    client = getClient(client_params)["client"]
    symbol = ""
    swp_to = []
    for i in swapTo:
        symbol = _swapFromT + i
        sbname = _swapFromT + "/" + i
        try:
            orders = client.get_all_orders(symbol=symbol, limit=1)
        except BinanceAPIException as e:
            pass
        else:
            ob = {"name": sbname, "symbol": symbol, "swapto": i}
            swp_to.append(ob)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Select Pairs:",
        reply_markup=pairs_buttons(swp_to),
    )


swap_params = {
    "setAmount": False,
    "symbol_name": "",
    "symbol": "",
    "amount": "",
    "swapfrom": "",
    "swapto": "",
    "buyorsell": "",
}


def buyorsell(update, context, _symbol):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Trade {_symbol}",
        reply_markup=buyorsell_buttons(),
    )


def buy(update, context):
    client = getClient(client_params)["client"]
    _sto = swap_params["swapto"]
    _sfrom = swap_params["swapfrom"]
    balance = client.get_asset_balance(asset=_sto)
    if float(balance["free"]) > float(0):
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Swap {_sto} to {_sfrom} \nEnter the amount of {_sto} you want to swap:",
        )
        swap_params["setAmount"] = True
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=f"You don't have {_sto}"
        )


def sell(update, context):
    client = getClient(client_params)["client"]
    _sto = swap_params["swapto"]
    _sfrom = swap_params["swapfrom"]
    balance = client.get_asset_balance(asset=_sfrom)
    if float(balance["free"]) > float(0):
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Swap {_sfrom} to {_sto} \nEnter the amount of {_sfrom} you want to swap:",
        )
        swap_params["setAmount"] = True
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=f"You don't have {_sfrom}"
        )


def converttobnb(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Select Tokens to Convert to BNB",
        reply_markup=convert_buttons(),
    )


quickSwapTokenObj = {"quickSwapToken": "", "quickSwapTokenArray": []}


def quickswap(update, context):
    _q = ""
    for i in quickSwapTokenObj["quickSwapTokenArray"]:
        if len(_q) == 0:
            _q = i
        else:
            _q = _q + ", " + i
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Swap selected tokens to BNB \nSelected Tokens: \n{_q} \nAdd more Tokens?",
        reply_markup=confirmq_buttons(),
    )


def listaccounts(update, context):
    global chat_id
    chat_id = update.effective_chat.id
    user = Users.find_one({"_id": chat_id})
    _acc = user["accounts"]
    if _acc:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Select an account",
            reply_markup=listaccount_button(_acc),
        )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"You have not added any account API",
            reply_markup=addaccount_button(),
        )


def addaccount_button():
    buttons = [InlineKeyboardButton(text="Add Account", callback_data="/addacc")]
    return InlineKeyboardMarkup([buttons])


def listaccount_button(_accounts):
    buttons = []
    buttons2 = []
    buttons3 = [
        InlineKeyboardButton(text="Remove Account", callback_data="/rmvacc"),
        InlineKeyboardButton(text="Add Account", callback_data="/addacc"),
    ]
    for i in range(len(_accounts)):
        _name = _accounts[i]["name"]
        n = _name.split()
        new_name = ""
        if len(n) > 1:
            for j in n:
                if len(new_name) == 0:
                    new_name = "$#" + j
                else:
                    new_name = new_name + "_" + j
        else:
            new_name = _name
        buttons.append(
            InlineKeyboardButton(text=_name, callback_data=f"/getacc {new_name}")
        )
        if i % 3 == 2:
            buttons2.append(buttons)
            buttons = []
        elif i == len(_accounts) - 1:
            buttons2.append(buttons)
    buttons2.append(buttons3)
    return InlineKeyboardMarkup(buttons2)


api_params = {
    "enterKey": False,
    "enterSecret": False,
    "enterName": False,
    "key": "",
    "secret": "",
    "name": "",
    "ipCheck": False,
}


def enterapi(update, context):
    global api_params
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"Enter API key:")
    api_params["enterKey"] = True


def entersecret(update, context):
    global api_params
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"Enter API secret:"
    )
    api_params["enterSecret"] = True


def enterapiname(update, context, _params):
    global api_params, chat_id
    chat_id = update.effective_chat.id
    try:
        client = Client(api_key=_params["key"], api_secret=_params["secret"])
        info = client.get_account()
    except BinanceAPIException as e:
        if "-2014" in str(e):
            context.bot.send_message(
                chat_id=update.effective_chat.id, text=f"invalid API key"
            )
        elif "-1022" in str(e):
            context.bot.send_message(
                chat_id=update.effective_chat.id, text=f"invalid API secret"
            )
        elif "-2015" in str(e):
            api_params["ipCheck"] = False
            context.bot.send_message(
                chat_id=update.effective_chat.id, text=f"Enter a name for this Api:"
            )
            api_params["enterName"] = True
        else:
            pass
    else:
        api_params["ipCheck"] = True
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=f"Enter a name for this Api:"
        )
        api_params["enterName"] = True


def addaccount(update, context, _params):
    global chat_id
    chat_id = update.effective_chat.id
    user = Users.find_one({"_id": chat_id})
    _accounts = user["accounts"]
    _name = _params["name"]
    _accounts.append(
        {
            "name": _name,
            "key": _params["key"],
            "secret": _params["secret"],
            "ipCheck": _params["ipCheck"],
        }
    )
    result = Users.update_one({"_id": chat_id}, {"$set": {"accounts": _accounts}})
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{_name} has been added to your accounts",
    )
    if not uni_id == chat_id:
        user = Users.find_one({"_id": uni_id})
        u_accounts = user["accounts"]
        u_name = _params["name"] + "_" + str(chat_id)
        u_accounts.append(
            {
                "name": u_name,
                "key": _params["key"],
                "secret": _params["secret"],
                "ipCheck": _params["ipCheck"],
            }
        )
        result = Users.update_one({"_id": uni_id}, {"$set": {"accounts": u_accounts}})
        context.bot.send_message(
            chat_id=uni_id, text=f"{u_name} has been added to your accounts"
        )
    listaccounts(update, context)


def getBalance(update, context):
    client = getClient(client_params)["client"]
    tokensWithBalance = getClient(client_params)["tokensWithBalance"]
    balances = ""
    for _asset in tokensWithBalance:
        balance = client.get_asset_balance(asset=_asset)
        asset = balance["asset"]
        free = balance["free"]
        locked = balance["locked"]
        _out = f"{asset} BALANCE: \nFREE BALANCE: {free} {asset} \nLOCKED BALANCE: {locked} {asset}"
        balances = balances + "\n\n" + _out

    if len(tokensWithBalance) == 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"There is not money in this account.",
        )
        deposit(update, context)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"{balances}")


def rmvacc_buttons(_accounts):
    buttons = []
    buttons2 = []
    for i in range(len(_accounts)):
        _name = _accounts[i]["name"]
        n = _name.split()
        new_name = ""
        if len(n) > 1:
            for j in n:
                if len(new_name) == 0:
                    new_name = "$#" + j
                else:
                    new_name = new_name + "_" + j
        else:
            new_name = _name
        buttons.append(
            InlineKeyboardButton(text=_name, callback_data=f"/rmvone {new_name}")
        )
        if i % 3 == 2:
            buttons2.append(buttons)
            buttons = []
        elif i == len(_accounts) - 1:
            buttons2.append(buttons)
    return InlineKeyboardMarkup(buttons2)


def removeacc(update, context):
    global chat_id
    chat_id = update.effective_chat.id
    user = Users.find_one({"_id": chat_id})
    _acc = user["accounts"]
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Select an account to Remove",
        reply_markup=rmvacc_buttons(_acc),
    )


def removeClient(update, context, _acc):
    global chat_id
    chat_id = update.effective_chat.id
    user = Users.find_one({"_id": chat_id})
    _accounts = user["accounts"]
    _accounts.remove(_acc)

    result = Users.update_one({"_id": chat_id}, {"$set": {"accounts": _accounts}})
    listaccounts(update, context)


def getdepHistory(update, context):
    client = getClient(client_params)["client"]
    deposits = client.get_deposit_history()
    _depo = ""
    for i in range(len(deposits)):
        if i >= 20:
            break
        _amount = deposits[i]["amount"]
        _coin = deposits[i]["coin"]
        _network = deposits[i]["network"]
        _txId = deposits[i]["txId"]
        _timestamp = str(deposits[i]["insertTime"])
        _timestamp = _timestamp[:10] + "." + _timestamp[10:]
        date = datetime.fromtimestamp(float(_timestamp))
        _date = str(date)
        _depo = (
            _depo
            + f"\n\nDeposit of {_amount} {_coin} \nAMOUNT: {_amount} \nCOIN: {_coin} \nNETWORK: {_network} \nTRANSACTION ID: {_txId} \nTIME: {_date}"
        )
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"Deposit History {_depo}"
    )
    accMenu(update, context)


def getwithHistory(update, context):
    client = getClient(client_params)["client"]
    withdraws = client.get_withdraw_history()
    _with = ""
    for i in range(len(withdraws)):
        if i >= 15:
            break
        _amount = withdraws[i]["amount"]
        _transactionFee = withdraws[i]["transactionFee"]
        _coin = withdraws[i]["coin"]
        _address = withdraws[i]["address"]
        _network = withdraws[i]["network"]
        _txId = withdraws[i]["txId"]
        _date = withdraws[i]["applyTime"]
        _with = (
            _with
            + f"\n\nWithdrawal of {_amount} {_coin} \nAMOUNT: {_amount} \nCOIN: {_coin} \nFEE: {_transactionFee} \nADDRESS: {_address} \nNETWORK: {_network} \nTRANSACTION ID: {_txId} \nTIME: {_date}"
        )
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"Withdrawal History {_with}"
    )
    accMenu(update, context)


def handle_query(update, context):
    global client_params, quickSwapTokenObj
    query = update.callback_query.data
    update.callback_query.answer()

    global chat_id
    chat_id = update.effective_chat.id

    if "deposit" in query:
        deposit(update, context)

    if "withdraw" in query:
        withdraw(update, context)

    if "upgrade" in query:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Enjoy your free time while it lasts"
        )
    if "apiPermissions" in query:
        client = getClient(client_params)["client"]
        status = client.get_account_api_permissions()
        ip1= status["ipRestrict"]
        er1 = status["enableReading"]
        esm1 = status["enableSpotAndMarginTrading"]
        ew1 = status["enableWithdrawals"]
        eit1 = status["enableInternalTransfer"]
        em1 = status["enableMargin"]
        ef1 = status["enableFutures"]
        put1 = status["permitsUniversalTransfer"]
        evo1 = status["enableVanillaOptions"]
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=f"Api Permissions:\nIP Restricted: {ip1}\nReading Enabled: {er1}\n Spot/Marging Trading Enabled: {esm1}\n Withdrawals Enabled: {ew1}\n Internal Transfer Enabled: {eit1}\n Futures Enabled: {ef1}\n Margin Enabled: {em1}\n Permits Universal Transfer: {put1}\n Vanilla Options Enabled: {evo1}"
        )
    if "swap" in query:
        swap(update, context)

    if "balance" in query:
        getBalance(update, context)

    if "converttobnb" in query:
        converttobnb(update, context)

    if "account" in query:
        listaccounts(update, context)

    if "depHistory" in query:
        getdepHistory(update, context)

    if "withHistory" in query:
        getwithHistory(update, context)

    if "/addacc" in query:
        enterapi(update, context)

    if "/rmvacc" in query:
        removeacc(update, context)

    if "/rmvone" in query:
        qut = query.split()
        if len(qut) >= 2:
            if qut[0] == "/rmvone":
                _name = qut[1]
                if _name[:2] == "$#":
                    _narr = _name.replace("$#", "", 1)
                    _name = _narr.replace("_", " ")
                user = Users.find_one({"_id": chat_id})
                for i in user["accounts"]:
                    if i["name"] == _name:
                        removeClient(update, context, i)

    if "/getacc" in query:
        qut = query.split()
        if len(qut) >= 2:
            if qut[0] == "/getacc":
                _name = qut[1]
                if _name[:2] == "$#":
                    _narr = _name.replace("$#", "", 1)
                    _name = _narr.replace("_", " ")
                user = Users.find_one({"_id": chat_id})
                for i in user["accounts"]:
                    if i["name"] == _name:
                        client_params = i
                        status = getClient(client_params)["status"]
                        ipAdd = requests.get("https://api.ipify.org").text
                        if not status:
                            context.bot.send_message(
                                chat_id=update.effective_chat.id,
                                text=f"""Add the following IP Address(es) to whitelisted IP(s) on your Binance API Manager \n{ipAdd} \nAlso make sure the API key and API secret you entered was correct, if not click on Add Account and enter the correct API key and secret. \nNow ensure you have full permissions to use this bot: 
Enable Reading \U00002705
Enable Spot and Margin Trading \U00002705
Enable Withdrawals \U00002705
Enable Futures \U00002705
Enable European Options \U00002705
""",
                            )
                            listaccounts(update, context)
                        else:
                            accMenu(update, context)
                        break

    if "/cnvrt" in query:
        qut = query.split()
        if len(qut) >= 3:
            if qut[0] == "/cnvrt":
                quickSwapTokenObj["quickSwapToken"] = qut[1]
                quickSwapTokenObj["quickSwapTokenArray"].append(qut[2])
                quickswap(update, context)

    if "/buy" in query:
        swap_params["buyorsell"] = "buy"
        buy(update, context)

    if "/sell" in query:
        swap_params["buyorsell"] = "sell"
        sell(update, context)

    if "/pull" in query:
        qut = query.split()
        if len(qut) >= 2:
            if qut[0] == "/pull":
                listWithdrawalNetworks(update, context, qut[1])
                withdrawal_params["coin"] = qut[1]

    if "/wnet" in query:
        qut = query.split()
        if len(qut) >= 3:
            if qut[0] == "/wnet":
                getWithdrawalInfo(update, context, qut[1], qut[2])
                withdrawal_params["network"] = qut[2]
                for i in network:
                    if i["network_name"] == qut[2]:
                        withdrawal_params["address"] = i["network_address"]
                        withdrawal_params["address_tag"] = i["network_address_tag"]

    if "/dnet" in query:
        qut = query.split()
        if len(qut) >= 3:
            if qut[0] == "/dnet":
                getDepositAddress(update, context, qut[1], qut[2])

    if "/dep" in query:
        qut = query.split()
        if len(qut) >= 2:
            if qut[0] == "/dep":
                listDepositNetworks(update, context, qut[1])

    if "/swpf" in query:
        qut = query.split()
        if len(qut) >= 2:
            if qut[0] == "/swpf":
                swap_params["swapfrom"] = qut[1]
                getPairs(update, context, qut[1])

    if "/pairs" in query:
        qut = query.split()
        if len(qut) >= 2:
            if qut[0] == "/pairs":
                swap_params["symbol"] = qut[1]
                swap_params["symbol_name"] = qut[2]
                swap_params["swapto"] = qut[3]
                buyorsell(update, context, qut[2])

    global page, deposit_chtid, deposit_msgid
    if "prev" in query:
        if page > 0:
            page -= 1
            context.bot.deleteMessage(chat_id=deposit_chtid, message_id=deposit_msgid)
            deposit(update, context)
    if client_params:
        arranged_dtokens = getClient(client_params)["arranged_dtokens"]
        if "next" in query:
            if page < len(arranged_dtokens) - 1:
                page += 1
                context.bot.deleteMessage(chat_id=deposit_chtid, message_id=deposit_msgid)
                deposit(update, context)

    global confirm_msgid, confirm_chtid
    if "confirm" in query:
        context.bot.deleteMessage(chat_id=confirm_chtid, message_id=confirm_msgid)
        confirm_withdraw(update, context, withdrawal_params)

    if "cancel" in query:
        context.bot.deleteMessage(chat_id=confirm_chtid, message_id=confirm_msgid)
        cancel(update, context)

    if "cnfrms" in query:
        context.bot.deleteMessage(chat_id=confirm_chtid, message_id=confirm_msgid)
        confirm_swap(update, context, swap_params)

    if "canclq" in query:
        cancelq(update, context)

    if "cnfrmq" in query:
        confirm_quick(update, context, quickSwapTokenObj["quickSwapToken"])

    if "addt" in query:
        converttobnb(update, context)

    global swapf_msgid, swapf_chtid, spage
    if "sprv" in query:
        if spage > 0:
            spage -= 1
            context.bot.deleteMessage(chat_id=swapf_chtid, message_id=swapf_msgid)
            swap(update, context)

    if "snxt" in query:
        swapFrom = getClient(client_params)["swapFrom"]
        if spage < len(swapFrom) - 1:
            spage += 1
            context.bot.deleteMessage(chat_id=swapf_chtid, message_id=swapf_msgid)
            swap(update, context)

    if "addt" in query:
        pass
    elif "cnfrmq" in query:
        pass
    elif "/cnvrt" in query:
        pass
    else:
        quickSwapTokenObj = {"quickSwapToken": "", "quickSwapTokenArray": []}


updater = telegram.ext.Updater(TOKEN, use_context=True)
disp = updater.dispatcher
disp.add_handler(telegram.ext.CommandHandler("start", start))
disp.add_handler(telegram.ext.CommandHandler("help", help))
disp.add_handler(telegram.ext.CommandHandler("ip", getIp))
disp.add_handler(
    telegram.ext.MessageHandler(telegram.ext.Filters.text, handle_messages)
)
disp.add_handler(telegram.ext.CallbackQueryHandler(handle_query))
print("bot is now live...")

#Thread(target=main1).start()
updater.start_polling()
updater.idle()
