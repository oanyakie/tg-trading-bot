import asyncio
from binance import Client, AsyncClient, BinanceSocketManager
from binance.exceptions import BinanceAPIException
from threading import Thread, Timer
from telegram import *
from pymongo import *
import telegram.ext

with open("botapi.txt", "r") as f:
    TOKEN = f.read()
updater = telegram.ext.Updater(TOKEN, use_context=True)
with open("cluster.txt", "r") as f:
    cluster = f.read()
mdclient = MongoClient(cluster)
database = mdclient.binanceapi
Users = database.Users
all1 = Users.find()
params = []
p_v = []
p_n = []
for i in all1:
    for j in i["accounts"]:
        p = {"key": j["key"], "secret": j["secret"]}
        if not p in params:
            params.append(p)
for p in params:
    client = Client(api_key=p["key"], api_secret=p["secret"])
    try:
        status = client.get_account_api_permissions()
    except BinanceAPIException as e:
        p_n.append(p)
    else:
        p_v.append(p)


async def main(_params):
    api_key = _params["key"]
    api_secret = _params["secret"]
    client = await AsyncClient.create(api_key, api_secret, {"timeout": 10})
    bm = BinanceSocketManager(client)
    ts = bm.user_socket()
    async with ts as tscm:
        msg = []
        while True:
            res = await tscm.recv()
            msg.append(res)
            if res["e"] == "outboundAccountPosition":
                print(msg)
                all2 = Users.find()
                for i in all2:
                    for j in i["accounts"]:
                        if api_key == j["key"] and api_secret == j["secret"]:
                            _id = i["_id"]
                            _name = j["name"]
                            updt = []
                            acctp = []
                            for m in msg:
                                if m["e"] == "balanceUpdate":
                                    t1 = m["d"] + " " + m["a"]
                                    updt.append(t1)
                                elif m["e"] == "outboundAccountPosition":
                                    for b in m["B"]:
                                        t2 = b["f"] + " " + b["a"]
                                        acctp.append(t2)
                            if len(updt) >= 2 and len(acctp) >= 2:
                                updater.bot.send_message(
                                    chat_id=_id,
                                    text=f"Account Update for {_name} \nTransaction:\n {updt[0]} \n {updt[1]} \nAccount Balance:\n{acctp[0]} \n {acctp[1]}",
                                )
                            elif len(updt) == 1 and len(acctp) >= 2:
                                updater.bot.send_message(
                                    chat_id=_id,
                                    text=f"Account Update for {_name} \nTransaction:\n {updt[0]} \nAccount Balance:\n{acctp[0]} \n {acctp[1]}",
                                )
                            elif len(updt) >= 2 and len(acctp) == 1:
                                updater.bot.send_message(
                                    chat_id=_id,
                                    text=f"Account Update for {_name} \nTransaction:\n {updt[0]} \n {updt[1]} \nAccount Balance:\n{acctp[0]}",
                                )
                            elif len(updt) == 1 and len(acctp) == 1:
                                updater.bot.send_message(
                                    chat_id=_id,
                                    text=f"Account Update for {_name} \nTransaction:\n {updt[0]} \nAccount Balance:\n{acctp[0]}",
                                )
                            else:
                                pass
                msg = []
    await client.close_connection()


def t(_par):
    asyncio.run(main(_par))


def keepChecking():
    w = Users.watch()
    for i in w:
        user = Users.find_one(i["documentKey"])
        for j in user["accounts"]:
            p = {"key": j["key"], "secret": j["secret"]}
            if not p in params:
                params.append(p)
                Thread(target=t, args=[p]).start()


def timed():
    timer = Timer(20.0, timed)
    timer.start()
    for p in p_n:
        client = Client(api_key=p["key"], api_secret=p["secret"])
        try:
            status = client.get_account_api_permissions()
        except BinanceAPIException as e:
            pass
        else:
            p_n.remove(p)
            p_v.append(p)
            Thread(target=t, args=[p]).start()

def main1():
    for p in p_v:
        Thread(target=t, args=[p]).start()
    Thread(target=keepChecking).start()
    Thread(target=timed).start()

if __name__ == "__main__":
    main1()