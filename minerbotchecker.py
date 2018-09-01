from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, JobQueue
import logging
import http.client
import json
import time
import ccxt

# ==================== NOTABLE VARIABLES =================================
# telegram token returned by BotFather
TELEGRAMTOKEN = "336697024:AAG2ZvoudCPSjzabd2gyy8jZGcARxB46EDg"
# get this url from ethermine -> json api section
ZELCASHURL = "zelcash.voidr.net"
APIURL = "/api/worker_stats?t1WDdAfRWbY9utuAxN1497SJwqG8oRKPnbu"
# if number of active workers drop less than this number bot will notify you.
# so if you have 3 rigs, WNUM should set to 3!
WNUM = 1
# every X minutes bot will check that WNUM workers are up on ethermine
# i suggest to set this to 30 minutes
WCHECKINGMINUTES = 30
BROKERMINUTES = 360
BALANCEMINUTES = 1 
# this list contains user_id of user that are allowed to get response from the bot
ALLOWEDUSERID = [175666244]
ALERTLOSS = -0.0005
LOSSMARGIN = 0.1
# log filename
LOGPATH = "/home/bot/minerbot/bot.log"
BROKERDBFILE = "/home/bot/minerbot/broker.txt"
EXTRABOT = 1
PROFITSELL = 0.0001
# ========================================================================


