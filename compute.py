import threading, json, time, datetime, os, pprint, traceback
import pandas as pd
import pandas_ta as ta
import numpy

class compute():
    def computeSMA(self, array, timeperiod):
        '''
            Compute Simple Moving Average from a list of close prices
        '''
        ma = []
        for i in range(timeperiod-1):
            ma.append(0) 
        for i in range(timeperiod, len(array)+1):
            ma.append(sum(array[i-timeperiod:i])/timeperiod)
        return ma

    def computeEMA(self, array, timeperiod):
        '''
            Compute Exponential Moving Average from a list of close prices
        '''
        ema = []
        sum = 0
        smooth = 2/(timeperiod+1)
        for i in range(timeperiod-1):
            ema.append(0)
            sum += array[i]
        ema.append((sum+array[timeperiod-1])/timeperiod)
        for i in range(timeperiod, len(array)):
            ema.append(array[i]*smooth + ema[i-1]*(1-smooth))
        return ema

    def computeRSI(self, data, timeperiod):
        '''
            Compute RSI value from list of close prices.
            Reference from: https://tcoil.info/compute-rsi-for-stocks-with-python-relative-strength-index/
        '''
        diff = numpy.diff(data)
        diff = diff[2:]

        #this preservers dimensions off diff values
        up_chg = 0 * diff
        down_chg = 0 * diff
        
        # up change is equal to the positive difference, otherwise equal to zero
        up_chg[diff > 0] = diff[ diff>0 ]
        
        # down change is equal to negative deifference, otherwise equal to zero
        down_chg[diff < 0] = diff[ diff < 0 ]
        
        up_chg = pd.DataFrame(up_chg)
        down_chg = pd.DataFrame(down_chg)

        up_chg_avg   = up_chg.ewm(com=timeperiod-1 , min_periods=timeperiod).mean()
        down_chg_avg = down_chg.ewm(com=timeperiod-1 , min_periods=timeperiod).mean()
        
        rs = abs(up_chg_avg/down_chg_avg)
        rsi = 100 - 100/(1+rs)
        rsi = rsi.values.tolist()
        rsi_list = [item for sublist in rsi for item in sublist]
        return rsi_list

    def computeMACD(self, array, fastperiod=12, slowperiod=26, signalperiod=9):
        '''
            Compute MACD, MACD signal, MACD histogram from list of close prices
        '''
        ema_fast = self.computeEMA(array, fastperiod)
        ema_slow = self.computeEMA(array, slowperiod)
        MACD = []
        for i in range(len(ema_fast)):
            MACD.append(ema_fast[i]-ema_slow[i])
        MACD_SIGNAL = self.computeEMA(MACD, signalperiod)
        MACD_HIST = []
        for i in range(len(MACD)):
            MACD_HIST.append(MACD[i]-MACD_SIGNAL[i])
        return MACD, MACD_SIGNAL, MACD_HIST

    def combo_select(self, event):
        self.get_last_price()


    def get_precisions(self):
        info = self.client.exchange_info()
        self.quantityPrecisions = {}
        self.pricesPrecisions = {}
        self.stepSizes = {}
        self.tickSizes = {}
        self.minSizes = {}

        for item in info['symbols']:
            self.quantityPrecisions[item['symbol']] = item['quantityPrecision']
            self.pricesPrecisions[item['symbol']] = item['pricePrecision']

            for symbol_filter in item['filters']:
                if symbol_filter['filterType'] == "PRICE_FILTER":
                    self.tickSizes[item['symbol']] = float(symbol_filter['tickSize'])
                if symbol_filter['filterType'] == "LOT_SIZE":
                    self.minSizes[item['symbol']] = float(symbol_filter['minQty'])
                    self.stepSizes[item['symbol']] = float(symbol_filter['stepSize'])


    def get_last_price(self):
        self.pair = self.comboPair.get()

        self.stepSize = self.stepSizes[self.pair]
        self.quantityPrecision = self.quantityPrecisions[self.pair]
        self.minSize = self.minSizes[self.pair]

        self.tickSize = self.tickSizes[self.pair]
        if self.pair == "BTCUSDT":
            self.tickSize = 0.1
        self.pricePrecision = self.pricesPrecisions[self.pair]

        self.price = float(self.client.ticker_price(self.pair)['price'])


    def openThread(self):
        if self.killThread:
            self.killThread = False

        self.btnStart.config(text=' 🚫 Stop ', command=lambda:self.closeThread())
        self.x = threading.Thread(target= self.startTrading)
        self.x.start()


    def restartThread(self):
        self.killThread = False
        self.openThread()

        self.attributes("-topmost", False)

        # Restart
        self.side = "none"
        self.size = 0
        self.minSize = 0
        self.leverage = 0
        self.startBalance = 0
        self.canTrade = False
        self.inPosition = False
        self.buyPrices = []

        self.lastTradeTimestamp = ""
        self.lastTradeSide = ""
        self.lastTradeSize = 0
        self.lastTradePrice = 0
        self.orderIds = []

        self.longConditionsTriggered = False
        self.shortConditionsTriggered = False
        self.longTriggerTime = ""
        self.shortTriggerTime = ""
        self.longOpenTime = ""
        self.shortOpenTime = ""
        self.longTriggerCandleTime = ""
        self.shortTriggerCandleTime = ""
        self.profits = 0

        self.btnStart.config(text='💵 Start Trading!', command=lambda:self.startThread())
        self.btnPublic.config(state= "normal")
        self.btnPrivate.config(state= "normal")
        self.btnLong.config(state="disabled")
        self.btnShort.config(state="disabled")
        self.btnCancel.config(state="disabled")
        self.entryAmount.config(state="normal")
        self.comboPair.config(state="readonly")
        self.chkbtnTrigger.config(state="normal")
        self.comboTimeframes.config(state="readonly")
        self.labelTimestampVar.set("")
        self.labelSideVar.set(self.side)
        self.labelCloseTimeVar.set("")
        self.labelStopLossVar.set(0.0)
        self.labelTakeprofitVar.set(0.0)
        self.labelBuyPriceVar.set(0.0)
        self.labelLastVar.set(0.0)
        self.labelDeltaVar.set("")
        self.labelLastTradeVar.set("")
        self.labelBalanceVar.set("")


    def startTrading(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        has = hasattr(self, 'balance')
        if not has:
            self.get_balance()
        self.startBalance = self.balance

        with open(f"{self.dir}/Trades_{datetime.datetime.now().strftime('%Y-%m-%d')}.json", "a") as file:
            json.dump({"status": "Connection Open", "timestamp": now, "balance": round(self.balance, 4)}, file, indent=4)

        while True:
            if not self.killThread:
                try:
                    self.trading()
                    time.sleep(0.3)
                except Exception as error:
                    print(f"Error: An error occur while searching:\n{traceback.format_exc()}")
                    continue
            else:
                break


    def order(self, side):
        try:
            orderObj = {
                "symbol": self.pair,
                "side": side, # BUY for long, SELL for short
                "type": "MARKET",
                "quantity": self.precisedSize # Precised quantity
            }
            order = self.client.new_order(**orderObj, recvWindow= 6000)
            return(order)
        except Exception as error:
            return(error)


    def trading(self):
        nowUtc = datetime.datetime.utcnow()
        now = datetime.datetime.now()
        nowStr = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        df = pd.DataFrame(self.binance.fetch_ohlcv(self.pair, timeframe= self.tf), columns= ["time", "open", "high", "low", "close", "volume"])
        df['datetime'] = pd.to_datetime(df['time'], unit="ms")

        self.startTime = df['datetime'].iloc[-1]
        self.labelTimestampVar.set(self.startTime)

        close_prices = df['close']
        macd = ta.macd(close_prices)
        df = pd.concat([df, macd], axis=1)

        previous_macd = df['MACD_12_26_9'].shift(1)
        previous_signal = df['MACDs_12_26_9'].shift(1)

        # Last Bearish Crossover
        crossingBearish = df[(df['MACD_12_26_9'] <= df['MACDs_12_26_9']) & (previous_macd >= previous_signal)]
        last_crossingBearish = crossingBearish.iloc[-1]

        # Last Bullish Crossover
        crossingBullish = df[(df['MACD_12_26_9'] >= df['MACDs_12_26_9']) & (previous_macd <= previous_signal)]
        last_crossingBullish = crossingBullish.iloc[-1]

        self.lastTradePrice = close_prices.iloc[-1]
        self.labelLastVar.set(round(self.lastTradePrice, 5))
        self.labelSideVar.set(self.side)


        # Check if condition is still valid after 1/3 of time until candle close
        if self.longConditionsTriggered:
            if self.startTime == last_crossingBullish['datetime']: # <= datetime.timedelta(minutes= self.tfMinutes):
                long_crossover = True
            else:
                long_crossover = False

            short_crossover = False
            shortStillValid = False

            minutesToClose = self.longTriggerCandleTime + datetime.timedelta(minutes= self.tfMinutes) - nowUtc
            longAfterMin = now - self.longTriggerTime >= minutesToClose / 3

            if longAfterMin and long_crossover:
                longStillValid = True
            else:
                longStillValid = False

        elif self.shortConditionsTriggered:
            if self.startTime == last_crossingBearish['datetime']: # <= datetime.timedelta(minutes= self.tfMinutes):
                short_crossover = True
            else:
                short_crossover = False

            long_crossover = False
            longStillValid = False

            minutesToClose = self.shortTriggerCandleTime + datetime.timedelta(minutes= self.tfMinutes) - nowUtc
            shortAfterMin = now - self.shortTriggerTime >= minutesToClose / 3

            if shortAfterMin and short_crossover:
                shortStillValid = True
            else:
                shortStillValid = False

        else:
            longStillValid = False
            shortStillValid = False

            # Current Crossover
            if last_crossingBearish['datetime'] == self.startTime:
                currentCrossover = {"side": "bear", "crossed": True}
            elif last_crossingBullish['datetime'] == self.startTime:
                currentCrossover = {"side": "bull", "crossed": True}
            else:
                currentCrossover = {"side": "none", "crossed": False}

            # Check if there is crossover now
            long_crossover = currentCrossover['side'] == "bull"
            short_crossover = currentCrossover['side'] == "bear"


        # Without trigger
        if long_crossover and not self.inPosition and self.side == "none" and not self.longConditionsTriggered:
            if self.modeTrigger == 0:
                # Open long position
                print(f"{nowStr}: OPEN LONG POSITION")
                self.side = "long"
                self.get_variables()
                if self.canTrade:
                    newOrder = self.order("BUY")
                    self.succeedOrder(newOrder, "Conditions")
                    self.inPosition = True
                    self.longOpenTime = self.startTime
                else:
                    print(f"{nowStr}: You don't have enough $ to execute that trade.")
                    return

            else:
                # Trigger long
                self.longConditionsTriggered = True
                self.longTriggerTime = now
                self.longTriggerCandleTime = self.startTime
                return

        elif short_crossover and not self.inPosition and self.side == "none" and not self.shortConditionsTriggered:
            if self.modeTrigger == 0:
                # Open short position
                print(f"{nowStr}: OPEN SHORT POSITION")
                self.side = "short"
                self.get_variables()
                if self.canTrade:
                    newOrder = self.order("SELL")
                    self.succeedOrder(newOrder, "Conditions")
                    self.inPosition = True
                    self.shortOpenTime = self.startTime
                else:
                    print(f"{nowStr}: You don't have enough $ to execute that trade.")
                    return

            else:
                # Trigger short
                self.shortConditionsTriggered = True
                self.shortTriggerTime = now
                self.shortTriggerCandleTime = self.startTime
                return


        elif not self.inPosition and self.side == "none" and self.longConditionsTriggered and longStillValid:
            # Open long position after trigger
            print(f"{nowStr}: OPEN LONG POSITION AFTER TRIGGER")
            self.side = "long"
            self.get_variables()
            if self.canTrade:
                newOrder = self.order("BUY")
                self.succeedOrder(newOrder, "Conditions")
                self.inPosition = True
                self.longConditionsTriggered = False
                self.longOpenTime = self.startTime
            else:
                print(f"{nowStr}: You don't have enough $ to execute that trade.")
                return

        elif self.longConditionsTriggered and not longStillValid:
            self.longConditionsTriggered = False


        elif not self.inPosition and self.side == "none" and self.shortConditionsTriggered and shortStillValid:
            # Open short position after trigger
            print(f"{nowStr}: OPEN SHORT POSITION AFTER TRIGGER")
            self.side = "short"
            self.get_variables()
            if self.canTrade:
                newOrder = self.order("SELL")
                self.succeedOrder(newOrder, "Conditions")
                self.inPosition = True
                self.shortConditionsTriggered = False
                self.shortOpenTime = self.startTime
            else:
                print(f"{nowStr}: You don't have enough $ to execute that trade.")
                return

        elif self.shortConditionsTriggered and not shortStillValid:
            self.shortConditionsTriggered = False


        elif self.inPosition:
            lastBuyPrice = self.buyPrices[-1]
            self.labelBuyPriceVar.set(round(lastBuyPrice, 5))

            self.dPrice = ((self.lastTradePrice - lastBuyPrice) * 100) / lastBuyPrice
            if self.side == "short": self.dPrice = -self.dPrice

            self.labelDeltaVar.set(f"{round(self.dPrice, 4)}%")

            if self.side == "long":
                stoplossPrice = lastBuyPrice * (1 - self.stopLoss / 100)
                takeprofitPrice = lastBuyPrice * (1 + self.takeprofit / 100)

                candleClosed = self.startTime - self.longOpenTime >= datetime.timedelta(minutes= self.tfMinutes)
                minutesToClose = self.longOpenTime + datetime.timedelta(minutes= self.tfMinutes) - nowUtc

            elif self.side == "short":
                stoplossPrice = lastBuyPrice * (1 + self.stopLoss / 100)
                takeprofitPrice = lastBuyPrice * (1 - self.takeprofit / 100)

                candleClosed = self.startTime - self.shortOpenTime >= datetime.timedelta(minutes= self.tfMinutes)
                minutesToClose = self.shortOpenTime + datetime.timedelta(minutes= self.tfMinutes) - nowUtc

            self.labelStopLossVar.set(round(stoplossPrice, 5))
            self.labelTakeprofitVar.set(round(takeprofitPrice, 5))

            hours, remainder = divmod(minutesToClose.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            closeTime = f"{int(minutes)}:{int(seconds)}"
            self.labelCloseTimeVar.set(closeTime)

            # Close long position after candle is closed
            if self.side == "long" and candleClosed:
                print(f"{now}: CLOSE LONG POSITION")

                newOrder = self.order("SELL")
                self.succeedOrder(newOrder, "Minutes")
                self.inPosition = False
                self.side = "none"
                self.longConditionsTriggered = False
                self.longTriggerTime = ""
                self.longOpenTime = ""
                self.longTriggerCandleTime = ""

            # Close long position with stop loss
            elif self.side == "long" and self.dPrice < 0 and self.stopLoss > 0 and self.dPrice < -self.stopLoss:
                print(f"{now}: CLOSE LONG POSITION WITH LOSS")

                newOrder = self.order("SELL")
                self.succeedOrder(newOrder, "Stop Loss")
                self.inPosition = False
                self.side = "none"
                self.longConditionsTriggered = False
                self.longTriggerTime = ""
                self.longOpenTime = ""
                self.longTriggerCandleTime = ""

            # Close long position with take profit
            elif self.side == "long" and self.dPrice > 0 and self.takeprofit > 0 and self.dPrice > self.takeprofit:
                print(f"{now}: CLOSE LONG POSITION WITH PROFIT")

                newOrder = self.order("SELL")
                self.succeedOrder(newOrder, "Take Profit")
                self.inPosition = False
                self.side = "none"
                self.longConditionsTriggered = False
                self.longTriggerTime = ""
                self.longOpenTime = ""
                self.longTriggerCandleTime = ""

            # Close short position after candle is closed
            elif self.side == "short" and candleClosed:
                print(f"{now}: CLOSE SHORT POSITION")

                newOrder = self.order("BUY")
                self.succeedOrder(newOrder, "Minutes")
                self.inPosition = False
                self.side = "none"
                self.shortConditionsTriggered = False
                self.shortTriggerTime = ""
                self.shortOpenTime = ""
                self.shortTriggerCandleTime = ""

            # Close short position with stop loss
            elif self.side == "short" and self.dPrice < 0 and self.stopLoss > 0 and self.dPrice < -self.stopLoss:
                print(f"{now}: CLOSE SHORT POSITION WITH LOSS")

                newOrder = self.order("BUY")
                self.succeedOrder(newOrder, "Stop Loss")
                self.inPosition = False
                self.side = "none"
                self.shortConditionsTriggered = False
                self.shortTriggerTime = ""
                self.shortOpenTime = ""
                self.shortTriggerCandleTime = ""

            # Close short position with take profit
            elif self.side == "short" and self.dPrice > 0 and self.takeprofit > 0 and self.dPrice > self.takeprofit:
                print(f"{now}: CLOSE SHORT POSITION WITH PROFIT")

                newOrder = self.order("BUY")
                self.succeedOrder(newOrder, "Take Profit")
                self.inPosition = False
                self.side = "none"
                self.shortConditionsTriggered = False
                self.shortTriggerTime = ""
                self.shortOpenTime = ""
                self.shortTriggerCandleTime = ""

        else:
            self.dPos = 0.0
            self.labelBuyPriceVar.set(0.0)
            self.labelStopLossVar.set(0.0)
            self.labelTakeprofitVar.set(0.0)
            self.labelDeltaVar.set(f"{round(self.dPos, 4)}%")
            self.labelCloseTimeVar.set("")

    def longShort(self, side):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.get_variables()

        if self.canTrade:
            if side == "long" and not self.inPosition:
                print(f"{now}: OPEN LONG POSITION MANUALLY")
                self.side = side
                newOrder = self.order("BUY")
                self.succeedOrder(newOrder, "Manually")
                self.longOpenTime = self.startTime

            elif side == "short" and not self.inPosition:
                print(f"{now}: OPEN SHORT POSITION MANUALLY")
                self.side = side
                newOrder = self.order("SELL")
                self.succeedOrder(newOrder, "Manually")
                self.shortOpenTime = self.startTime

            elif side == "short" and self.inPosition and self.side == "long":
                print(f"{now}: CLOSE LONG POSITION MANUALLY")
                newOrder = self.order("SELL")
                self.succeedOrder(newOrder, "Manually")

            elif side == "long" and self.inPosition and self.side == "short":
                print(f"{now}: CLOSE SHORT POSITION MANUALLY")
                newOrder = self.order("BUY")
                self.succeedOrder(newOrder, "Manually")

    def succeedOrder(self, newOrder, condition="Conditions"):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pprint.pprint(newOrder)

        if isinstance(newOrder, Exception):
            # messagebox.showwarning("Error", f"Order execution failed due to an error:\n{newOrder}", parent= self)
            print(f"Error: Order execution failed due to an error:\n{newOrder}")

        elif "orderId" in newOrder:
            self.lastTradeTimestamp = now

            self.orderIds.append(newOrder['orderId'])

            userOrders = self.client.get_all_orders(self.pair)
            for o in userOrders:
                if o['orderId'] == newOrder['orderId']:
                    order = o
                    break

            positions = self.client.account()['positions']
            for pos in positions:
                if pos['symbol'] == self.pair:
                    havingQuantity = float(pos['positionAmt'])
                    break

            if order['status'] == "FILLED":
                buyPrice = float(order['avgPrice'])
                self.buyPrices.append(buyPrice)

                self.lastTradeSize = float(order['origQty'])
                self.buySizes.append(self.lastTradeSize)

                if condition == "Manually":
                    if (self.side == "long" and havingQuantity >= self.minSize) or (self.side == "short" and -havingQuantity >= self.minSize):
                        self.inPosition = True
                        self.lastTradeSide = self.side
                    elif abs(havingQuantity < self.minSize):
                        self.inPosition = False
                        self.lastTradeSide = self.side
                        self.side = "none"
                elif condition == "Conditions":
                    if (self.side == "long" and havingQuantity >= self.minSize) or (self.side == "short" and -havingQuantity >= self.minSize):
                        self.inPosition = True
                        self.lastTradeSide = self.side
                    elif self.side == "long" and havingQuantity < self.minSize:
                        self.lastTradeSide = "short"
                        self.inPosition = False
                        self.side = "none"
                    elif self.side == "short" and abs(havingQuantity) < self.minSize:
                        self.lastTradeSide = "long"
                        self.inPosition = False
                        self.side = "none"
                elif condition == "Stop Loss" or condition == "Take Profit" or condition == "Minutes" or condition == "Close All":
                    if self.side == "long" and havingQuantity < self.minSize:
                        self.lastTradeSide = "short"
                        self.inPosition = False
                        self.side = "none"
                    elif self.side == "short" and abs(havingQuantity) < self.minSize:
                        self.lastTradeSide = "long"
                        self.inPosition = False
                        self.side = "none"
                else:
                    self.inPosition = False
                    self.side = "none"

                self.labelSideVar.set(self.side)
                self.labelBuyPriceVar.set(round(buyPrice, 5))
                self.labelLastTradeVar.set(f"{self.lastTradeTimestamp} - {self.lastTradeSide} x{round(self.lastTradeSize, 4)} @ {round(buyPrice, 5)}")

                if self.side == "none":
                    profit = buyPrice * self.lastTradeSize - self.buyPrices[-2] * self.buySizes[-2]
                    if self.lastTradeSide == "long":
                        profit = -profit
                    profitPerc = profit * 100 / (self.buyPrices[-2] * self.buySizes[-2])

                    self.profits += profitPerc
                    self.get_balance()

                with open(f"{self.dir}/Trades_{datetime.datetime.now().strftime('%Y-%m-%d')}.json", "a") as file:
                    json.dump({"status": f"Execute {self.lastTradeSide} order", "timestamp": now, "price": buyPrice, "condition": condition}, file, indent= 4)
                    json.dump(newOrder, file, indent=4)

    def onClose(self):
        self.killThread = True
        self.destroy()
        os._exit(0)