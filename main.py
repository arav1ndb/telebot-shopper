from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import pandas as pd
import stripe
import pickle
# Telegram bot token
TOKEN = '6026142184:AAE1AGVwwXq5AKSx0YhM2Hiobv8kWQjAdiI'

# Stripe API key
stripe.api_key = 'pk_test_51N5C8dSIEvzvJOEZ6JpKDWjGLQs5Wt0dTP5ZkiclUxbWV3qAYAcgkfCUcoOoQkl0UNp87sjaXYuOgP0BpgGyQ5Yi003TS5iEdg'

# Create a dataframe to store inventory items
inventory = pd.DataFrame({
    'item_id': ['item1', 'item2', 'item3', 'item4', 'item5'],
    'item_name': ['sting', 'good day ', 'hide n seek', 'amul chocobar', 'kit kat'],
    'item_price': [20, 10, 30, 15, 25],
    'item_quantity': [35, 50, 30, 8, 100]
})

# Define the user history dataframe
user_history_df = pd.DataFrame(
    columns=['user_id', 'item_id', 'item_name', 'item_price', 'points_earned'])

# Define the user points dictionary
user_points = {}

# Define the cart dictionary
cart = {}

options = [['/inventory', '/cart']]
# Define a function to handle the /start command


def start(update, context):
    user_id = update.effective_user.id
    if user_id not in user_points:
        user_points[user_id] = 0
    chat_id = update.effective_chat.id
    message = "Welcome to the inventory system. Please click /inventory to view the available items or /cart to see you items in cart"
    context.bot.send_message(chat_id=chat_id, text=message, reply_markup=ReplyKeyboardMarkup(options, one_time_keyboard=True, input_field_placeholder="select an option"
                                                                                             ),)

# Define a function to handle the /inventory command


def show_inventory(update, context):
    chat_id = update.effective_chat.id
    message = "Here are the available items:\n"
    for index, item in inventory.iterrows():
        message += f"{item['item_id']}: {item['item_name']} - \u20B9{item['item_price']}\n"
    context.bot.send_message(chat_id=chat_id, text=message)

# # Define a function to handle item selection and adding to cart
# def select_item(update, context):
#     chat_id = update.effective_chat.id
#     user_id = update.effective_user.id
#     message = "Please enter the item ID to add to your cart:"
#     context.bot.send_message(chat_id=chat_id, text=message)
#     context.user_data['user_id'] = user_id

# def add_to_cart(update, context):
#     chat_id = update.effective_chat.id
#     user_id = update.effective_user.id
#     item_id = update.message.text
#     item = inventory[inventory['item_id'] == item_id].iloc[0]
#     print(item)
#     if item['item_quantity'] > 0:
#         context.user_data['cart'] = context.user_data.get('cart', {})
#         context.user_data['cart'][item_id] = item
#         message = f"{item['item_name']} has been added to your cart."
#     else:
#         message = f"{item['item_name']} is out of stock."
#     context.bot.send_message(chat_id=chat_id, text=message)

# Function to handle the /add command


def add_to_cart(update, context):
    user_id = update.effective_user.id
    args = context.args
    print(args)
    if len(args) < 2:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Please provide the item ID and quantity.")
        return
    try:
        item_id = str(args[0])
        quantity = int(args[1])
    except ValueError:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Invalid input.")
        return
    if item_id not in inventory['item_id'].tolist():
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Item not found.")
        return
    item = inventory.loc[inventory['item_id'] == item_id].iloc[0]

    if quantity <= 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Please provide a valid quantity.")
        return
    if item['item_quantity'] < quantity:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Insufficient stock.")
        return
    if user_id not in cart:
        cart[user_id] = {}
    if item_id not in cart[user_id]:
        cart[user_id][item_id] = 0
    cart[user_id][item_id] += quantity
    inventory.loc[inventory['item_id'] == item_id, 'item_quantity'] -= quantity
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"{quantity} {item['item_name']} added to cart.")
# Function to handle the /remove command


def remove_from_cart(update, context):
    user_id = update.effective_user.id
    args = context.args
    if len(args) < 2:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Please provide the item ID and quantity.")
        return
    try:
        item_id = str(args[0])
        quantity = int(args[1])
    except ValueError:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Invalid input.")
        return
    if item_id not in inventory['item_id'].tolist():
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Item not found.")
        return
    if quantity <= 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Please provide a valid quantity.")
        return
    if user_id not in cart or item_id not in cart[user_id]:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Item not found in cart.")
        return
    if cart[user_id][item_id] < quantity:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Invalid quantity.")
        return
    item = inventory.loc[inventory['item_id'] == item_id].iloc[0]
    cart[user_id][item_id] -= quantity
    inventory.loc[inventory['item_id'] == item_id, 'item_quantity'] += quantity
    if cart[user_id][item_id] == 0:
        del cart[user_id][item_id]
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"{quantity} {item['item_name']} removed from cart.")

