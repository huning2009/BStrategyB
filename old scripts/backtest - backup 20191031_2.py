import pandas as pd
import numpy as np
import datetime as dt
import matplotlib.pyplot as plt
import math
import sys
import os
import random
from multiprocessing import Process, Queue

def backtest_slice(ticker):
    obj = Strategy(ticker)
    obj.backtest()



class Strategy():
    def __init__(self, ticker) -> None:
        if 'slice' not in ticker:
            self.ticker = ticker
            self.all_data = pd.read_csv(ticker + ".csv")
        else:
            self.all_data = pd.read_csv(ticker)
        self.multiplier_df = pd.read_csv("multiplier.csv")
        self.date_list = sorted(list(set(self.all_data["date"])))
        self.all_data["quantity"] = self.all_data["Volume_(BTC)"].apply(lambda x: round(x, 2))
        self.x = list(range(1440))
        self.xtick = list(range(0, 1441, 120))
        self.xticklabel = list(range(0, 25, 2))
        self.plot = True

    def multi_backtest(self, arg_dict=None, plot=False):

        if not os.path.exists(self.ticker + "/data_slice_9.csv"):
            self.slice()
        q = Queue()
        jobs = list()
        for i in range(0, 10):
            ticker = self.ticker + "/data_slice_" + str(i) + ".csv"
            p = Process(target=backtest_slice, args=(ticker,))
            jobs.append(p)
            p.start()
            print("Start process" + str(i))
        # for i in range(0, 10):
        #     df = df.append(q.get())
        for job in jobs:
            job.join()


    def slice(self, process_num=10):
        n = process_num
        N = len(self.date_list)
        try:
            os.removedirs("btc/" + self.ticker)
            print("Re-writing the data slice of", self.ticker)
        except:
            print("Writing new data slice of", self.ticker)
        os.makedirs("btc/" + self.ticker)
        for i in range(0, n):
            date_scope = self.date_list[math.floor(i * (N / n)): math.floor((i + 1) * (N / n))]
            data_slice = self.all_data[self.all_data["date"].apply(lambda s: True if s in date_scope else False)]
            data_slice.to_csv("btc/" + "\\data_slice_" + str(i) + ".csv", index=False)
        print("Slice data into " + str(n) + " part.\n Save data slice to: " + "btc/"  + self.ticker)

    def backtest(self) -> None:
        # self.stat_df = pd.DataFrame(columns=["sig_type", "direction", "open_price", "close_price", "pnl", "date"])
        for i in range(len(self.date_list)):
            self.backtest_oneday(i)

    def backtest_oneday(self, i: int) -> None:
        date = self.date_list[i]
        self.initDailyParam(pos_type="all", date=date, i=i)
        self.ax = None
        self.initPlot()


        for n in range(1440):
            self.RAP_Signal(n, 'B')
            self.RAP_Signal(n, 'S')

        self.ax.set_xticks(self.xtick, self.xticklabel)
        self.ax.set_title(date + " PNL:" + str(round(self.pnl, 3)) )
        self.fig.savefig("backtest/" + self.date + ".png")
        plt.close()
        print(date)

    def initDailyParam(self, pos_type="all", date=None, i=None) -> None:
        if pos_type == "all":
            self.date = date
            df = self.all_data.iloc[1440 * i: 1440 * (i + 1)].copy()
            self.y = df["price"].tolist()
            self.q = df["quantity"]. tolist()
            raw_slope_list = [0,] + list(np.diff(self.y))
            self.multiplier = self.multiplier_df[self.multiplier_df["date"] == date]
            self.multiplier = self.multiplier["multiplier"].tolist()[0]
            self.multiplier = self.multiplier / 4 + self.y[0] / 1000 / 4
            self.slope_list_real = [int(round(t / self.multiplier)) for t in raw_slope_list]
            self.y_min = df["price"].min()
            self.y_max = df["price"].max()
            self.y_mid = 0.5 * (self.y_min + self.y_max)
            self.pnl = 0
        if pos_type == 'B' or pos_type == "all":
            self.RAPB_num = 0
            self.RAPB_sig_type = None
            self.RAPB_start_pos = None
            self.RAPB_start_price = None
            self.RAPB_peak_pos = None
            self.RAPB_peak_price = None
        if pos_type == 'S' or pos_type == "all":
            self.RAPS_num = 0
            self.RAPS_sig_type = None
            self.RAPS_start_pos = None
            self.RAPS_start_price = None
            self.RAPS_nadir_pos = None
            self.RAPS_nadir_price = None


    def initPlot(self) -> (plt, plt):
        y_offset = self.y[0] / 1000 * 0.5
        self.fig, self.ax = plt.subplots(figsize=(20, 10))
        self.ax.plot(self.x, self.y, color="lightgray", linewidth=1)
        self.ax.plot(self.x, self.y, ".", color="lightgray", markersize=2)
        for i in range(1440):
            slope =  self.slope_list_real[i]
            if slope > 0:
                color = "red"
            elif slope < 0:
                color = "green"
            else:
                color = "blue"
            if self.date == "2017-02-01":
                self.ax.text(self.x[i] - 1, self.y[i], str(abs(slope)), fontsize=6, color=color)
            elif abs(slope) > 3:
                self.ax.text(self.x[i] - 1, self.y[i] + y_offset, str(abs(slope)), fontsize=10, color=color)
        plt.title(self.date, size=15)
        # return fig, ax


    def count(self, n: int, threshold: int, *args):
        k = 0
        for h in args:
            if h >= threshold:
                k += 1
        if k >= n:
            return True
        else:
            return False

    def previous_trend(self, n: int):
        if n < 8:
            var1 = 0
        else:
            var1 = round((self.yplus[n + 1] - self.yplus[n - 7]) / self.multiplier / 8, 2)
        if n < 30:
            var2 = 0
        else:
            var2 = round((self.yplus[n + 1] - self.yplus[n - 29]) / self.multiplier / 30, 2)
        if n < 60:
            var3 = 0
        else:
            var3 = self.volitility(self.slope_list[n - 59: n + 1])
        if n < 240:
            var4 = 0
        else:
            var4 = self.volitility(self.slope_list[n - 239: n + 1])
        return var1, var2, var3, var4


    def calTriggerPrice(self, n: int, direction: str):
        price = self.y[n]
        if direction == 'B':
            H = self.delta2h(self.RAPB_peak_price - self.RAPB_start_price)
            if price - self.y[n - 1] >= 0:
                if price > self.RAPB_peak_price:
                    self.RAPB_peak_price = self.y[n]
                if self.RAPB_strike is False and self.delta2h(price - self.RAPB_start_price) > 6:
                    self.RAPB_strike = True
                return price - 4 * self.multiplier
            elif price - self.y[n - 1] < 0:
                if self.RAPB_strike is False:
                    return self.RAPB_start_price - 4 * self.multiplier
                elif H < 10:
                    return  self.RAPB_start_price + 2 / 3 * H * self.multiplier
                elif H < 20:
                    return self.RAPB_start_price + 4 / 5 * (H + 1) * self.multiplier
                elif H < 30:
                    return self.RAPB_start_price + 4 / 5 * (H + 5) * self.multiplier
                else:
                    return self.RAPB_peak_price -  7 * self.multiplier
        if direction == 'S':
            H = self.delta2h(self.RAPS_start_price - self.RAPS_nadir_price)
            if price - self.y[n - 1] <= 0:
                if price < self.RAPS_nadir_price:
                    self.RAPS_nadir_price = self.y[n]
                if self.RAPS_strike is False and self.delta2h(self.RAPS_start_price - price) > 6:
                    self.RAPS_strike = True
                return price + 4 * self.multiplier
            elif price - self.y[n - 1] > 0:
                if self.RAPS_strike is False:
                    return self.RAPS_start_price + 4 * self.multiplier
                elif H < 10:
                    return  self.RAPS_start_price - 2 / 3 * H * self.multiplier
                elif H < 20:
                    return self.RAPS_start_price - 4 / 5 * (H + 1) * self.multiplier
                elif H < 30:
                    return self.RAPS_start_price - 4 / 5 * (H + 5) * self.multiplier
                else:
                    return self.RAPS_nadir_price +  7 * self.multiplier

    def delta2h(self, delta):
        return round(delta / self.multiplier)

    def RAP_Signal(self, n: int, direction: str):

        if direction == 'B':
            self.slope_list = self.slope_list_real
            self.yplus = self.y
            color = "gold"
        elif direction == 'S':
            self.slope_list = [- t for t in  self.slope_list_real]
            self.yplus = [- t for t in self.y]
            color = "deeppink"
        else:
            raise ValueError("Wrong direction: " + direction)

        # Close position part
        if direction == 'B' and n > 2 and self.RAPB_num > 0:
            b_trigger_price = self.calTriggerPrice(n, 'B')
            if self.y[n] < b_trigger_price:
                self.pnl += self.y[n] - self.RAPB_start_price
                self.ax.plot([self.x[n],], [self.y[n], ], marker='x', markersize=8, color=color)
                self.initDailyParam(pos_type='B')
        if direction == 'S' and n > 2 and self.RAPS_num > 0:
            s_trigger_price =self.calTriggerPrice(n, 'S')
            if self.y[n] > s_trigger_price:
                self.pnl += self.y[n] - self.RAPS_start_price
                self.ax.plot([self.x[n],], [self.y[n], ], marker='x', markersize=8, color=color)
                self.initDailyParam(pos_type='S')



        #Open position part
        if self.RAPB_num > 0 and direction == 'B':
            return
        if self.RAPS_num > 0 and direction == 'S':
            return
        if n < 8:
            return
        h8, h7, h6, h5, h4, h3, h2, h1 = self.slope_list[n - 7 : n + 1]
        if self.count(2, 6, h1, h2):
            sig_type, diff = "RAP1", 2
        elif self.count(2, 6, h1, h2, h3) and min([h1, h2, h3]) >= 0 and h1 + h2 + h3 >= 14:
            sig_type, diff = "RAP2", 3
        elif self.count(2, 4, h1, h2, h3, h4, h5) and self.count(4, 2, h1, h2 ,h3 ,h4, h5)\
                and min([h1, h2, h3, h4, h5]) >= 0 and h1 + h2 + h3 + h4 + h5 >= 10:
            sig_type, diff = "RAP3", 4
        elif self.count(1, 4, h1, h2, h3, h4, h5, h6, h7, h8) and self.count(4, 2, h1, h2, h3, h4, h5, h6, h7, h8)\
            and self.count(7, 0, h1, h2, h3, h4, h5, h6, h7, h8) and h1 + h2 + h3 + h4 + h5 + h6 + h7 + h8 >= 12:
            sig_type, diff = "RAP4", 8
        elif self.count(7, 0, h1, h2, h3, h4, h5, h6, h7, h8) and min([h1, h2, h3, h4, h5, h6, h7, h8]) >= -2\
                and h1 + h2 + h3 + h4 + h5 + h6 + h7 + h8 >= 8:
            sig_type, diff =  "RAP5", 8
        else:
            return
        var1, var2, var3, var4 = self.previous_trend(n - diff)
        if var1 >= - 0.125 and var2 >= - 0.125 and var3 < 4.5 and var4 < 4.5:
            self.plotSignal(n, diff, color=color)
            if direction == 'B':
                self.RAPB_num = 1
                self.RAPB_sig_type = sig_type
                self.RAPB_start_pos = n
                self.RAPB_start_price = self.y[n]
                self.RAPB_peak_pos = n
                self.RAPB_peak_price = self.y[n]
                self.RAPB_strike = False
            else:
                self.RAPS_num = 1
                self.RAPS_sig_type = sig_type
                self.RAPS_start_pos = n
                self.RAPS_start_price = self.y[n]
                self.RAPS_nadir_pos = n
                self.RAPS_nadir_price = self.y[n]
                self.RAPS_strike = False

    def plotSignal(self, n, diff, color):
        self.ax.plot(self.x[n - diff: n + 1], self.y[n - diff: n + 1], color=color)
        self.ax.plot([self.x[n],], [self.y[n],], marker='o', color=color, markersize=5)
            # self.ax.text(self.x[n - diff], self.y[n - diff]- 10, str('(' + str(var1) + ',' + str(var2) + ',' + str(var3) + ',' + str(var4) +')'))


    def volitility(self,  ls):
        N = len(ls)
        assembled_ls = list()
        j = 0
        while j < N and ls[j] == 0:
            j += 1
        assembled_ls.append(ls[j])
        sign = np.sign(ls[j])
        for item in ls[j + 1: ]:
            if np.sign(item) * sign >= 0:
                assembled_ls[-1] += item
            else:
                assembled_ls.append(item)
                sign *= -1
        if len(assembled_ls) == 0:
            raise ValueError("Empty assembled list!!!")
        var_ls = list()
        for item in assembled_ls:
            if abs(item) < 10:
                var_ls.append(item)
        if len(var_ls) == 0:
            return 0
        else:
            return round(np.std(var_ls), 1)

if __name__ == "__main__":
    obj = Strategy("btc")
    obj.multi_backtest()