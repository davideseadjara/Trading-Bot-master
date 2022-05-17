import ccxt
from datetime import datetime
from compute import compute
import csv
import requests

class trader:
    def __init__(self, _symbol, _interval, _exchange_name, _trade_amount, _is_futures, _live_trade, _apiKey, _apiSecret, _userId):
        '''
            Initialize a trader instance. Input parameters include:
                +Trading symbol e.g. BTC/USDT, ETH/BUSD,.. (String)
                +Interval e.g. 1m, 3m, 1d,... (String)
                +Exchange name e.g. binance, binanceusdm, kucoin, kraken,... (String)
                +Default trade amount in quote asset e.g. 0.001, 2, 3,.. (Float)
                +Is futures, whether you are trading futures or not (Bool)
                +Is live, whether you are trading live (Bool). If False, only dry run, if True, live trade + dry run double as logging
                +API key (String)
                +API secret (String)
                +Telegram user IDs for notification bot (List of String)
        '''
        self.symbol = _symbol
        self.interval = _interval
        self.exchange_name = _exchange_name
        self.trade_amount = _trade_amount
        self.is_futures = _is_futures
        self.live_trade = _live_trade
        self.apiKey = _apiKey
        self.apiSecret = _apiSecret
        self.userids = []
        self.computer = compute()
        for id in _userId:
            self.userids.append(id)

    def writeCSV(self, data, filename = 'dryRunResult.csv'):
        '''
            Write a list of data to a CSV file.
            Used to log trade signals
        '''
        # Create the file if doesn't exist
        try:
            with open(filename, 'r'):
                pass
        except:
            with open(filename, 'w'):
                pass
        
        # Open the CSV file, read last line and calculate last trade's profit, then append to data
        with open(filename, 'r') as f:
            content = f.readlines()
            try:
                last_price = float(content[-1].split(',')[-2])
                if data[2] == 'buy':
                    data.append(f'{round(((last_price/float(data[4]))-1)*100,2)}%')
                elif data[2] == 'sell':
                    data.append(f'{round(((float(data[4])/last_price)-1)*100,2)}%')
            except:
                data.append('0%')
            if len(content) == 0:
                    with open(filename, 'w', newline = '') as f:
                        writer = csv.writer(f)
                        writer.writerow(['Time', 'Symbol', 'Side', 'Size', 'Price', 'Profit from last trade'])

        # Write data with last trade's profit in it
        with open(filename, 'a', newline = '') as f:
            writer = csv.writer(f)
            writer.writerow(data)

    def teleSend(self, text):
        '''
            Send trade signal to Telegram accounts specified
        '''
        # The token of the Telegram bot
        token = '5246438844:AAFPeNBBXZ2l7c2fFMat4Uaesw3_yc0CL24'
        for userid in self.userids:
            params = {'chat_id': userid, 'text': text, 'parse_mode': 'HTML'}
            resp = requests.post('https://api.telegram.org/bot{}/sendMessage'.format(token), params)
            resp.raise_for_status()

    def run(self):
        '''
            Main program with infinite while loop
        '''
        # Operational variables
        shorting = False
        longing = False
        close = []
        run_once = 0
        interval_second = {
            '1m': 60, '3m': 180, '5m': 300,
            '15m': 900, '30m': 1800, '1h': 3600,
            '2h': 7200, '4h': 14400, '6h': 21600,
            '8h': 28800, '12h': 43200, '1d': 86400,
            '3d': 259200, '1w': 604800, '1M': 2592000
            }

        # Exchange initialization
        if self.live_trade:
            exchange = getattr(ccxt, self.exchange_name)({
                'enableRateLimit': True,
                'apiKey': self.apiKey,
                'secret': self.apiSecret
                })
        else:
            exchange = getattr(ccxt, self.exchange_name)({
                'enableRateLimit': True
                })

        # Get historical klines closes
        print('Running...')
        ohlcvs = exchange.fetch_ohlcv(self.symbol, self.interval, limit = 400)
        for ohlcv in ohlcvs[:-1]:
            close.append(ohlcv[4]) # Get historical close price and append to a list

        # Main program loop
        while 1:
            # Getting live close prices
            now = round(datetime.timestamp(datetime.now())-1)
            if now%interval_second[self.interval] == 0 and run_once == 0:
                last = exchange.fetch_ticker(self.symbol)
                close.append(last['last'])
                run_once = 1

                # Print recent close prices to the screen to check
                print(close)
                
                # Calculate indicators
                close = close[-500:]
                EMA10 = self.computer.computeEMA(array = close, timeperiod=10)
                EMA20 = self.computer.computeEMA(array = close, timeperiod=20)
                MA50 = self.computer.computeSMA(array = close, timeperiod=50)
                RSI = self.computer.computeRSI(data = close, timeperiod=14)
                MACD, MACD_SIGNAL, MACD_HIST = self.computer.computeMACD(array = close, fastperiod=12, slowperiod=26, signalperiod=9)

                # Long condition
                if (EMA10[-1] > EMA20[-1] > MA50[-1]) and RSI[-1] < 70 and MACD_HIST[-1] > 0 and not longing:
                    # Open Long position when:
                    #   +EMA10 > EMA20 > MA50 
                    #   +RSI < 70
                    #   +MACD histogram > 0
                    print('Long')
                    shorting = False
                    longing = True
                    if self.live_trade:
                        if self.is_futures:
                            try:
                                exchange.create_order(self.symbol, 'market', 'buy', self.trade_amount, params = {"reduceOnly": True})
                            except:
                                pass
                        exchange.create_order(self.symbol, 'market', 'buy', self.trade_amount)

                    # Logging
                    data = [datetime.now().strftime("%m/%d/%Y-%H:%M:%S"), self.symbol, 'buy', self.trade_amount, close[-1]]
                    self.writeCSV(data)

                    # Sending Telegram notification
                    self.teleSend(f'Opening long position of {self.trade_amount} {self.symbol} at {datetime.now().strftime("%m/%d/%Y-%H:%M:%S")} at the price of {close[-1]}')
                
                # Short condition
                elif (EMA10[-1] < EMA20[-1] < MA50[-1]) and RSI[-1] > 30 and MACD_HIST[-1] < 0 and not shorting:
                    # Open Short position when:
                    #   +EMA10 < EMA20 < MA50 
                    #   +RSI > 30
                    #   +MACD histogram < 0
                    print('Short')
                    shorting = True
                    longing = False
                    if self.live_trade:
                        if self.is_futures:
                            try:
                                exchange.create_order(self.symbol, 'market' 'sell', self.trade_amount, params = {'reduceOnly': True})
                            except:
                                pass
                        exchange.create_order(self.symbol, 'market', 'sell', self.trade_amount)

                    # Logging
                    data = [datetime.now().strftime("%m/%d/%Y-%H:%M:%S"), self.symbol, 'sell', self.trade_amount, close[-1]]
                    self.writeCSV(data)

                    # Sending Telegram notification
                    self.teleSend(f'Opening short position of {self.trade_amount} {self.symbol} at {datetime.now().strftime("%m/%d/%Y-%H:%M:%S")} at the price of {close[-1]}')
            elif now%interval_second[self.interval] != 0 and run_once == 1:
                run_once = 0