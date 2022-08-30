from winreg import EnumValue
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
DISCORD_WEBHOOK_URL = cfg['DISCORD_WEBHOOK_URL']

# 디스코드
def send_message(txt):
    now = datetime.datetime.now()
    msg = {
        "content": f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {str(txt)}"
    }
    requests.post(DISCORD_WEBHOOK_URL, data=msg)

# 토큰 발급
def get_access_token():
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

# 해쉬키 발급
def get_hashkey(datas):
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

# 주식잔고 조회
def get_stock_balance():
    PATH = "/uapi/domestic-stock/v1/trading/inquire-balance"
    URL = f"{URL_BASE}/{PATH}"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "VTTC8434R", # 모의투자, 실전투자(TTTC8434R)
        "custtype": "P"
    }
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "AFHR_FLPR_YN": "N",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }
    res = requests.get(URL, headers=headers, params=params)
    evaluation = res.json()['output2']
    send_message(f"주식 평가 금액: {evaluation[0]["scts_evlu_amt"]}")
    send_message(f"평가 손익: {evaluation[0]["evlu_pfls_smtl_amt"]}")
    send_message(f"총 평가 금액: {evaluation[0]["tot_evlu_amt"]}")
    return res.json()

# 현금잔고 조회
def get_cash_balance(ticker, current_price):
    PATH = "uapi/domestic-stock/v1/trading/inquire-psbl-order"
    URL = f"{URL_BASE}/{PATH}"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "VTTC8908R"
    }
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "PDNO": ticker,
        "ORD_UNPR": current_price,
        "ORD_DVSN": "01", # 시장가
        "CMA_EVLU_AMT_ICLD_YN": "N",
        "OVRS_ICLD_YN": "N"
    }
    res = requests.get(URL, headers=headers, params=params)
    cash = res.json()["output"]["ord_psbl_cash"]
    send_message(f"현금잔고: {cash} 원")
    return int(cash)

# 현재가 조회
def get_current_price(ACCESS_TOKEN, ticker):
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

# 종목 매수(시장가)
def buy_ticker(ticker, quantity):
    PATH = "uapi/domestic-stock/v1/trading/order-cash"
    URL = f"{URL_BASE}/{PATH}"
    data = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "PDNO": ticker, # 종목
        "ORD_DVSN": "01",
        "ORD_QTY": quantity, # 수량
        "ORD_UNPR": "0", # 시장가 주문
    }
    headers = {
        "content-type": "application/json", 
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "VTTC0802U",
        "custtype": "P",
        "hashkey" : get_hashkey(data)
    }
    res = requests.post(URL, headers=headers, data=json.dumps(data))
    KRX_FWDG_ORD_ORGNO = res.json()["output"]["KRX_FWDG_ORD_ORGNO"]
    ODNO = res.json()["output"]["ODNO"]
    
    return KRX_FWDG_ORD_ORGNO, ODNO

# 종목 매도(시장가)
def sell_ticker(ticker, quantity):
    PATH = "uapi/domestic-stock/v1/trading/order_cash"
    URL = f"{URL_BASE}/{PATH}"
    data = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "PDNO": ticker, # 종목
        "ORD_DVSN": "01",
        "ORD_QTY": quantity, # 수량
        "ORD_UNPR": "0", # 시장가 주문
    }
    headers = {
        "content-type": "application/json", 
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "TTTC0801U",
        "custtype": "P",
        "hashkey" : get_hashkey(data)
    }
    res = requests.post(URL, headers=headers, data=json.dumps(data))
    KRX_FWDG_ORD_ORGNO = res.json()["output"]["KRX_FWDG_ORD_ORGNO"]
    ODNO = res.json()["output"]["ODNO"]
    
    return KRX_FWDG_ORD_ORGNO, ODNO