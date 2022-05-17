-The strategy is as follow:
    +Open long/buy position when: EMA10>EMA20>MA50 and RSI<70 and MACD>0
    +Open short/sell order when: EMA10<EMA20<MA50 and RSI>30 and MACD<0
-Initial parameters can be changed in line 98=106 of main.py
-If you want to run live, fill your API keys in and remove the comments of line 118-119
-Dry run will be running at default. If you choose to run live, dry run features will double as a logging method
-Dry run/logging result will be stored in a CSV file named dryRunResult.csv

22/03/2022:
-Move main to trader.py. Change its structure to OOP.
-To set parameters, change line 3 in main. The order is: [symbol, timeframe, exchange, trade quantity, is future, live trade mode, api key, api secret, [telegram is]]

25/03/2022:
-Finished everything
-You would need to put the 3 files GUI.py, trader.py, azure.tcl and the folder theme in the same folder in order for this to work
-GUI.py would be our main program. Run it and everything should work
-All the GUI fields are self-explainatory. The button at the bottom is the start/stop button. There is also a status indicator on the top left, which tells you whether the bot is running or stopped. The dark mode toggle switch is for switching between dark and light mode
-the file BacktestScript.rar contains the backtest script and a manual on how to set it up and use it. If you have any question on how to set it up, message me

26/03/2022:
-Added new 700 lines compute.py file. This can be seen as a framework for computing various datas
-The total length now is 1100 lines
-You can tell your professor that the compute.py file is a framework that you developed for further developement but you didn't have time to put all of its functions into the final product.