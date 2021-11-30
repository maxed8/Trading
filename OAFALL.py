#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 20 00:18:40 2020

@author: jackhalsey
"""
##load packages and query data into dataframe
from yahoo_fin import stock_info as si
import yfinance as yf
import numpy as np
import random
import robin_stocks as rs
from datetime import datetime, timedelta
from slack_webhook import Slack
import schedule
from apscheduler.schedulers.blocking import BlockingScheduler

slack = Slack(url='https://hooks.slack.com/services/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')

def job():
    slack_output = ''
    
    symbol = 'SPY'
    chain = rs.options.get_chains(symbol, info=None)
    dates = chain['expiration_dates']
    LexpDates = dates[1:3]
    
    
    
    for i in LexpDates:
        prev = datetime.today() - timedelta(days=1)
        prevS = prev.strftime('%Y-%m-%d')
        now = datetime.today()
        today = now.strftime('%Y-%m-%d')
        
        expDate = datetime.strptime(i, '%Y-%m-%d')
        expirationDate = expDate.strftime('%Y-%m-%d')
        diff = expDate - now
        
        SPYdata = yf.download("SPY", start = "2004-01-01" , end = today)
        VIXdata = yf.download("^VIX", start = "2004-01-01" , end = today)
        SPYdata["DPR"] = (SPYdata["Close"] - SPYdata["Open"]) / SPYdata["Open"]
        SPYdata['Date'] = SPYdata.index
        SPYdata.reset_index(drop=True,inplace = True)
        
        # add inputs CSP, CVL, DTE, LBLen
        date = prevS
        cspp = rs.stocks.get_latest_price(inputSymbols = "SPY", priceType=None, includeExtendedHours=True)
        CSP = float(cspp[0])
        CVL = si.get_live_price("^VIX")
        
        DTE = int(diff.days)
        if DTE < 6 :
            LBLen = 3000
        elif DTE < 8 :
            LBLen = 2200
        elif DTE < 10 :
            LBLen = 1500
        else : 
            LBLen = 1250
        index = SPYdata[SPYdata['Date']==date].index[0]
        LBList = SPYdata['DPR'][index-1250:index+1]
        VIXlist = VIXdata['Close'][index-1250:index+1]
        
        VIXmean = np.mean(VIXlist)
        VIXsd = np.std(VIXlist)
        
        ZCVL = (CVL - VIXmean) / VIXsd
        Vixmult = 1 + (ZCVL / 4)
        LBList_adj_df = LBList * Vixmult
        LBList_adj = []
        for num in LBList_adj_df:
            LBList_adj.append(num)
        
        # run simulation
        
        SimDist = []
        for i in range(1, 10000):
        	sample = random.choices(LBList_adj, k=DTE)
        	estimate = CSP
        	for s in sample:
        		estimate = estimate * (1 + s)
        	SimDist.append(estimate)
        
        # calculate quantiles, hi lo likelihood etc
        
        for i in range(0,6):
            lowP = .15 - (0.025*i)
            hiP = .85 + (0.025*i)
            PCR = (hiP - lowP) * 100
            Lo = np.quantile(SimDist, lowP)
            Hi = np.quantile(SimDist, hiP)
            
            # rounding and probabilities
            hi_strike = round(Hi)
            lo_strike = round(Lo)
            count = 0
            for i in SimDist:
                if lo_strike <= i <= hi_strike:
                    count += 1  
            prob_s = count / len(SimDist)
            try:
                # log into robinhood
                login = rs.login('jhalsey93@gmail.com','1561Jack!!')
                
                
                #pull options chain
                
                
                optionTypehi = 'call'
                optionTypelo = 'put'
                strikePricehi = hi_strike
                strikePricehi2 = hi_strike + 1
                
                strikePricelo = lo_strike
                strikePricelo2 = lo_strike - 1 
                
                ###iron condor price
                
                #leg 1 sell call @ histrike 
                hb1 = rs.options.get_option_market_data(symbol, expirationDate, strikePricehi, optionTypehi, info=None)
                hb10 = hb1[0]
                hbdict = hb10[0]
                SCprice = float(hbdict['mark_price'])
                
            
            #leg 2  buy call 1 strike above histrike 
                hb2 = rs.options.get_option_market_data(symbol, expirationDate, strikePricehi2, optionTypehi, info=None)
                hb20 = hb2[0]
                hb2dict = hb20[0]
                BCprice = float(hb2dict['mark_price'])
        
            
            #leg 3 sell put @ lo strike
                hb3 = rs.options.get_option_market_data(symbol, expirationDate, strikePricelo, optionTypelo, info=None)
                hb30 = hb3[0]
                hb3dict = hb30[0]
                SPprice = float(hb3dict['mark_price'])
            
            #leg 4 buy put @ lo strike - 1 
                hb4 = rs.options.get_option_market_data(symbol, expirationDate, strikePricelo2, optionTypelo, info=None)
                hb40 = hb4[0]
                hb4dict = hb40[0]
                BPprice = float(hb4dict['mark_price'])
                
                ICprice = 100 * round((SCprice - BCprice) + (SPprice - BPprice),4)
                
                
                ### Expected Value Calculation 
                
                EV = (prob_s * ICprice) - ((1-prob_s)*(100-ICprice))
            
            
                ## printouts
                print('Expiration: ',expDate)
                print('DTE: ', DTE)
                print('LBLen: ', LBLen)
                print('Low Strike: ',lo_strike)
                print('High Strike: ',hi_strike)
                print('Predicted Coverage Rate: ', PCR)
                print('Probability of Success: ',prob_s)
                
                print('Price: ', ICprice)
                print('Expected Value: ',EV)
                print()
                
                if EV > 1:
                    ev_label = 'EV: '
                    ev = str(EV)
                    expiration_label = '\nExpiration: '
                    expiration = str(expDate)
                    low_strike_label = '\nLow Strike: '
                    low_strike = str(lo_strike)
                    high_strike_label = '\nHigh Strike: '
                    high_strike = str(hi_strike)
                    pcr_label = '\nPCR: '
                    pcr = str(PCR)
                    p_success_label = '\nProbability of Success: '
                    p_success = str(prob_s)
                    output = ev_label + ev + expiration_label + expiration + low_strike_label + low_strike + high_strike_label + high_strike + pcr_label + pcr + p_success_label + p_success + '\n------------------------------------------------------\n'
                    slack_output = slack_output + output
            except:
                pass
    
    slack.post(text=slack_output)
    
# Run every 10 minutes from 9:30am to 4:10pm on weekdays 
sched = BlockingScheduler()
sched.add_job(job, 'interval', minutes=10) 
schedule.every().monday.at("09:30").do(sched.start())
schedule.every().monday.at("16:10").do(sched.shutdown())
schedule.every().tuesday.at("09:30").do(sched.start())
schedule.every().tuesday.at("16:10").do(sched.shutdown())
schedule.every().wednesday.at("09:30").do(sched.start())
schedule.every().wednesday.at("16:10").do(sched.shutdown())
schedule.every().thursday.at("09:30").do(sched.start())
schedule.every().thursday.at("16:10").do(sched.shutdown())
schedule.every().friday.at("09:30").do(sched.start())
schedule.every().friday.at("16:10").do(sched.shutdown())



        

