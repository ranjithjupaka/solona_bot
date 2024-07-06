import json
import logging
import random

import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, Bot, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, Filters, MessageHandler
from solona import create_wallet
import config

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

# Replace with your Telegram bot token and chat ID
TELEGRAM_BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
# NOW_PAYMENTS_API_KEY = config.NOW_PAYMENTS_API_KEY

# Define Products Here
products = {
    # Add products in the below format
    1: {
        "name": "White",
        "image": "https://e1.pxfuel.com/desktop-wallpaper/59/539/desktop-wallpaper-solid-white-thumbnail.jpg",
        "options": {
            "0.5G": 35,
            "1G": 65,
            "2G": 125,
            "3.5G": 200,
            "5G": 275,
            "7G": 350,
            "10G": 450,
            "14G": 595,
            "28G": 1120,
        },
    },
    2: {
        "name": "Grey",
        "image": "https://garden.spoonflower.com/c/12211285/p/f/m/C33sI6eqUKwnX9A5jneEq1skrcRlNC2Qz_6BEns5X0MN-yr1S1MO/Medium%20Grey%20Solid%20Color.jpg",
        "options": {
            "0.5G": 15,
            "1G": 20,
            "3.5G": 61.5,
            "7G": 105,
            "10G": 150,
            "28G": 224,
        }
    }
}

# User cart (global dictionary)
user_carts = {}
order_history = {}

ratings = {}
referrals = {}