logging.basicConfig(
    filename=LOGPATH,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

logger = logging.getLogger(__name__)

broker = ccxt._1broker({
        'apiKey': 'A028e93dd48f12b1aedeb3e17dd4614b',
})

def extramonitor(bot, update, args):
    brokerBalance = broker.fetch_balance()
    op = brokerBalance['info']['positions_open']
    positionfound = False
    global EXTRABOT
    global PROFITSELL
    if args[0] == "1": 
     EXTRABOT = 1
     PROFITSELL = 0.0001
    else:
     for buf in op:
        if args[0] == buf['position_id']: 
	   positionfound = True
           posid = args[0]
           symbid = buf['symbol']
     if positionfound:
           toSend = "Start Monitoring closely for positive value for:\nPos ID {}\nSymbol: {}\n".format(posid,symbid)
    	   EXTRABOT = args[0]
           PROFITSELL = args[1]
     else:
           toSend = "Position ID: {} was not found in your open positions".format(args[0])

     for usr in ALLOWEDUSERID:
                bot.send_message(usr, text=toSend)

def extracheckprofit(bot, job):
    global EXTRABOT
    global PROFITSELL
    if EXTRABOT != 1:
       brokerBalance1 = broker.fetch_balance()
       op1 = brokerBalance1['info']['positions_open']
       for buf in op1:
          if buf['position_id'] == EXTRABOT:
	    if buf['profit_loss'] >= PROFITSELL:
   	      toSend = "### - Price Hit Target Monitoring: {} - ###\n".format(buf['profit_loss'])
	      for usr in ALLOWEDUSERID: bot.send_message(usr, text=toSend)
 	      EXTRABOT = 1    

def checkBalance(bot, job):
    brokerBalance = broker.fetch_balance()
    op = brokerBalance['info']['positions_open']
    brokerdata ={}
    brokerlowestprice = {}
    with open(BROKERDBFILE, "r") as f:
           for line in f:
                if len(line.split()) == 0: continue
                posid, profitloss, lowestprice = line.split(',')
                brokerdata[posid] = float(profitloss)
                brokerlowestprice[posid] = float(lowestprice)

    f = open(BROKERDBFILE,"w+")
    
    for buf in op:
        curprice = float(buf['profit_loss'])
	posid = str(buf['position_id'])
        toSend = ""
        #if abs(curprice) > abs(ALERTLOSS):
	if brokerdata.has_key(posid):
	 #      if abs(curprice) > abs(brokerdata[posid]):
         #         if abs(curprice) > abs(brokerlowestprice[posid]):
         #   	    toSend = "!! ALERT !!\nPosition ID: {}\nSymbol: {}\nLoss: {}\n\n".format(
	 #	       buf['position_id'],
	 #	       buf['symbol'],
	 #	       buf['profit_loss'])   
         #            for usr in ALLOWEDUSERID: bot.send_message(usr, text=toSend)
         toSend = ""
	else:
           toSend = "New Position opened\nPosition ID: {}\nSymbol: {}\nLoss: {}\n\n".format(
                     buf['position_id'],
                     buf['symbol'],
                     buf['profit_loss'])
           for usr in ALLOWEDUSERID: bot.send_message(usr, text=toSend)

        if brokerlowestprice.has_key(posid):
           if abs(curprice) < abs(brokerlowestprice[posid]):
              curprice = brokerlowestprice[posid]

	f.write("{},{},{}\r\n".format(str(buf['position_id']),str(buf['profit_loss']),str(curprice)))
    
    f.close()

def checkBroker(bot, job):
    toSend = ""
    brokerBalance = broker.fetch_balance()
    username = brokerBalance['info']['username']
    networth = brokerBalance['info']['net_worth']
    op = brokerBalance['info']['positions_open']
    toSend = "Username: {}\nNet Worth: {}\n\n".format(username, networth)
    for buf in op:
         toSend += "ID: {}\nSymbol: {}\nProfit Loss: {}\nValue: {}\nDate Creation: {}\n\n".format(
                    buf['position_id'],
		    buf['symbol'],
                    buf['profit_loss'],
                    buf['value'],
                    buf['date_created'])
    for usr in ALLOWEDUSERID:
                bot.send_message(usr, text=toSend)

def checkWorkers(bot, job):
    conn = http.client.HTTPSConnection(ZELCASHURL)
    conn.request("GET", APIURL)
    res = conn.getresponse()
    toSend = ""
    if res.status == 200:
        buf = json.loads(res.read().decode("utf-8"))
        #s = buf['minerStats']
        #activeWorkers = s['activeWorkers']
        activeWorkers = buf['workers']
        activeWorker=0
        for iterator in activeWorkers:
           activeWorker = activeWorker+1

        if activeWorker < WNUM:
            toSend = "WARNING: Seems like some of your workers are offline ({}/{})".format(activeWorkers, WNUM)
            for usr in ALLOWEDUSERID:
                bot.send_message(usr, text=toSend)
    else:
        toSend = "Unable to reach voidr API site: {}".format(res.reason)
        for usr in ALLOWEDUSERID:
            bot.send_message(usr, text=toSend)


#def status(bot, update):
#    if update.message.chat_id in ALLOWEDUSERID:
#        conn = http.client.HTTPSConnection("zelcash.voidr.net")
#        conn.request("GET", APIURL)
#        res = conn.getresponse()
#        toSend = ""
#        if res.status == 200:
#            buf = json.loads(res.read().decode("utf-8"))
#            aus = buf['minerStats']
#            toSend = "Addr: {}\nHash: {}\nreportedHash: {}\nnWorkers: {}\nShares (v/s/i): {}/{}/{}".format(
#                buf['address'], buf['hashRate'], buf['reportedHashRate'], aus['activeWorkers'], aus['validShares'], aus['staleShares'], aus['invalidShares'])
#        else:
#            toSend = "Unable to reach voidr API site: {}".format(res.reason)
#        update.message.reply_text(toSend)
#        conn.close()
#    else:
#        logger.info("{} tried to contact me (comm: {})".format(
#            update.message.from_user, update.message.text))

def workers(bot, update):
    if update.message.chat_id in ALLOWEDUSERID:
        conn = http.client.HTTPSConnection(ZELCASHURL)
        conn.request("GET", APIURL)
        res = conn.getresponse()
        toSend = ""
        if res.status == 200:
            buf = json.loads(res.read().decode("utf-8"))
            w = buf['workers']
            for iterator in w:
                buf = w[iterator]
                toSend += "Worker {}\nHash: {}\nreportedHash: {}\nShares (s/i): {}/{}\n\n".format(
                    buf['name'], buf['hashrate'], buf['hashrateString'], buf['shares'], buf['invalidshares'])
        else:
            toSend = "Unable to reach voidr API site: {}".format(res.reason)
        update.message.reply_text(toSend)
        conn.close()
    else:
        logger.info("{} tried to contact me (comm: {})".format(
            update.message.from_user, update.message.text))

def brokerstatus(bot, update):
    if update.message.chat_id in ALLOWEDUSERID:
 	brokerBalance = broker.fetch_balance()
	username = brokerBalance['info']['username']
	networth = brokerBalance['info']['net_worth']
	op = brokerBalance['info']['positions_open']
	toSend = "Username: {}\nNet Worth: {}\n\n".format(username, networth)
	for buf in op:
		toSend += "ID: {}\nSymbol: {}\nProfit Loss: {}\nValue: {}\nDate Creation: {}\n\n".format(
		    buf['position_id'],
		    buf['symbol'], 
                    buf['profit_loss'], 
                    buf['value'], 
                    buf['date_created'])
	update.message.reply_text(toSend)
    else:
	logger.info("{} tried to contact me (comm: {})".format(
            update.message.from_user, update.message.text))

def help(bot, update):
    if update.message.chat_id in ALLOWEDUSERID:
        toSend = "Command List\n\n/workers - list workers\n/brokerstatus - list all the 1broker open positions\n/extramonitoring (POSID) (VALUE) - extra monitoring for POSID if value to break VALUE\n/extramonitor 1 - reset to no extra monitoring\nNOTE: this bot automatically checks for workers crash!"
        update.message.reply_text(toSend)
    else:
        logger.info("{} tried to contact me (comm: {})".format(
            update.message.from_user, update.message.text))

def ping(bot, update):
    if update.message.chat_id in ALLOWEDUSERID:
        update.message.reply_text("pong")
    else:
        logger.info("{} tried to contact me (comm: {})".format(
            update.message.from_user, update.message.text))


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def main():
    updater = Updater(TELEGRAMTOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("workers", workers))
#    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("ping", ping))
    dp.add_handler(CommandHandler("brokerstatus", brokerstatus))
    dp.add_handler(CommandHandler("extramonitor", extramonitor, pass_args=True))

    dp.job_queue.run_repeating(
        checkWorkers, (WCHECKINGMINUTES * 60))

    dp.job_queue.run_repeating(
	checkBroker, (BROKERMINUTES * 60))

    dp.job_queue.run_repeating(
        checkBalance, (BALANCEMINUTES *60 ))

    dp.job_queue.run_repeating(
        extracheckprofit, (5 ))


    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
