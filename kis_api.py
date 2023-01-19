import requests
import json
import yaml
import time
import pandas as pd
from datetime import datetime, timedelta

# config
with open("config/config.yaml", encoding="UTF-8") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)
    
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

# 개장일 확인
def check_open(date):
    PATH = "uapi/domestic-stock/v1/quotations/chk-holiday"
    URL = f"{URL_BASE}/{PATH}"
    params = {
        "BASS_DT": date,
        "CTX_AREA_NK": "",
        "CTX_AREA_FK": ""
    }
    headers = {
        "content-type": "application/json", 
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "CTCA0903R"
    }
    res = requests.get(URL, headers=headers, params=params)
    data = res.json()

    return data["output"]#[0]["opnd_yn"]

def find_date_m(date, lag):
    date_m = ""
    
    date_list = check_open(date)
    cnt = 0
    for dt in date_list[1:]:
        if dt["opnd_yn"] == "Y":
            cnt += 1
            if cnt == lag:
                date_m = dt["bass_dt"]
                break
    return date_m

# 주식잔고 조회
def get_stock_balance():
    PATH = "/uapi/domestic-stock/v1/trading/inquire-balance"
    URL = f"{URL_BASE}/{PATH}"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "TTTC8434R",
    }
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }
    res = requests.get(URL, headers=headers, params=params)
    stock_list = res.json()["output1"]
    cash = int(res.json()["output2"][0]["prvs_rcdl_excc_amt"])
    stock_dict = {}
    for stock in stock_list:
        if int(stock["hldg_qty"]) > 0:
            stock_dict[stock["pdno"]] = stock["hldg_qty"]
    return stock_dict, cash

# 현재가 조회
def get_current_price(ticker):
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
    data = res.json()
    
    return data["output"]

# 기간 데이터
def get_daily_price(ticker):
    today = datetime.strftime(datetime.today(), "%Y%m%d")
    daysago = datetime.strftime(datetime.today() - timedelta(weeks=22), "%Y%m%d")
    
    def get_ohlcv(from_date, to_date):  
        PATH = "uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        URL = f"{URL_BASE}/{PATH}"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {ACCESS_TOKEN}",
            "appkey": APP_KEY,
            "appsecret": APP_SECRET,
            "tr_id": "FHKST03010100",
            "custtype": "P"
        }
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": ticker,
            "fid_input_date_1": from_date,
            "fid_input_date_2": to_date,
            "fid_period_div_code": "D",
            "fid_org_adj_prc": "0"
        }
        res = requests.get(URL, headers=headers, params=params)
        data = res.json()
        
        df = pd.DataFrame(data["output2"])
        df = df.iloc[:, :7]
        df.columns = ["date", "close", "open", "high", "low", "volume", "trading_value"]
        df = pd.concat([df[["date"]], df[["close", "open", "high", "low", "volume", "trading_value"]].astype(float)], axis=1)
        df = df.sort_values("date", ascending=True).reset_index(drop=True)
        
        market_cap = int(data["output1"]["hts_avls"])
        df["pct"] = df["close"].pct_change(1)
        pct_list = df["pct"].dropna().tolist()
        pct_list.reverse()

        mc_list = []
        mc = market_cap
        for pct in pct_list:
            mc = mc / (1 + pct)
            mc_list.append(mc)
        mc_list.reverse()
        mc_list.append(market_cap)

        df = df.drop(columns=["pct"])
        df["market_cap"] = mc_list
        df["market_cap"] = df["market_cap"] * 1e+8
        df["tv/mc"] = df["trading_value"] / df["market_cap"]
        
        return df
    
    df1 = get_ohlcv(daysago, today)
    time.sleep(0.05)
    date1 = datetime.strftime(datetime.strptime(df1["date"][0], "%Y%m%d") - timedelta(days=1), "%Y%m%d")
    date2 = datetime.strftime(datetime.strptime(date1, "%Y%m%d") - timedelta(weeks=22), "%Y%m%d")
    df2 = get_ohlcv(date2, date1)
    
    df = pd.concat([df2, df1]).reset_index(drop=True)
    return df

# 투자자별 거래량
def get_trading_volume(ticker):    
    PATH = "uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    URL = f"{URL_BASE}/{PATH}"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01010900",
        "tr_cont": "N",
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": ticker,
    }
    res = requests.get(URL, headers=headers, params=params)
    data = res.json()
    
    df = pd.DataFrame(data["output"])
    df = df[["stck_bsop_date", "frgn_ntby_qty", "prsn_ntby_qty", "orgn_ntby_qty"]]
    df.columns = ["date", "foreign", "individual", "institutional"]
    
    df = df.sort_values("date", ascending=True)
    df = pd.concat([df[["date"]], df[["foreign", "individual", "institutional"]].astype(float)], axis=1)
    return df

# 종목 매수(시장가)
def buy_ticker(ticker, quantity):
    PATH = "uapi/domestic-stock/v1/trading/order-cash"
    URL = f"{URL_BASE}/{PATH}"
    data = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "PDNO": ticker, # 종목
        "ORD_DVSN": "01",
        "ORD_QTY": str(int(quantity)), # 수량
        "ORD_UNPR": "0", # 시장가 주문
    }
    headers = {
        "content-type": "application/json", 
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "TTTC0802U",
        "hashkey" : get_hashkey(data)
    }
    res = requests.post(URL, headers=headers, data=json.dumps(data))
    if res.json()['rt_cd'] == '0':
        return True
    else:
        return False

# 종목 매도(시장가)
def sell_ticker(ticker, quantity):
    PATH = "uapi/domestic-stock/v1/trading/order-cash"
    URL = f"{URL_BASE}/{PATH}"
    data = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "PDNO": ticker, # 종목
        "ORD_DVSN": "01",
        "ORD_QTY": str(int(quantity)), # 수량
        "ORD_UNPR": "0", # 시장가 주문
    }
    headers = {
        "content-type": "application/json", 
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "TTTC0801U",
        "hashkey" : get_hashkey(data)
    }
    res = requests.post(URL, headers=headers, data=json.dumps(data))
    if res.json()['rt_cd'] == '0':
        return True
    else:
        return False

APP_KEY = cfg["APP_KEY"]
APP_SECRET = cfg["APP_SECRET"]
ACCESS_TOKEN = ""
CANO = cfg["CANO"]
ACNT_PRDT_CD = cfg["ACNT_PRDT_CD"]
URL_BASE = cfg["URL_BASE"]
ACCESS_TOKEN = get_access_token()