def start(update: Update, context: CallbackContext) -> None:
    args = context.args

    if args and args[0].startswith('ref_'):
        update.message.reply_text(f'Deep link with ref_ detected! {args[0]}')

    public_key, secret_key = create_wallet()

    context.user_data["public_key"] = public_key
    context.user_data["private_key"] = secret_key.hex()

    welcome_message = (
        f"*Welcome to MEMEBot*\n\n"
        f"Solana’s fastest bot to trade any coin \( SPL token \), built by the MEMEBot community\!\n\n"
        f"You currently have no SOL in your wallet\. To start trading, deposit SOL to your MEMEBot wallet address:\n\n"
        f"`{public_key}`"
        " \(Tap to copy\)\n\n"
        "Once done, tap refresh and your balance will appear here\.\n\n"
        "To buy a token enter a ticker, token address, or a URL from [pump\.fun](https://pump.fun/), Birdeye, Dexscreener or Meteora\.\n\n"
        "For more info on your wallet and to retrieve your private key, tap the wallet button below\. User funds are safe on MEMEbot, but if you expose your private key we can't protect you\!"
    )

    keyboard = [
        [InlineKeyboardButton("Buy", callback_data="buy"),
         InlineKeyboardButton("Sell", callback_data="sell")],
        [InlineKeyboardButton("Help", callback_data="help"),
         InlineKeyboardButton("Alerts", callback_data="alerts")],
        [InlineKeyboardButton("Refer Friends", callback_data="refer"),
         InlineKeyboardButton("Wallet", callback_data="wallet")],
        [InlineKeyboardButton("Settings", callback_data="settings"),
         InlineKeyboardButton("Refresh", callback_data="refresh")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)


def help(update: Update, context: CallbackContext) -> None:
    welcome_message = (
        f"*Help:*\n\n"
        "*Which tokens can I trade?*\n"
        "Any SPL token that is a SOL pair, on Raydium or Jupiter, and will integrate more platforms on a rolling basis\. We pick up Raydium pairs instantly, and Jupiter will pick up non\-SOL pairs within approx\. 15 minutes\.\n\n"
        "*How can I see how much money I've made from referrals?*\n"
        "Tap the referrals button or type /referrals to see your payment in $MEME\!\n\n"
        "*How do I create a new wallet on MEMEbot?*\n"
        "Tap the Wallet button or type /wallet, and you'll be able to configure your new wallets\!\n\n"
        "*Is MEMEbot free? How much do I pay for transactions?*\n"
        "MEMEbot is *completely* free\! We charge 1\% on transactions, and keep the bot free so that anyone can use it\.\n\n"
        "*Why is my Net Profit lower than expected?*\n"
        "Your Net Profit is calculated after deducting all associated costs, including Price Impact, Transfer Tax, Dex Fees, and a 1\% BONKbot fee\. This ensures the figure you see is what you actually receive, accounting for all transaction related expenses\.\n\n"
        "Is there a difference between @memeprobot and the backup bots?\n"
        "No, they are all the same bot and you can use them interchangeably\. If one is slow or down, you can use the other ones\. You will have access to the same wallet and positions\.\n\n"
        "Further questions? Join our Telegram group:\n"
        "[https://t\.me/\+t7TU1G83KA4yZjFl](https://t.me/+t7TU1G83KA4yZjFl)"
    )

    keyboard = [
        [InlineKeyboardButton("Close", callback_data='close')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)


def chat(update: Update, context: CallbackContext) -> None:
    welcome_message = (
        "Join the discussion, share bugs and feature requests in our Telegram group:\n"
        "[https://t\.me/\+t7TU1G83KA4yZjFl](https://t.me/+t7TU1G83KA4yZjFl)"
    )
    update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN_V2)


def view_products(update: Update, context: CallbackContext) -> None:
    # Show individual products with pictures and purchase options
    for product_id, product_info in products.items():
        # Create a button for each product
        pr_name = product_info['name']
        purchase_options = [
            [InlineKeyboardButton(f"{amount} - {price}£", callback_data=f"buy_{product_id}_{amount}")]
            for amount, price in product_info.get("options", {}).items()
        ]

        # Add the "Give Rating" button for each product
        rating = ratings.get(pr_name, "N/A")
        if rating != "N/A":
            rating = float(rating).__round__(2)

        rating_button = [InlineKeyboardButton(f"📈 Rating: {rating} ⭐", callback_data=f"dummy")]

        # Merge the two lists
        keyboard = [rating_button] + purchase_options

        reply_markup = InlineKeyboardMarkup(keyboard)

        # If the product has an image, show it
        if product_info["image"]:
            update.effective_message.reply_photo(photo=product_info["image"], caption=f"{product_info['name']}",
                                                 reply_markup=reply_markup)
        else:
            update.effective_message.reply_text(f"{product_info['name']}", reply_markup=reply_markup)


def checkout(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    _, product_id, amount = query.data.split('_')
    product_id = int(product_id)

    if product_id in products and amount in products[product_id]["options"]:
        product_info = products[product_id]
        price = product_info["options"][amount]

        # Ask user to input shipping address
        query.message.reply_text(f"Checkout - {product_info['name']} - {amount} - {price}£\n\n"
                                 "Please provide your shipping address: \n\n Format: \n TOM JONES \n 15 WESTKEY WAY \n MANCHESTER \n M1 8SS")
        context.user_data["checkout_product_id"] = product_id
        context.user_data["checkout_amount"] = amount
    else:
        query.message.reply_text("Invalid product or option.")


def receive_address(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    product_id = context.user_data.get("checkout_product_id")
    amount = context.user_data.get("checkout_amount")
    query = update.callback_query

    if product_id is not None and amount is not None and user_id is not None:
        product_info = products[product_id]
        price = product_info["options"][amount]
        address = update.message.text
        order_summary = f"Order Summary:\n\n" \
                        f"Product: {product_info['name']}\n" \
                        f"Amount: {amount}\n" \
                        f"Price: {price} £\n" \
                        f"Shipping Address: {address}\n\n"

        # Display order summary and buttons for Bitcoin (BTC) and Monero (XMR)
        keyboard = [
            [InlineKeyboardButton("Bitcoin (BTC)", callback_data="pay_btc")],
            [InlineKeyboardButton("Monero (XMR)", callback_data="pay_xmr")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Ask the user to choose a payment method
        update.message.reply_text(order_summary + "Please choose a payment method:", reply_markup=reply_markup)
        context.user_data["checkout_product_id"] = product_id
        context.user_data["checkout_amount"] = amount
        context.user_data["shipping_address"] = address
    else:
        update.message.reply_text("Unexpected input. Please use /start to proceed.")


def choose_payment_method(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    payment_method = query.data
    message = update.message or update.callback_query.message

    if payment_method in ["pay_btc", "pay_xmr"]:
        user_id = update.effective_user.id
        product_id = context.user_data.get("checkout_product_id")
        amount = context.user_data.get("checkout_amount")
        shipping_address = context.user_data.get("shipping_address")

        if product_id is not None and amount is not None and user_id is not None and shipping_address is not None:
            product_info = products[product_id]
            price = product_info["options"][amount]
            currency = "btc" if payment_method == "pay_btc" else "xmr"

            orderDetails = f"Order Details:\n\n" \
                           f"Product: {product_info['name']}\n" \
                           f"Price: {price} £\n" \
                           f"Shipping Address: {shipping_address}\n\n" \
                           f"Payment Method: {currency.upper()}\n"

            order_id = random.randint(100000, 999999)

            url = "https://api.nowpayments.io/v1/payment"

            payload = json.dumps({
                "price_amount": price,
                "price_currency": "eur",
                "pay_currency": currency,
                "ipn_callback_url": "https://nowpayments.io",
                "order_id": order_id,
                "order_description": orderDetails,
                "is_fixed_rate": "true",
            })
            headers = {
                'x-api-key': '',
                'Content-Type': 'application/json'
            }

            response = requests.request("POST", url, headers=headers, data=payload)
            # print(response.json())
            if response.status_code == 201:
                pay_address = response.json().get('pay_address')
                # Open the checkout link for the user
                if pay_address:
                    #                    payment_id = response.json().get('payment_id')
                    #                    price_amount = response.json().get('price_amount')
                    #                    pay_amount = response.json().get('pay_amount')
                    #                    message_text1 = f"Payment Details:\n\nPayment ID: {payment_id}\nPayment Amount in EUR: {price_amount} \n" \
                    # \
                    #                    message_text2 = f"Please send `{pay_amount}` {currency.upper()} to the following address\\:\n\n" \
                    #                                            f"`{pay_address}`\n\n" \
                    #                                            f"Thanks for shopping with us\\! Once your payment is confirmed\\, we will ship your order\\. Continue shopping by using /start \\. For rating the order by using /rate \n\n"
                    #                    # Save order details to order history
                    if user_id not in order_history:
                        order_history[user_id] = []

                    # orderFinalDetails = {
                    #     "product": product_info['name'],
                    #     "amount": amount,
                    #     "price": price,
                    #     "shipping_address": shipping_address,
                    #     "orderid": payment_id,
                    # }
                    # order_history[user_id].append(orderFinalDetails)
                    # message.reply_text(message_text1)
                    # message.reply_text(message_text2, parse_mode='MarkdownV2')
                else:
                    message.reply_text("There was an issue generating the payment link. Please try again later.")
            else:
                message.reply_text("There was an issue generating the invoice. Please try again later.")
            context.user_data.pop("checkout_product_id")
            context.user_data.pop("checkout_amount")
            context.user_data.pop("shipping_address")
        else:
            message.reply_text("Unexpected input. Please use /start to proceed.")
    else:
        message.reply_text("Invalid payment method.")


def show_order_history(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    message = update.message or update.callback_query.message
    # print(order_history)

    if user_id in order_history:
        for idx, order_details in enumerate(order_history[user_id], start=1):
            order_history_text = f"Order #{idx}:\n" \
                                 f"Product: {order_details['product']}\n" \
                                 f"Amount: {order_details['amount']}\n" \
                                 f"Price: {order_details['price']} £\n" \
                                 f"Shipping Address: {order_details['shipping_address']}\n" \
                                 f"Order Id: {order_details['orderid']} \n\n"

            # Add the "Give Rating" button
            keyboard = [[InlineKeyboardButton("Give Rating", callback_data=f"give_rating_{order_details['product']}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send a new message for each order detail
            context.bot.send_message(chat_id=update.effective_chat.id, text=order_history_text,
                                     reply_markup=reply_markup)
    else:
        message.reply_text("You have no order history.")


def handle_wallets(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = update.effective_user.id

    public_key = context.user_data.get('public_key')
    balance = "0.0"
    keyboard = [
        [InlineKeyboardButton("View on Solscan",url=f"https://solscan.io/account/{public_key}"),InlineKeyboardButton("Deposit Sol", callback_data="deposit")],
        [InlineKeyboardButton("Withdraw all SOL", callback_data="withdraw_all"),InlineKeyboardButton("Withdraw X SOL", callback_data="withdraw_x")],
        [InlineKeyboardButton("Import Private Keys", callback_data=f"import_secret"),InlineKeyboardButton("Export Private Key", callback_data=f"export_secret")],
        [InlineKeyboardButton("Reset Wallet", callback_data=f"reset_wallet"),InlineKeyboardButton("Refresh", callback_data=f"refresh")],
        [InlineKeyboardButton("Close", callback_data=f"close")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(f"*Your Wallet*:\n\n Address: {public_key}\nBalance: {balance}\n\n Tap to copy the address and send SOL to deposit",
                             reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)


def handle_settings(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = update.effective_user.id

    settings_text = "Settings \n\n BUY-IN \n\n Here you can specify the amount of SOL you want to buy each transaction. The standard is set at 0.01." \
                    "\n\n SLIPPAGE CONFIG\n\nCustomize your slippage settings. ⚠️ High slippage on Pump.fun can increase the amount of SOL that you will pay." \
                    "\n\n INTERVAL\n\nSet an interval for each wallet in seconds. This determines after how many seconds a it takes before a new buy is executed for each Wallet. The standard is set at 30 seconds."

    # Add inline keyboard for rating options
    keyboard = [
        [InlineKeyboardButton("💵 Buy In", callback_data=f"rate_1")],
        [InlineKeyboardButton("⚙️ Slippage Config", callback_data=f"rate_2")],
        [InlineKeyboardButton("🕐 Interval", callback_data=f"rate_3")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(settings_text, reply_markup=reply_markup)


def handle_selected_rating(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = update.effective_user.id

    # Extract order_id and rating from callback data
    productRated, rating = query.data.split("_")[1:]

    # Check if the rating is within the valid range (1 to 5)
    if 1 <= int(rating) <= 5:
        # Send the rating to the admin
        send_rating_message(productRated, rating)
        if productRated not in ratings:
            ratings[productRated] = int(rating)
        else:
            # Update the rating if the user has already rated the product
            ratings[productRated] = (ratings[productRated] + int(rating)) / 2

        # print(ratings)
        # Inform the user that the rating has been submitted
        query.message.reply_text(f"Thank you for your rating of {rating}/5!")

    else:
        query.answer("Invalid rating selection")


def send_rating_message(productRated: str, rating: int) -> None:
    # Replace with the desired phone number to receive the rating message
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    message_text = f"New Rating Received!\nProduct: {productRated}\nRating: {rating} ⭐"
    bot.send_message(chat_id=config.CHATID, text=message_text)


def button_click(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if query.data == 'close':
        query.message.delete()


def main() -> None:
    updater = Updater(token=TELEGRAM_BOT_TOKEN)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("home", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("chat", chat))

    dp.add_handler(CallbackQueryHandler(handle_wallets, pattern=r'^wallet'))

    dp.add_handler(CommandHandler("checkout", checkout))
    dp.add_handler(CommandHandler("rate", show_order_history))
    dp.add_handler(CallbackQueryHandler(button_click))

    # dp.add_handler(MessageHandler(Filters.text & ~Filters.command, receive_address))
    dp.add_handler(CallbackQueryHandler(choose_payment_method, pattern='^pay_'))
    # dp.add_handler(CallbackQueryHandler(handle_rating, pattern=r'^give_rating_'))
    # dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_rating))
    dp.add_handler(CallbackQueryHandler(handle_selected_rating, pattern=r'^rate_'))

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
