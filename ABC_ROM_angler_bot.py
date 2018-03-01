# ==========================
#  general python modules
# ==========================
import time
import requests
from bs4 import BeautifulSoup
import os
import numpy as np
from functools import wraps

# ==========================
# python-temegam-bot modules
# ==========================
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import telegram as telegram

# ===============================
# create necessary folders
# ===============================
if not os.path.exists('users'):
    os.makedirs('users')

# ===============================
# admin list
# ===============================
fid = open('./admin_only/admin_list.txt', 'r')
LIST_OF_ADMINS = [int(adm) for adm in fid.readline().split()]
fid.close()

# ==========================
# The following function reads the TOKEN from a file.
# This file is not incuded in the github-repo for obvious reasons
# ==========================
def read_token(filename):
    with open(filename) as f:
        token = f.readline().replace('\n', '')
    return token


# ==============================================================
# function to get current release released in Kantjer's web site
# ==============================================================
def get_current_release():
    # ABC ROM kantjer web site
    url = "http://kantjer.com/"

    # get content
    webpage = requests.get(url)

    # parse content
    soup = BeautifulSoup(webpage.text, "lxml")

    # get latest release
    index1 = str(soup).find('ABC_ROM')
    index2 = str(soup).find('.zip') + 4
    CurrentABC = str(soup)[index1:index2]

    return CurrentABC

# ========================================================
# assign a global variable inlcuding the latest release
# ========================================================
LatestABC = get_current_release()


# ==========================
# restriction decorator
# ==========================
def restricted(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in LIST_OF_ADMINS:
            print("Unauthorized access denied for {}.".format(user_id))
            bot.send_message(chat_id=update.message.chat_id, text="You are not authorized to run this command")
            return
        return func(bot, update, *args, **kwargs)
    return wrapped


# ==========================
# start - welcome message
# ==========================
def start(bot, update):
    url_download = 'http://kantjer.com/wp-content/uploads/2018/02/' + LatestABC
    url_xda = 'https://forum.xda-developers.com/custom-roms/android-builders-' \
              'collective/rom-builders-collective-t2861778'
    msg = "*Welcome to ABC-ROM_angler bot*.\n\n"
    msg += "It will notify you when an update is available for angler\n\n"
    msg += "The current release is:\n"
    msg += "[" + LatestABC + "]({})\n\n".format(url_download)
    msg += 'Changelog here:\n[http://kantjer.com/](http://kantjer.com/)\n\n'
    msg += 'XDA thread here:\n[Android Builders Collective]({})\n'.format(url_xda)

    bot.send_message(chat_id=update.message.chat_id,
                     text=msg,
                     parse_mode=telegram.ParseMode.MARKDOWN, disable_web_page_preview=True)

    # add user to database for future communications
    current_users = str(update.message.chat_id)

    # merge it to the existing database and filter duplicates
    if os.path.exists('./users/users_database.db'):
        user_db = []
        with open('./users/users_database.db', 'r') as fid:
            for line in fid:
                user_db.append(int(line))
        user_db.append(int(current_users))
        user_db = np.unique(user_db)
        np.savetxt('./users/users_database.db', user_db, fmt="%s")
    else:
        np.savetxt('./users/users_database.db', [int(current_users)], fmt="%s")


# ==========================
# help - short guide
# ==========================
def help(bot, update):
    msg = "The *ABC-ROM_angler bot* is really simple to be used.\n\n"
    msg += "You just need to activate it.\n\n"
    msg += "The bot will notify you when an update is available for angler."

    bot.send_message(chat_id=update.message.chat_id,
                     text=msg,
                     parse_mode=telegram.ParseMode.MARKDOWN, disable_web_page_preview=True)


# =====================================================
# check the current release and send message to users
# if an update is fount
# =====================================================
def check4update(bot, job):
    # global variables
    global LatestABC
    # current release
    currentABC = get_current_release()

    # check for updates
    if LatestABC != currentABC:
        # update latest release
        LatestABC = currentABC

        # build message for users
        url_xda = 'https://forum.xda-developers.com/custom-roms/android-builders-' \
                  'collective/rom-builders-collective-t2861778'

        url_download = 'http://kantjer.com/wp-content/uploads/2018/02/' + LatestABC
        msg = "*New build for ABC-ROM_angler is available:*.\n\n"
        msg += "[" + LatestABC + "]({})\n\n".format(url_download)
        msg += 'Changelog here:\n[http://kantjer.com/](http://kantjer.com/)\n'
        msg += 'XDA thread here:\n[Android Builders Collective]({})\n'.format(url_xda)

        # send message to all users (keeping track of the incative ones)
        users = np.loadtxt('./users/users_database.db').reshape(-1,)
        inactive_users = []
        for index, single_user in enumerate(users):
            chat_id = int(single_user)
            # try to send the message
            try:
                bot.send_message(chat_id=chat_id,
                                 text=msg,
                                 parse_mode=telegram.ParseMode.MARKDOWN, disable_web_page_preview=True)

            # if the user closed the bot, cacth exception and update inactive_users
            except telegram.error.TelegramError:
                inactive_users.append(index)

        # remove inactive_users and update database
        users = np.delete(users, inactive_users)
        np.savetxt('./users/users_database.db', users.astype(int), fmt="%s")


# =========================================
# restart - restart the BOT
# =========================================
@restricted
def restart(bot, update):
    bot.send_message(update.message.chat_id, "Bot is restarting...")
    time.sleep(0.2)
    os.execl(sys.executable, sys.executable, *sys.argv)


# =========================================
# bot - main
# =========================================
def main():
    # set TOKEN and initialization
    fname = './admin_only/ABC_ROM_angler_bot_token.txt'
    updater = Updater(token=read_token(fname))
    dispatcher = updater.dispatcher
    # set the time interval to check for updates (900 sec = 15 min)
    job_queue = updater.job_queue
    job_c4u = job_queue.run_repeating(check4update, interval=900, first=60)

    # /start handler
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    # /help handler
    help_handler = CommandHandler('help', help)
    dispatcher.add_handler(help_handler)

    # /r - restart the bot
    dispatcher.add_handler(CommandHandler('r', restart))

    # start the BOT
    updater.start_polling()
    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
