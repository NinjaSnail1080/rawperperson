from flask import Flask, render_template
import requests

from decimal import Decimal, getcontext
import re
import threading
import time

getcontext().prec = 39

DATA = {}

app = Flask(__name__)


def update_population():
    while True:
        r = requests.get("https://www.theworldcounts.com/embed/challenges/8")
        pop_regex = re.compile(r"number_interval\([0-9.]*, [0-9.]*")
        pop_data = pop_regex.findall(r.text)[0].split(", ")
        DATA["population"] = round(float(pop_data[0][16:]))
        DATA["perperson"] = int(DATA["supply"]) // DATA["population"]
        DATA["perpersonusd"] = str(Decimal(int(DATA["supply"]) // DATA["population"]) / Decimal(10**30) * Decimal(DATA["price"]))
        DATA["interval"] = 1 / float(pop_data[1])

        DATA["last_reset"] = time.time()
        while (time.time() - DATA["last_reset"]) // 86400 <= 0: # Reset every 24 hours (86400 sec)
            time.sleep(DATA["interval"])
            DATA["population"] += 1
            DATA["perperson"] = int(DATA["supply"]) // DATA["population"]
            DATA["perpersonusd"] = str(Decimal(int(DATA["supply"]) // DATA["population"]) / Decimal(10**30) * Decimal(DATA["price"]))


def update_supply_and_price():
    while True:
        time.sleep(30)
        try:
            r = requests.post("https://nault.nanos.cc/proxy", json={"action": "price"})
            DATA["price"] = str(r.json()["quotes"]["USD"]["price"])
        except:
            try:
                r = requests.post("https://proxy.powernode.cc/proxy", json={"action": "price"})
                DATA["price"] = str(r.json()["quotes"]["USD"]["price"])
            except:
                r = requests.post("https://rainstorm.city/api", json={"action": "price"})
                DATA["price"] = str(r.json()["quotes"]["USD"]["price"])

        try:
            r = requests.post("https://mynano.ninja/api/node", json={"action": "available_supply"})
            DATA["supply"] = r.json()["available"]
            DATA["supply_nano"] = round(int(DATA['supply']) / 10**30)
        except:
            r = requests.get("https://node.shrynode.me/api?action=available_supply")
            DATA["supply"] = r.json()["available"]
            DATA["supply_nano"] = round(int(DATA['supply']) / 10**30)
        # Excess redundancy for the win


@app.before_first_request
def init():
    r = requests.post("https://nault.nanos.cc/proxy", json={"action": "price"})
    DATA["price"] = str(r.json()["quotes"]["USD"]["price"])

    r = requests.post("https://mynano.ninja/api/node", json={"action": "available_supply"})
    DATA["supply"] = r.json()["available"]
    DATA["supply_nano"] = round(int(DATA['supply']) / 10**30)

    threading.Thread(target=update_population).start()
    threading.Thread(target=update_supply_and_price).start()

    time.sleep(2) # Wait long enough for all neccesary values to appear in DATA


@app.route("/")
def index():
    return render_template(
        "index.html",
        perperson=f"{DATA['perperson']:,}",
        perpersonusd=round(Decimal(DATA['perpersonusd']), 4).normalize(),
        population=f"{DATA['population']:,}",
        supply=f"{DATA['supply_nano']:,}",
        price=f"{round(Decimal(DATA['price']), 2):,.2f}",
        price_data=DATA["price"],
        supply_data=DATA["supply"],
        pop_data=DATA["population"],
        interval=DATA["interval"],
    )


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/data")
def data():
    return DATA


@app.errorhandler(404)
def page_not_found(error):
    return render_template("page_not_found.html"), 404
