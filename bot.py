import json
import logging
import random
import re
import time
import random
import string

import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, Bot, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, Filters, MessageHandler, \
    ConversationHandler
from solona import create_wallet, get_wallet_balance, send_sol
from dexscreener import get_token_details
import config
import qrcode
from io import BytesIO

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

# Replace with your Telegram bot token and chat ID
TELEGRAM_BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
BOT_LINK = config.BOT_LINK

AMOUNT, ADDRESS = range(2)
AUTOBUY_AMT, BUY_LEFT, BUY_RIGHT, SELL_LEFT, SELL_RIGHT, BUY_SLIPPAGE, SELL_SLIPPAGE, MAX_PRICE_IMPACT = range(8)

refs = {
    'user1': ['ref1', 'ref2'],
    'user2': '',
}

refcodes = {
    'user1': 'abcd12'
}

gas_fees = {
    'Medium': "0.00100",
    'High': '0.00500',
    'Very High': '0.0100'
}

mev = ["Secure", "Turbo"]
trans_priority = ['Medium', 'High', 'Very High']


def convert_number_to_k_m(number):
    if number >= 1000000:
        return f"{number / 1000000:.1f}M"
    elif number >= 1000:
        return f"{number / 1000:.1f}K"
    else:
        return str(number)


def generate_qr_code(data: str) -> BytesIO:
    qr_bytes = BytesIO()
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(qr_bytes, format='PNG')
    qr_bytes.seek(0)

    return qr_bytes


def generate_settings_msg() -> str:
    msg = (
        f"*Settings:*\n\n"
        "*GENERAL SETTINGS*\n"
        "*Language:* Shows the current language. Tap to switch between available languages.\n"
        "*Minimum Position Value:* Minimum position value to show in portfolio. You can edit this value to whatever amount you like. Tokens whose value is below this threshold,will be hidden from view.\n\n"
        "*AUTO BUY*\n"
        "Immediately buy when you paste a token's contract address. Tap on the left side to enable or disable this feature and tap on the right side to set how much Solana you want to spend on auto-buys.\n\n"
        "*BUTTONS CONFIG*\n"
        "You can customize your buy and sell buttons for buy tokens and manage positions. Tap to edit the values. When you set values for the left and right 'buy' buttons,be sure that you have a little bit more SOL in your Memebot wallet than those values.For example,if you set the value of left 'buy' button at 1 SOL,you should have around 1.10 SOL in your Memebot wallet for the left 'buy' button to work.The extra 0.10 SOL will go towards Gas fee,slippage,DEX fee and Memebot's fee.The same is applicable to the right 'buy' button.\n\n"
        "*SLIPPAGE CONFIG*\n"
        "Here you can customize your slippage settings for buys and sells. Tap to edit the values.Ideally the 'buy' side slippage should be between 2-5% and 'sell' side slippage should be 5-10%.\n\n"
        "*Max Price Impact*\n"
        "Max Price Impact is to protect against trades in extremely illiquid pools.\n\n"
        "*MEV PROTECT*\n"
        "MEV Protect accelerates your transactions and protect against frontruns to make sure you get the best price possible.\n"
        "*Turbo:* Memebot will use MEV Protect, but if unprotected sending is faster it will use that instead.\n"
        "*Secure:* Transactions are guaranteed to be protected. This is the ultra secure option, but may be slower.\n\n"
        "*TRANSACTION PRIORITY*\n"
        "Increase your transaction priority to improve transaction speed. Tap to set the priority to 'medium','high',or 'very high' as per your choice.\n\n"
        "*SELL PROTECTION*\n"
        "If this feature is enabled,100% sell commands will require an additional confirmation step.  Tap to enable or disable this feature.\n\n"

    )
    msgV2 = escape_markdown_v2(msg)
    return msgV2


def update_settings_msg(update: Update, context: CallbackContext):
    msg_id = context.user_data['settings_id']
    chat_id = context.user_data['chat_id']
    msgV2 = generate_settings_msg()
    reply_markup = generate_settings_keyboard(context)
    context.bot.edit_message_text(msgV2, message_id=msg_id, chat_id=chat_id, reply_markup=reply_markup,
                                  parse_mode=ParseMode.MARKDOWN_V2)


def generate_random_string(length):
    alphanumeric_chars = string.ascii_letters + string.digits
    return ''.join(random.choice(alphanumeric_chars) for _ in range(length))


def escape_markdown_v2(text):
    """
    Escapes characters in a string to make it suitable for Telegram Markdown V2.
    """
    escape_chars = r'_[]()~>#+-=|{}.!'
    escaped_text = re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)
    return escaped_text