# Function to handle the /checkout command


def checkout(update, context):
    user_id = update.effective_user.id
    global user_history_df
    if user_id not in cart:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Your cart is empty.")
        return
    total_price = 0
    for item_id, quantity in cart[user_id].items():
        item = inventory.loc[inventory['item_id'] == item_id].iloc[0]
        total_price += item['item_price'] * quantity
        user_history_df=pd.concat([user_history_df,pd.DataFrame({'user_id': [user_id],
                                                  'item_id': [item['item_id']],
                                                  'item_name': [item['item_name']],
                                                  'item_price': [item['item_price']],
                                                  'points_earned': [item['item_price'] / 10]})])
    if user_id not in user_points:
        user_points[user_id] = 0
    user_points[user_id] += total_price / 10
    cart[user_id] = {}
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"You have successfully purchased items for a total of {total_price:.2f}.\n\n"
                             f"You have earned {total_price / 10:.2f} points.\n\n"
                             f"Your current points balance is {user_points[user_id]:.2f}.")


# Function to handle the /points command


def points(update, context):
    user_id = update.effective_user.id
    if user_id not in user_points:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="You do not have any points yet.")
        return
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"You have {user_points[user_id]:.2f} points.")

# Function to handle the /usepoints command


def use_points(update, context):
    user_id = update.effective_user.id
    args = context.args
    if len(args) < 1:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Please provide the amount of points you want to use.")
        return
    try:
        points_to_use = float(args[0])
    except ValueError:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Invalid input.")
        return
    if user_id not in user_points:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="You do not have any points yet.")
        return
    if points_to_use <= 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Please provide a valid amount of points.")
        return
    if user_points[user_id] < points_to_use:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Insufficient points.")
        return
    user_points[user_id] -= points_to_use
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"You have used {points_to_use:.2f} points.\n\n"
                             f"Your current points balance is {user_points[user_id]:.2f}.")




# Define a function to handle the /cart command


def show_cart(update, context):
    user_id = update.effective_user.id
    if user_id not in cart:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Your cart is empty.")
        return
    cart_text = "Here is your cart:\n\n"
    total_price = 0
    for item_id, quantity in cart[user_id].items():
        item = inventory.loc[inventory['item_id'] == item_id].iloc[0]
        cart_text += f"{item['item_name']} - \u20B9{item['item_price']} - Quantity: {quantity}\n"
        total_price += item['item_price'] * quantity
    cart_text += f"\nTotal price: \u20B9{total_price}"
    context.bot.send_message(chat_id=update.effective_chat.id, text=cart_text)


def checkout_stripe(update, context):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    cart = context.user_data.get('cart', {})
    total_price = context.user_data.get('total_price', 0)
    if len(cart) == 0:
        message = "Your cart is empty."
    else:
        # Create a Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': item['item_name'],
                    },
                    'unit_amount': int(item['item_price'] * 100),
                },
                'quantity': 1,
            } for item in cart.values()],
            mode='payment',
            success_url='https://your_website/success',
            cancel_url='https://your_website/cancel',
        )

    # Store user history and update inventory
    for item in cart.values():
        inventory.loc[inventory['item_id'] ==
                      item['item_id'], 'item_quantity'] -= 1
        user_history = user_history.append({
            'user_id': user_id,
            'item_id': item['item_id'],
            'item_name': item['item_name'],
            'item_price': item['item_price']
        }, ignore_index=True)

    # Update user credits
    user_credits[user_id] = user_credits.get(user_id, 0) + total_price/10
    message = f"Please complete the payment using this link: {checkout_session.url}"
    context.bot.send_message(chat_id=chat_id, text=message)


def unknown_command(update, context):
    chat_id = update.effective_chat.id
    message = "Sorry, I didn't understand that command."
    context.bot.send_message(chat_id=chat_id, text=message)


def main():

    

    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher


    start_handler = CommandHandler("start", start)#
    help_handler = CommandHandler("help", help)#
    inventory_handler = CommandHandler("inventory", show_inventory)#
    add_handler = CommandHandler("add", add_to_cart,pass_args=True)#
    remove_handler = CommandHandler("remove", remove_from_cart,pass_args=True)
    cart_handler = CommandHandler("cart", show_cart)#
    checkout_handler = CommandHandler("checkout", checkout)#
    points_handler = CommandHandler("points", points)#
    use_points_handler = CommandHandler("usepoints", use_points)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(inventory_handler)
    dispatcher.add_handler(add_handler)
    dispatcher.add_handler(remove_handler)
    dispatcher.add_handler(cart_handler)
    dispatcher.add_handler(checkout_handler)
    dispatcher.add_handler(points_handler)
    dispatcher.add_handler(use_points_handler)
    dispatcher.add_handler(MessageHandler(Filters.command, unknown_command))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
