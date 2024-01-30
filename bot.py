from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from telegram.error import Forbidden
from dotenv import load_dotenv
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Bot
from datetime import datetime
from datetime import time
import httpx


load_dotenv()

telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
base_url = os.getenv("HOUSE_REMINDER_BASE_URL")


async def fetch(url, method="get", data=None):
    async with httpx.AsyncClient() as client:
        if method == "get":
            response = await client.get(url)
        elif method == "post":
            response = await client.post(url, json=data)
        elif method == "delete":
            response = await client.delete(url)
        else:
            raise ValueError(f"Invalid method: {method}")

        if response.status_code == 404:
            raise UserNotFoundError("User not found")

        response.raise_for_status()
        return response.json()


class UserNotFoundError(Exception):
    pass


async def daily_task(context: ContextTypes.DEFAULT_TYPE):
    try:
        # Get all users
        users = await fetch(f"{base_url}/users/list")
        # Send the result to all users
        for chat_id in users["chat_ids"]:
            # Send date message
            today = datetime.now().strftime("%A, %d %B %Y")
            message = await context.bot.send_message(
                chat_id=chat_id, text=f"Today is {today}. Loading latest update..."
            )

            # Call api to get list of houses
            cities_response = await fetch(f"{base_url}/h2s/list/all")

            for city in cities_response["list"]:
                # Check if results is a list
                if isinstance(city["results"], list):
                    for house in city["results"]:
                        # Format message
                        message_text = "*{}*\n{}\nPrice: {}\nAvailable Date: {}".format(
                            city["city_name"],
                            house["name"],
                            house["price"],
                            house["available_date"],
                        )

                        # Create a link button
                        keyboard = [
                            [InlineKeyboardButton("More Info", url=house["url"])]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)

                        # Send message
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=message_text,
                            parse_mode="Markdown",
                            reply_markup=reply_markup,
                        )

                else:
                    # Send message with no house found
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="*{}*\nNo house found".format(city["city_name"]),
                        parse_mode="Markdown",
                    )

            # Edit loading message to say finished
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message.message_id,
                text=f"Today is {today}. Here is the latest update:",
            )
    except Forbidden as e:
        print(f"The bot was blocked by the user with chat_id: {chat_id}")

    except Exception as e:
        # Handle error
        print(f"Error: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"An error occurred: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text="Welcome! You can turn on reminders with /set_reminder command. We will send you about all available houses every day on this bot",
    )


async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        try:
            await fetch(f"{base_url}/users/{chat_id}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="You're already registered! You can turn off reminders with /unset_reminder command.",
            )
        except UserNotFoundError:
            await fetch(
                f"{base_url}/users/register",
                method="post",
                data={"chat_id": chat_id},
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text="You're now registered. You will receive reminders every day. You can turn off reminders with /unset_reminder command.",
            )
    except Exception as e:
        print(f"Request error: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Sorry, there was an error processing your request. Please try again later.",
        )


async def unset_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        await fetch(f"{base_url}/users/{chat_id}", method="delete")
        await context.bot.send_message(
            chat_id=chat_id,
            text="You have been unregistered. You will not receive reminders anymore.",
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            await context.bot.send_message(
                chat_id=chat_id,
                text="User not found. You may have already been unregistered.",
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Sorry, there was an error processing your request. Please try again later.",
            )
    except Exception as e:
        print(f"Request error: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Sorry, there was an error processing your request. Please try again later.",
        )


async def send_message(context, chatId, message):
    await context.bot.send_message(chat_id=chatId, text=message)


def create_and_start_bot():
    try:
        application = ApplicationBuilder().token(telegram_bot_token).build()

        start_handler = CommandHandler("start", start)
        set_reminder_handler = CommandHandler("set_reminder", set_reminder)
        unset_reminder_handler = CommandHandler("unset_reminder", unset_reminder)

        application.add_handler(start_handler)
        application.add_handler(set_reminder_handler)
        application.add_handler(unset_reminder_handler)

        # schedule a job to run at 9 am
        application.job_queue.run_daily(daily_task, time(hour=12, minute=0))

        # start polling
        application.run_polling()

        return application
    except Exception as e:
        print(f"Unexpected error: {e}")


create_and_start_bot()
