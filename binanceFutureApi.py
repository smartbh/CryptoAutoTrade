import ccxt
import pprint
import schedule
import time
import math
import csv
import datetime as dt

print('binance automatic processing working...')

with open("api.txt") as apifile:
    lines = apifile.readlines()
    api_key = lines[0].strip()
    secret = lines[1].strip()



binance = ccxt.binance(config={
    'apiKey': api_key,
    'secret': secret,
    'enableRateLimit': True,
    'options':{
        'defaultType': 'future'
        }
})




#심볼과 레버리지 정하기 (1회)
markets = binance.load_markets()
symbol = "BTC/USDT"
market = binance.market(symbol)
leverage = 50

resp = binance.fapiPrivate_post_leverage({
    'symbol':market['id'],
    'leverage':leverage
    })


#맨 처음 돌릴때 계좌 잔고  한번 선언 필요
balance  = binance.fetch_balance(params={"type": "future"})



###전역 변수들 만들기 (1회 실행)
count = 0 #카운트가 2가 되면 프로그램 종료하게
start_seed = 0
daytime = dt.datetime.now() #오늘 날짜
days = ['월요일','화요일','수요일','목요일','금요일','토요일','일요일'] #요일 리스트
day = dt.datetime.today().weekday() #오늘 요일 받아옴, 숫자로 받아오게 됨 0~6
#days[day] <- 요일 나옴
today_profit = 0 #수익
today_result = None #승패
last_amount = 0 #short에서 사용할 변수
### 전역 변수들은 무한루프에서 계속 수정해줘야함




#잔고 계산 함수
def cal_amount(usdt_balance, cur_price): #usdt기준
    portion = 0.95 #현 잔고의 95% 
    usdt_trade = usdt_balance * portion
    amount = math.floor((usdt_trade * 1000000)/cur_price) / 1000000 * leverage
    return amount 




usdt = balance['total']['USDT']
ticker = binance.fetch_ticker(symbol)
cur_price = ticker['last']




#바이낸스 선물 매수 포지션 잡는 함수
#롱포지션 잡고 정리시
# long먼저 -> short함수순
def binance_long():
    #그날 시작 시드
    global start_seed
    start_seed = balance['total']['USDT']

    #주문 함수
    order = binance.create_market_buy_order(
        symbol = symbol,
        amount=cal_amount(usdt, cur_price) #잔고, 현재가
    )
    global last_amount
    last_amount = cal_amount(usdt, cur_price)
    global count
    count+=1

    #작업 착수일 기입
    print("거래 시작")
    print("오늘 날짜 = ", end = '')
    print(daytime)
    print("오늘 요일 = ", end = '')
    print(days[day])
    print("현재 내 잔고 : ", end = '')
    print(balance['USDT']['free'])
    print("현재 레버리지 : ", end='')
    print(leverage)







#바이낸선 선물 매도 포지션 잡는 함수
#롱포지션 잡고 정리시
# shot먼저 -> long함수순
def binance_short():
    order = binance.create_market_sell_order(
        symbol=symbol,
        amount=last_amount #같은 수량을 팔아야함 buy order의 amount
    )
    global count
    count+=1
    




#월
schedule.every().monday.at("23:21:00").do(binance_long)
schedule.every().monday.at("23:32:00").do(binance_short)

#화
schedule.every().tuesday.at("23:21:00").do(binance_long)
schedule.every().tuesday.at("23:32:00").do(binance_short)

#수
schedule.every().wednesday.at("23:21:00").do(binance_long)
schedule.every().wednesday.at("23:32:00").do(binance_short)

#목
schedule.every().thursday.at("23:21:00").do(binance_long)
schedule.every().thursday.at("23:32:00").do(binance_short)

#금
schedule.every().friday.at("23:21:00").do(binance_long)
schedule.every().friday.at("23:32:00").do(binance_short)




#스케쥴 함수 돌아가게
while True:
    #usdt, cur_price가 계속 바뀜
    #usdt = 내 계좌의 잔고
    #cur_price = 비트코인의 가격, 수량에 영향주기때문
    usdt = balance['total']['USDT'] #현재 계좌내 USDT달러
    ticker = binance.fetch_ticker(symbol)
    cur_price = ticker['last'] #현재 비트 가격
    schedule.run_pending()
    time.sleep(0.1) #0.1초 마다 루프
    

    if count >= 2:
        daytime = dt.datetime.now() #오늘 날짜
        days = ['월요일','화요일','수요일','목요일','금요일','토요일','일요일'] #요일 리스트
        day = dt.datetime.today().weekday() #오늘 요일 받아옴, 숫자로 받아오게 됨 0~6
        #days[day] <- 요일 나옴
        
        balance  = binance.fetch_balance(params={"type": "future"})
        #포지션 종료 후 계좌 잔고
        last_seed = balance['total']['USDT'] #마지막 계좌(수익포함)
        today_profit = last_seed - start_seed #하루 수익
        profit_percentage = round((today_profit/start_seed), 3) * 100
        print("오늘 작업 종료")
        print("현재 내 잔고 : ")
        print(balance['USDT'])
        print("오늘 수익 : ", end = '')
        print(today_profit)
        print("오늘 수익률 : ", end = '')
        print(profit_percentage)

        if today_profit > 0:
            today_result = '승'
        elif today_profit == 0:
            today_result = '무'
        else:
            today_result = '패'
            
        #csv 파일 열고 불러오기
        f = open('binance.csv', 'a', encoding = 'utf-8', newline='')
        wr = csv.writer(f)
        wr.writerow([daytime,days[day],start_seed,last_seed,today_profit,today_result,profit_percentage])
        f.close()
        
        #변수들 초기화 작업
        count = 0 #다시 카운트를 초기화해줌
        today_profit = 0 #수익
        today_result = None #승패
        last_amount = 0
        print('오늘 작업 종료')
        #break 쓰면 안된다 무한루프가 깨져버림



        

