import requests
import json
import yaml
import datetime
import time

# config
with open("config.yaml", encoding="UTF-8") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)
    
APP_KEY = cfg["APP_KEY"]
APP_SECRET = cfg["APP_SECRET"]
ACCESS_TOKEN = ""
CANO = cfg["CANO"]
ACNT_PRDT_CD = cfg["ACNT_PRDT_CD"]
URL_BASE = cfg["URL_BASE"]

def accessToken():
    PATH = "oauth2/tokenP"
    URL = f"{URL_BASE}/{PATH}"
    headers = {
        "content-type": "application/json"
        }
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
        }
    res = requests.post(URL, headers=headers, data=json.dumps(body))
    ACCESS_TOKEN = res.json()["access_token"]
    
    return ACCESS_TOKEN

def hashKey(datas):
    PATH = "uapi/hashkey"
    URL = f"{URL_BASE}/{PATH}"
    headers = {
        "content-type": "application/json",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
        }
    res = requests.post(URL, headers=headers, data=json.dumps(datas))
    hashkey = res.json()["HASH"]
    
    return hashkey

def currentPrice(ACCESS_TOKEN, ticker):
    PATH = "uapi/domestic-stock/v1/quotations/inquire-price"
    URL = f"{URL_BASE}/{PATH}"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01010100"
        }
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": ticker
    }
    res = requests.get(URL, headers=headers, params=params)
    current_price = res.json()["output"]["stck_prpr"]
    
    return current_price

def buyTicker(ACCESS_TOKEN, ticker, amount, price, type="limit"):
    PATH = "uapi/domestic-stock/v1/trading/order-cash"
    URL = f"{URL_BASE}/{PATH}"

    data = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "PDNO": ticker, # 종목
        "ORD_DVSN": "01",
        "ORD_QTY": amount, # 수량
        "ORD_UNPR": "0", # 시장가 주문
        }
    
    if type == "limit":
        data["ORD_DVSN"] = "00"
        data["ORD_UNPR"] = price
    elif type == "market":
        data["ORD_UNPR"] = "0"

    headers = {
        "content-type": "application/json", 
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "VTTC0802U",
        "custtype": "P",
        "hashkey" : hashKey(data)
        }
    res = requests.post(URL, headers=headers, data=json.dumps(data))
    KRX_FWDG_ORD_ORGNO = res.json()["output"]["KRX_FWDG_ORD_ORGNO"]
    ODNO = res.json()["output"]["ODNO"]
    
    return KRX_FWDG_ORD_ORGNO, ODNO