def start(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    username = user.username
    # print(username)

    args = context.args

    if args and args[0].startswith('ref_'):
        # update.message.reply_text(f'Deep link with ref_ detected! {args[0]}')

        refferal_username = refcodes[args[0]]
        if refs[refferal_username] and isinstance(refs[refferal_username], list):
            refs[refferal_username].append(username)

    public_key, secret_key = create_wallet()
    context.user_data["public_key"] = public_key
    context.user_data["private_key"] = secret_key
    context.user_data["balance"] = get_wallet_balance(public_key)
    print('balance ', get_wallet_balance(public_key))

    ref_code = 'ref_' + generate_random_string(6)
    refcodes[ref_code] = username
    refs[username] = []
    context.user_data["ref_code"] = ref_code
    context.user_data["public_key"] = public_key

    # initial settings
    context.user_data["autobuy_enabled"] = False
    context.user_data["autobuy_amt"] = "0.010"
    context.user_data["sell_protection_enabled"] = False
    context.user_data["sell_left"] = 25
    context.user_data["sell_right"] = 100
    context.user_data["buy_left"] = "0.030"
    context.user_data["buy_right"] = "1.0"
    context.user_data["sell_slip"] = 5
    context.user_data["buy_slip"] = 2
    context.user_data["transaction_priority"] = trans_priority[0]
    context.user_data["max_price_impact"] = 25
    context.user_data["mev_protect"] = mev[0]

    welcome_message = (
        f"*Welcome to MEMEBot*\n\n"
        f"*What can this bot do?*\n\n"
        "Using this bot you can trade(buy and sell) any Solana memecoin, right inside your Telegram account.The bot executes trades lightening-fast and our fees is the LOWEST(only 0.5%) among all the Solana trading bots.\n\n"
        f"Use /home to open the main menu and start using all our features-fast trades,new token alerts,trade tracking and PnL(profit and loss) in a single dashboard.\n\n"
        f"Our links:\n\n"
        "Website: https://memebot.pro\nTwitter: https://x.com/memebot2024\nTelegram: https://t.me/+t7TU1G83KA4yZjFl"
    )

    msgv2 = escape_markdown_v2(welcome_message)

    keyboard = [
        [InlineKeyboardButton("Buy", callback_data="buy"),
         InlineKeyboardButton("Sell", callback_data="sell")],
        [InlineKeyboardButton("Help", callback_data="help"),
         InlineKeyboardButton("Alerts", callback_data="alerts")],
        [InlineKeyboardButton("Refer Friends", callback_data="referrals"),
         InlineKeyboardButton("Wallet", callback_data="wallet")],
        [InlineKeyboardButton("Settings", callback_data="settings"),
         InlineKeyboardButton("Refresh", callback_data="refresh")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(msgv2, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)


def home(update: Update, context: CallbackContext) -> None:
    public_key = context.user_data.get('public_key')

    msg1 = (
        f"*Welcome to Memebot!*\n\n"
        f"Enjoy fast,smooth and effortless crypto trading right inside your Telegram account!\n\n"
        f"You currently have no SOL in your wallet. To start trading, deposit SOL to your Memebot wallet address:\n\n"
        f"`{public_key}`"
        "(Tap to copy)\n\n"
        "Once done, tap refresh and your balance will appear here.\n\n"
        "To start trading using Memebot,purchase any Solana token listed on https://dexscreener.com .\n\n"
        "To buy a token just enter a ticker,token's contract address, or paste a Dexscreener URL, and you will see a Buy dashboard pop up where you can choose how much you want to buy.\n\n"
        "For more info on your Memebot wallet and to retrieve your private key, tap the wallet button below. User funds are perfectly safe on Memebot, but if you expose your private key we can't protect you! Please copy and save your private key at a secure place and never share it with anyone."
    )

    balance = context.user_data["balance"]

    msg2 = (
        f"*Welcome to Memebot!*\n\n"
        "Enjoy fast,smooth and effortless crypto trading right inside your Telegram account!\n\n"
        f"You currently have a balance of {balance} SOL, but no open positions.\n\n"
        "To start trading using Memebot,purchase any Solana token listed on https://dexscreener.com .\n\n"
        "To buy a token just enter a ticker,token's contract address, or paste a Dexscreener URL, and you will see a Buy dashboard pop up where you can choose how much you want to buy.\n\n"
        "Advanced traders can enable Auto Buy in their settings. When enabled, Memebot will instantly buy any token you enter with a fixed amount that you set. This is disabled by default."
    )

    keyboard = [
        [InlineKeyboardButton("Buy", callback_data="buy"),
         InlineKeyboardButton("Sell", callback_data="sell")],
        [InlineKeyboardButton("Help", callback_data="help"),
         InlineKeyboardButton("Alerts", callback_data="alerts")],
        [InlineKeyboardButton("Refer Friends", callback_data="referrals"),
         InlineKeyboardButton("Wallet", callback_data="wallet")],
        [InlineKeyboardButton("Settings", callback_data="settings"),
         InlineKeyboardButton("Refresh", callback_data="refresh")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if float(balance) > 0:
        msgV2 = escape_markdown_v2(msg2)
        update.message.reply_text(msgV2, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        msgV2 = escape_markdown_v2(msg1)
        update.message.reply_text(msgV2, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)


def help(update: Update, context: CallbackContext) -> None:
    message = ''
    if update.message:
        message = update.message
    elif update.callback_query:
        message = update.callback_query.message

    msg = (
        f"*Help:*\n\n"
        "*Which tokens can I trade?*\n"
        "Any SOLANA token listed on https://dexscreener.com.\n\n"
        "*How can I see how much money I've made from referrals?*\n"
        "Tap the referrals button or type /referrals to see your affiliate earnings!\n\n"
        "*How do I create a new wallet on MEMEbot?*\n"
        "Tap the Wallet button or type /wallet, and you'll be able to configure your new wallet!\n\n"
        "*Is MEMEbot free? How much do I pay for transactions?*\n"
        "Memebot is completely free! We charge 0.5% on transactions, and keep the bot free so that anyone can use it.Our transaction fees is the LOWEST among all the SOLANA trading bots.\n\n"
        "*Why is my Net Profit lower than expected?*\n"
        "Your Net Profit is calculated after deducting all associated costs, including Price Impact, gas fee, Dex Fees, and a 0.5% Memebot fee. This ensures the figure you see is what you actually receive, accounting for all transaction-related expenses.\n\n"
        "Further questions? Need help? Join our Telegram support group: \n"
        "https://t.me/+t7TU1G83KA4yZjFl"
    )

    msgV2 = escape_markdown_v2(msg)

    keyboard = [
        [InlineKeyboardButton("Close", callback_data='close')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message.reply_text(msgV2, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)


def referrals(update: Update, context: CallbackContext) -> None:
    ref_code = context.user_data.get('ref_code')

    keyboard = [
        [InlineKeyboardButton("QR Code", callback_data='qrcode'), InlineKeyboardButton("Close", callback_data='close')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    no_of_ref = 0
    message = ''

    if update.message:
        user = update.message.from_user
        username = user.username
        no_of_ref = len(refs[username])
        message = update.message
    elif update.callback_query:
        username = update.effective_user.username
        no_of_ref = len(refs[username])
        message = update.callback_query.message

    msg = (
        "*Referrals*\n\n"
        "Refer people to our bot and earn a cool 25% commission LIFETIME on all the fees generated through them.Our top affiliates are making 4-5 figures per month by promoting our bot.Join them now and enjoy passive income for life!\n\n"
        f"Your Referrer link is: `{BOT_LINK}?start={ref_code}`\n\n"
        f"Referrals: *{no_of_ref}*\n\n"
        "Lifetime commissions earned: *0.00 SOL ($0.00)*\n\n"
        "All the affiliate commissions are deposited to your Memebot wallet instantly,once your referred customers make a trade.\n\n"
        "Send your family,friends,co-workers or anyone you know to your referrer link and earn 25% commission *lifetime* on all the fees generated through them."
    )
    msg_v2 = escape_markdown_v2(msg)
    message.reply_text(msg_v2, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)


def chat(update: Update, context: CallbackContext) -> None:
    welcome_message = (
        "Join the discussion, share bugs and feature requests in our Telegram group:\n"
        "[https://t\.me/\+t7TU1G83KA4yZjFl](https://t.me/+t7TU1G83KA4yZjFl)"
    )
    update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN_V2)


def handle_wallets(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = update.effective_user.id

    public_key = context.user_data.get('public_key')
    balance = context.user_data["balance"]
    keyboard = [
        [InlineKeyboardButton("View on Solscan", url=f"https://solscan.io/account/{public_key}"),
         InlineKeyboardButton("Deposit Sol", callback_data="deposit")],
        [InlineKeyboardButton("Withdraw all SOL", callback_data="withdraw_all"),
         InlineKeyboardButton("Withdraw X SOL", callback_data="withdraw_x")],
        [InlineKeyboardButton("Export Private Key", callback_data=f"export_secret"),
         InlineKeyboardButton("Reset Wallet", callback_data=f"reset_wallet")],
        [InlineKeyboardButton("Refresh", callback_data=f"refresh_wallet")],
        [InlineKeyboardButton("Close", callback_data=f"close")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    msgV2 = escape_markdown_v2(
        f"*Your Wallet*:\n\n Address: `{public_key}`\nBalance: {balance}\n\n Tap to copy the address and send SOL to deposit")
    query.message.reply_text(msgV2,
                             reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)


def handle_wallet_refresh(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    public_key = context.user_data.get('public_key')
    balance = context.user_data["balance"]
    updated_balance = get_wallet_balance(public_key)
    print('refresh balance', updated_balance, 'previous balance', balance)

    keyboard = [
        [InlineKeyboardButton("View on Solscan", url=f"https://solscan.io/account/{public_key}"),
         InlineKeyboardButton("Deposit Sol", callback_data="deposit")],
        [InlineKeyboardButton("Withdraw all SOL", callback_data="withdraw_all"),
         InlineKeyboardButton("Withdraw X SOL", callback_data="withdraw_x")],
        [InlineKeyboardButton("Export Private Key", callback_data=f"export_secret"),
         InlineKeyboardButton("Reset Wallet", callback_data=f"reset_wallet")],
        [InlineKeyboardButton("Refresh", callback_data=f"refresh_wallet")],
        [InlineKeyboardButton("Close", callback_data=f"close")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if updated_balance != balance:
        context.user_data["balance"] = updated_balance
        msgV2 = escape_markdown_v2(
            f"*Your Wallet*:\n\n Address: `{public_key}`\nBalance: {updated_balance}\n\n Tap to copy the address and send SOL to deposit")
        query.edit_message_text(msgV2, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)


def generate_settings_keyboard(context: CallbackContext):
    autobuy_enabled = context.user_data["autobuy_enabled"]
    autobuy_amt = context.user_data["autobuy_amt"]
    sell_protection_enabled = context.user_data["sell_protection_enabled"]
    sell_left = context.user_data["sell_left"]
    sell_right = context.user_data["sell_right"]
    buy_left = context.user_data["buy_left"]
    buy_right = context.user_data["buy_right"]
    sell_slip = context.user_data["sell_slip"]
    buy_slip = context.user_data["buy_slip"]
    transaction_priority = context.user_data["transaction_priority"]
    max_price_impact = context.user_data["max_price_impact"]
    mev_protect = context.user_data["mev_protect"]

    keyboard = [
        [InlineKeyboardButton("---AUTO BUY---", callback_data='autobuy')],
        [
            InlineKeyboardButton(
                f"🟢 Enabled" if autobuy_enabled else f"🔴 Disabled",
                callback_data='toggle'
            ),
            InlineKeyboardButton(f"✏️ {autobuy_amt} SOL", callback_data='autobuy_amt')
        ],
        [InlineKeyboardButton("---BUY BUTTONS CONFIG---", callback_data='autobuy')],
        [
            InlineKeyboardButton(f"✏️ Left: {buy_left} SOL", callback_data='buy_left'),
            InlineKeyboardButton(f"✏️ Right: {buy_right} SOL", callback_data='buy_right')
        ],
        [InlineKeyboardButton("---SELL BUTTONS CONFIG---", callback_data='autobuy')],
        [
            InlineKeyboardButton(f"✏️ Left: {sell_left}%", callback_data='sell_left'),
            InlineKeyboardButton(f"✏️ Right: {sell_right}%", callback_data='sell_right')
        ],
        [InlineKeyboardButton("---SLIPPAGE CONFIG---", callback_data='slippage')],
        [
            InlineKeyboardButton(f"✏️ Buy: {buy_slip}%", callback_data='buy_slippage'),
            InlineKeyboardButton(f"✏️ Sell: {sell_slip}%", callback_data='sell_slippage')
        ],
        [InlineKeyboardButton(f"✏️ Max Price Impact: {max_price_impact}%", callback_data='maxprice_impact')],
        [InlineKeyboardButton("---MEV PROTECT---", callback_data='mev')],
        [InlineKeyboardButton(f"↔️ {mev_protect}", callback_data='mev_protect')],
        [InlineKeyboardButton("---TRANSACTION PRIORITY---", callback_data='mev')],
        [InlineKeyboardButton(f"↔️ {transaction_priority}", callback_data='priority'),
         InlineKeyboardButton(f"✏️ {gas_fees[transaction_priority]} SOL", callback_data='gas_fees')],
        [InlineKeyboardButton("---SELL PROTECTION---", callback_data='autobuy')],
        [
            InlineKeyboardButton(
                f"🟢 Enabled" if sell_protection_enabled else f"🔴 Disabled",
                callback_data='toggle2'
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def settings(update: Update, context: CallbackContext) -> None:
    global gas_fees
    message = ''
    if update.message:
        message = update.message
    elif update.callback_query:
        message = update.callback_query.message

    msg = (
        f"*Settings:*\n\n"
        "*GENERAL SETTINGS*\n"
        "*Language:* Shows the current language. Tap to switch between available languages.\n"
        "*Minimum Position Value:* Minimum position value to show in portfolio. You can edit this value to whatever amount you like. Tokens whose value is below this threshold,will be hidden from view.\n\n"
        "*AUTO BUY*\n"
        "Immediately buy when you paste a token's contract address. Tap on the left side to enable or disable this feature and tap on the right side to set how much Solana you want to spend on auto-buys.\n\n"
        "*BUTTONS CONFIG*\n"
        "You can customize your buy and sell buttons for buy tokens and manage positions. Tap to edit the values. When you set values for the left and right 'buy' buttons,be sure that you have a little bit more SOL in your Memebot wallet than those values.For example,if you set the value of left 'buy' button at 1 SOL,you should have around 1.10 SOL in your Memebot wallet for the left 'buy' button to work.The extra 0.10 SOL will go towards Gas fee,slippage,DEX fee and Memebot's fee.The same is applicable to the right 'buy' button.\n\n"
        "*SLIPPAGE CONFIG*\n"
        "Here you can customize your slippage settings for buys and sells. Tap to edit the values.Ideally the 'buy' side slippage should be between 2-5% and 'sell' side slippage should be 5-10%.\n\n"
        "*Max Price Impact*\n"
        "Max Price Impact is to protect against trades in extremely illiquid pools.\n\n"
        "*MEV PROTECT*\n"
        "MEV Protect accelerates your transactions and protect against frontruns to make sure you get the best price possible.\n"
        "*Turbo:* Memebot will use MEV Protect, but if unprotected sending is faster it will use that instead.\n"
        "*Secure:* Transactions are guaranteed to be protected. This is the ultra secure option, but may be slower.\n\n"
        "*TRANSACTION PRIORITY*\n"
        "Increase your transaction priority to improve transaction speed. Tap to set the priority to 'medium','high',or 'very high' as per your choice.\n\n"
        "*SELL PROTECTION*\n"
        "If this feature is enabled,100% sell commands will require an additional confirmation step.  Tap to enable or disable this feature.\n\n"

    )

    msgV2 = escape_markdown_v2(msg)
    reply_markup = generate_settings_keyboard(context)
    msg = message.reply_text(msgV2, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
    context.user_data['settings_id'] = msg.message_id
    context.user_data['chat_id'] = msg.chat_id


def change_settings_button(update: Update, context: CallbackContext):
    global gas_fees
    query = update.callback_query
    query.answer()

    msg = (
        f"*Settings:*\n\n"
        "*GENERAL SETTINGS*\n"
        "*Language:* Shows the current language. Tap to switch between available languages.\n"
        "*Minimum Position Value:* Minimum position value to show in portfolio. You can edit this value to whatever amount you like. Tokens whose value is below this threshold,will be hidden from view.\n\n"
        "*AUTO BUY*\n"
        "Immediately buy when you paste a token's contract address. Tap on the left side to enable or disable this feature and tap on the right side to set how much Solana you want to spend on auto-buys.\n\n"
        "*BUTTONS CONFIG*\n"
        "You can customize your buy and sell buttons for buy tokens and manage positions. Tap to edit the values. When you set values for the left and right 'buy' buttons,be sure that you have a little bit more SOL in your Memebot wallet than those values.For example,if you set the value of left 'buy' button at 1 SOL,you should have around 1.10 SOL in your Memebot wallet for the left 'buy' button to work.The extra 0.10 SOL will go towards Gas fee,slippage,DEX fee and Memebot's fee.The same is applicable to the right 'buy' button.\n\n"
        "*SLIPPAGE CONFIG*\n"
        "Here you can customize your slippage settings for buys and sells. Tap to edit the values.Ideally the 'buy' side slippage should be between 2-5% and 'sell' side slippage should be 5-10%.\n\n"
        "*Max Price Impact*\n"
        "Max Price Impact is to protect against trades in extremely illiquid pools.\n\n"
        "*MEV PROTECT*\n"
        "MEV Protect accelerates your transactions and protect against frontruns to make sure you get the best price possible.\n"
        "*Turbo:* Memebot will use MEV Protect, but if unprotected sending is faster it will use that instead.\n"
        "*Secure:* Transactions are guaranteed to be protected. This is the ultra secure option, but may be slower.\n\n"
        "*TRANSACTION PRIORITY*\n"
        "Increase your transaction priority to improve transaction speed. Tap to set the priority to 'medium','high',or 'very high' as per your choice.\n\n"
        "*SELL PROTECTION*\n"
        "If this feature is enabled,100% sell commands will require an additional confirmation step.  Tap to enable or disable this feature.\n\n"
    )

    msgV2 = escape_markdown_v2(msg)

    autobuy_enabled = context.user_data["autobuy_enabled"]
    sell_protection_enabled = context.user_data["sell_protection_enabled"]
    transaction_priority = context.user_data["transaction_priority"]
    mev_protect = context.user_data["mev_protect"]

    if query.data == 'toggle':
        autobuy_enabled = not autobuy_enabled
        context.user_data["autobuy_enabled"] = autobuy_enabled
        msg = "Auto Buy Enabled" if autobuy_enabled else "Auto Buy Disabled"
        query.message.reply_text(msg)
    elif query.data == 'toggle2':
        sell_protection_enabled = not sell_protection_enabled
        context.user_data["sell_protection_enabled"] = sell_protection_enabled
        msg = "Sell Protection Enabled" if sell_protection_enabled else "Sell Protection Disabled"
        query.message.reply_text(msg)
    elif query.data == 'priority':

        if transaction_priority == trans_priority[0]:
            transaction_priority = trans_priority[1]
        elif transaction_priority == trans_priority[1]:
            transaction_priority = trans_priority[2]
        else:
            transaction_priority = trans_priority[0]

        context.user_data["transaction_priority"] = transaction_priority
        msg = f"Transaction Priority set to {transaction_priority}"
        query.message.reply_text(msg)
    elif query.data == 'mev_protect':
        if mev_protect == mev[0]:
            mev_protect = mev[1]
        else:
            mev_protect = mev[0]

        context.user_data["mev_protect"] = mev_protect
        msg = f"MEV Protect set to {mev_protect}"
        query.message.reply_text(msg)

    reply_markup = generate_settings_keyboard(context)
    query.edit_message_text(msgV2, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)


def edit_settings_button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data == 'autobuy_amt':
        query.message.reply_text(text="Enter new autobuy amount: (in SOL)\n Example:0.005")
        return AUTOBUY_AMT
    elif query.data == 'buy_left':
        query.message.reply_text(text="Enter new buy left amount: (in SOL)\n Example:0.005")
        return BUY_LEFT
    elif query.data == 'buy_right':
        query.message.reply_text(text="Enter new buy right amount: (in SOL)\n Example:0.005")
        return BUY_RIGHT
    elif query.data == 'sell_left':
        query.message.reply_text(text="Enter new sell left percentage: (0 - 100)\n Example:25")
        return SELL_LEFT
    elif query.data == 'sell_right':
        query.message.reply_text(text="Enter new sell right percentage: (0 - 100)\n Example:55")
        return SELL_RIGHT
    elif query.data == 'buy_slippage':
        query.message.reply_text(text="Enter new buy slippage percentage: (0 - 100)\n Example:2")
        return BUY_SLIPPAGE
    elif query.data == 'sell_slippage':
        query.message.reply_text(text="Enter new sell slippage percentage: (0 - 100)\n Example:5")
        return SELL_SLIPPAGE
    elif query.data == 'maxprice_impact':
        query.message.reply_text(text="Enter new max price impact percentage: (0 - 100)\n Example:25")
        return MAX_PRICE_IMPACT


def change_autobuy_amt(update: Update, context: CallbackContext):
    autobuy_amt = float(update.message.text)
    context.user_data["autobuy_amt"] = autobuy_amt
    update.message.reply_text(f"Autobuy amount updated to {autobuy_amt} SOL.")
    update_settings_msg(update, context)
    return ConversationHandler.END


def change_buy_left(update: Update, context: CallbackContext):
    buy_left = float(update.message.text)
    context.user_data["buy_left"] = buy_left
    update.message.reply_text(f"Buy left amount updated to {buy_left} SOL.")
    update_settings_msg(update, context)
    return ConversationHandler.END


def change_buy_right(update: Update, context: CallbackContext):
    global buy_right
    buy_right = float(update.message.text)
    context.user_data["buy_right"] = buy_right
    update.message.reply_text(f"Buy right amount updated to {buy_right} SOL.")
    update_settings_msg(update, context)
    return ConversationHandler.END


def change_sell_left(update: Update, context: CallbackContext):
    sell_left = float(update.message.text)
    context.user_data["sell_left"] = sell_left
    update.message.reply_text(f"Sell left percentage updated to {sell_left}%.")
    update_settings_msg(update, context)
    return ConversationHandler.END


def change_sell_right(update: Update, context: CallbackContext):
    sell_right = float(update.message.text)
    context.user_data["sell_right"] = sell_right
    update.message.reply_text(f"Sell right percentage updated to {sell_right}%.")
    update_settings_msg(update, context)
    return ConversationHandler.END


def change_buy_slippage(update: Update, context: CallbackContext):
    buy_slip = float(update.message.text)
    context.user_data["buy_slip"] = buy_slip
    update.message.reply_text(f"Buy slippage percentage updated to {buy_slip}%.")
    update_settings_msg(update, context)
    return ConversationHandler.END


def change_sell_slippage(update: Update, context: CallbackContext):
    sell_slip = float(update.message.text)
    context.user_data["sell_slip"] = sell_slip
    update.message.reply_text(f"Sell slippage percentage updated to {sell_slip}%.")
    update_settings_msg(update, context)
    return ConversationHandler.END


def change_max_price_impact(update: Update, context: CallbackContext):
    max_price_impact = float(update.message.text)
    context.user_data["max_price_impact"] = max_price_impact
    update.message.reply_text(f"Max price impact percentage updated to {max_price_impact}%.")
    update_settings_msg(update, context)
    return ConversationHandler.END


def handle_withdraw(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    balance = context.user_data["balance"]

    if balance > 0:
        if query.data == 'withdraw_x':
            public_key = context.user_data.get('public_key')
            context.user_data['withdraw_type'] = 'partial'
            query.message.reply_text(
                f"Reply with the amount to withdraw (0 - {balance})"
            )
            return AMOUNT
        elif query.data == 'withdraw_all':
            context.user_data['withdraw_type'] = 'all'
            query.message.reply_text(
                "Reply with the destination address"
            )
            return ADDRESS
    else:
        query.message.reply_text(
            "You have No Balance to Withdraw"
        )


# Handler for capturing the amount to withdraw
def handle_amount(update: Update, context: CallbackContext) -> None:
    amount = update.message.text
    balance = context.user_data["balance"]
    try:
        amount = float(amount)
        if 0 <= amount <= balance:
            context.user_data['withdraw_amount'] = amount
            update.message.reply_text(
                "Reply with the destination address"
            )
            return ADDRESS
        else:
            update.message.reply_text(f"Invalid amount. Please enter a value between 0 and {balance}.")
            return AMOUNT
    except ValueError:
        update.message.reply_text("Invalid amount. Please enter a numeric value.")
        return AMOUNT


# Handler for capturing the destination address and performing the transaction
def handle_address(update: Update, context: CallbackContext) -> int:
    to_address = update.message.text
    withdraw_type = context.user_data.get('withdraw_type')
    private_key = context.user_data.get('private_key')
    resp = ''
    amount = 0

    if withdraw_type == 'partial':
        amount = context.user_data.get('withdraw_amount')
    elif withdraw_type == 'all':
        amount = context.user_data["balance"]

    update.message.reply_text(f"Transaction initiated for {amount} SOL to address {to_address}.")
    resp = send_sol(private_key, to_address, float(amount))
    print(resp)

    if resp["result"]:
        update.message.reply_text(f"Transaction is Sucessful !\n https://solscan.io/tx/{resp['result']}")
    else:
        update.message.reply_text(f"Transaction failed. \n Please Try again")

    return ConversationHandler.END


# Handler for cancelling the conversation
def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Withdrawal process cancelled.")
    return ConversationHandler.END


def button_click(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if query.data == 'close':
        query.message.delete()
    elif query.data == 'deposit':
        public_key = context.user_data.get('public_key')
        query.message.reply_text(f"To deposit send SOL to below address:\n\n `{public_key}`",
                                 parse_mode=ParseMode.MARKDOWN_V2)
    elif query.data == 'export_secret':
        keyboard = [
            [InlineKeyboardButton("Cancel", callback_data=f"close"),
             InlineKeyboardButton("Confirm", callback_data=f"export_secret_confirm")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text(f"Are you sure you want to export your *Private Key*?", reply_markup=reply_markup,
                                 parse_mode=ParseMode.MARKDOWN_V2)
    elif query.data == 'export_secret_confirm':
        private_key = context.user_data.get('private_key')
        message = query.message.reply_text(
            f"Your Private Key is:\n\n `{private_key}` \n\n You can now import the key into a wallet like Phantum \(tap to copy\)\n\nThis message should auto\-delete in 1 minute\. If not, delete this message once you are done\.",
            parse_mode=ParseMode.MARKDOWN_V2)

        context.job_queue.run_once(delete_message, 60, context=(message.chat_id, message.message_id))

    elif query.data == 'reset_wallet':
        keyboard = [
            [InlineKeyboardButton("Cancel", callback_data=f"close"),
             InlineKeyboardButton("Confirm", callback_data=f"reset_wallet_confirm")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text(
            f"Are you sure you want to *reset* your *MEMEbot Wallet*?\n\n ⚠️*WARNING: This action is irreversible\!*\n\n MEMEbot will generate a new wallet for you and discard your old one\.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN_V2)
    elif query.data == 'reset_wallet_confirm':
        private_key = context.user_data.get('private_key')
        query.message.reply_text(
            f"Your *Private Key* for your *OLD* wallet is:\n\n {private_key}\n\n You can now import the key into a wallet like Phantum \(tap to copy\) \n\nSave this key in case you need to access this wallet again\.",
            parse_mode=ParseMode.MARKDOWN_V2)
        public_key, secret_key = create_wallet()

        if public_key and secret_key:
            context.user_data["public_key"] = public_key
            context.user_data["private_key"] = secret_key
            query.message.reply_text(
                f"*Sucess*\n\nYour new wallet is:\n`{public_key}`\n\nYou can now send SOL to this address to deposit into your new wallet\.",
                parse_mode=ParseMode.MARKDOWN_V2)
    elif query.data == 'qrcode':
        ref_code = context.user_data.get('ref_code')
        qr_link = f"{BOT_LINK}?start={ref_code}"
        qr_img = generate_qr_code(qr_link)
        query.message.reply_photo(photo=qr_img)


def delete_message(context: CallbackContext) -> None:
    chat_id, message_id = context.job.context
    context.bot.delete_message(chat_id=chat_id, message_id=message_id)


def handle_message(update: Update, context: CallbackContext):
    address = update.message.text
    token_details = get_token_details(address)

    autobuy_amt = context.user_data["autobuy_amt"]
    balance = context.user_data["balance"]
    autobuy_enabled = context.user_data["autobuy_enabled"]

    buy_left = context.user_data["buy_left"]
    buy_right = context.user_data["buy_right"]

    if autobuy_enabled and float(autobuy_amt) > float(balance):
        update.message.reply_text(
            f"Auto Buy amount ({autobuy_amt} SOL) is greater than your wallet balance ({balance} SOL). Please disable Auto Buy or lower the amount.")
    else:
        if token_details == {}:
            update.message.reply_text(
                f"Token not found.Make sure address ({address}) is correct.\n\n You can enter  any Solana token listed on https://dexscreener.com ")
        else:
            msg = (
                f"{token_details['symbol']} | *{token_details['symbol']}*\n"
                f"`{address}`\n\n"
                f"Price: *${token_details['price']}*\n"
                f"5m: *{token_details['priceChange']['m5']}%*, 1h: *{token_details['priceChange']['h1']}%*, 6h: *{token_details['priceChange']['h6']}%*, 24h: *{token_details['priceChange']['h24']}%*\n"
                f"Market Cap: *${convert_number_to_k_m(token_details['marketCap'])}*\n\n"
                f"wallet balance: *{balance} SOL*\n\n"
                "To buy press one of the buttons below."
            )
            msgV2 = escape_markdown_v2(msg)
            keyboard = [
                [InlineKeyboardButton("Cancel", callback_data=f"close")],
                [InlineKeyboardButton("View on Solscan", url=f"https://solscan.io/account/{address}"),
                 InlineKeyboardButton("View on Dexscreener", url=f"https://dexscreener.com/solana/{address}")]
                , [InlineKeyboardButton(f"Buy {buy_left} SOL", callback_data=f"buy_left"),
                   InlineKeyboardButton(f"Buy {buy_right} SOL", callback_data=f"buy_right"),
                   InlineKeyboardButton("Buy X SOL", callback_data=f"buy_x")],
                [InlineKeyboardButton("Refresh", callback_data=f"refresh")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(msgV2, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)


def main() -> None:
    updater = Updater(token=TELEGRAM_BOT_TOKEN)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("home", home))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("settings", settings))
    dp.add_handler(CommandHandler("chat", chat))
    dp.add_handler(CommandHandler("referrals", referrals))

    dp.add_handler(CallbackQueryHandler(handle_wallets, pattern=r'wallet'))
    dp.add_handler(CallbackQueryHandler(handle_wallet_refresh, pattern=r'refresh_wallet'))
    dp.add_handler(CallbackQueryHandler(referrals, pattern=r'referrals'))
    dp.add_handler(CallbackQueryHandler(settings, pattern=r'settings'))
    dp.add_handler(CallbackQueryHandler(help, pattern=r'help'))

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    settings_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_settings_button,
                                           pattern='^(autobuy_amt|buy_left|buy_right|sell_left|sell_right|buy_slippage|sell_slippage|maxprice_impact)$')],
        states={
            AUTOBUY_AMT: [MessageHandler(Filters.text & ~Filters.command, change_autobuy_amt)],
            BUY_LEFT: [MessageHandler(Filters.text & ~Filters.command, change_buy_left)],
            BUY_RIGHT: [MessageHandler(Filters.text & ~Filters.command, change_buy_right)],
            SELL_LEFT: [MessageHandler(Filters.text & ~Filters.command, change_sell_left)],
            SELL_RIGHT: [MessageHandler(Filters.text & ~Filters.command, change_sell_right)],
            BUY_SLIPPAGE: [MessageHandler(Filters.text & ~Filters.command, change_buy_slippage)],
            SELL_SLIPPAGE: [MessageHandler(Filters.text & ~Filters.command, change_sell_slippage)],
            MAX_PRICE_IMPACT: [MessageHandler(Filters.text & ~Filters.command, change_max_price_impact)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(settings_conv_handler)

    dp.add_handler(CallbackQueryHandler(change_settings_button, pattern=r'^(toggle|toggle2|priority|mev_protect)$'))

    withdraw_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_withdraw, pattern='^withdraw_x$|^withdraw_all$')],
        states={
            AMOUNT: [MessageHandler(Filters.text & ~Filters.command, handle_amount)],
            ADDRESS: [MessageHandler(Filters.text & ~Filters.command, handle_address)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dp.add_handler(withdraw_conv_handler)
    dp.add_handler(CallbackQueryHandler(button_click))

    # dp.add_handler(MessageHandler(Filters.text & ~Filters.command, receive_address))
    # dp.add_handler(CallbackQueryHandler(handle_rating, pattern=r'^give_rating_'))
    # dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_rating))

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
