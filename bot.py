from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from telegram.error import Forbidden, BadRequest, ChatMigrated
from dotenv import load_dotenv
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Bot
from datetime import datetime
from datetime import time
import httpx
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type


load_dotenv()

telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
base_url = os.getenv("HOUSE_REMINDER_BASE_URL")


@retry(
    stop=stop_after_attempt(3),  # stop after 3 attempts
    wait=wait_fixed(5),  # wait 5 seconds between attempts
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.NetworkError)
    ),  # retry only for HTTPStatusError
)
async def fetch(url, method="get", data=None):
    async with httpx.AsyncClient(timeout=None) as client:
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


async def generate_house_info_messages(cities_response):
    messages = []
    for city in cities_response["list"]:
        if isinstance(city["results"], list):
            for house in city["results"]:
                message_text = "*{}*\n{}\nPrice: {}\nAvailable Date: {}".format(
                    city["city_name"],
                    house["name"],
                    house["price"],
                    house["available_date"],
                )
                keyboard = [[InlineKeyboardButton("More Info", url=house["url"])]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Add the message text and reply_markup to the messages list
                messages.append((message_text, reply_markup))
        else:
            messages.append(("*{}*\nNo house found".format(city["city_name"]), None))
    return messages


async def daily_task(context: ContextTypes.DEFAULT_TYPE):
    try:
        users = await fetch(f"{base_url}/users/list")
        cities_response = await fetch(f"{base_url}/h2s/list/all")

        base_message = f"Here is the most recent list of available residences for Thursday, 01 February 2024. Please note, this list does not include any lottery-based residences. Best of luck with your booking! If you have any questions, please contact the H2S team."

        house_info_messages = await generate_house_info_messages(cities_response)

        for chat_id in users["chat_ids"]:
            try:
                message = await context.bot.send_message(
                    chat_id=chat_id,
                    text=base_message,
                    read_timeout=60,
                    write_timeout=120,
                )

                for message_text, reply_markup in house_info_messages:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=message_text,
                        parse_mode="Markdown",
                        reply_markup=reply_markup,
                        read_timeout=60,
                        write_timeout=120,
                    )

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"If you do not wish to get these reminders anymore, you can turn them off with /unset_reminder command.",
                    read_timeout=60,
                    write_timeout=120,
                )

            except BadRequest as e:
                if "chat not found" in str(e).lower():
                    print(f"Chat ID not found: {chat_id}")
                else:
                    print(f"Unknown BadRequest error: {e}")
                    raise e

            except Forbidden as e:
                print(f"Bot was blocked by user with chat_id: {chat_id}")
                try:
                    await fetch(f"{base_url}/users/{chat_id}", method="delete")
                except Exception as e:
                    print(f"Error deleting user: {e}")

            except Exception as e:
                print(f"Error sending message: {e}")
                await context.bot.send_message(
                    chat_id=chat_id, text=f"An error occurred: {e}"
                )

    except Exception as e:
        print(f"Error fetching data: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    intro_text = (
        "Welcome! This bot is designed to help you keep track of available houses. "
        "Use the /set_reminder command to activate daily reminders.\n\n"
        "Please note: This service is not endorsed by H2S, and it's crucial that you do not disclose to them that "
        "you used this bot to find a house. We are simply providing a free tool to help you stay updated on "
        "availability. We are not responsible for any issues or disputes that may arise from your use of this bot or "
        "any information it provides. Thank you for your understanding."
    )
    await context.bot.send_message(
        chat_id=chat_id,
        text=intro_text,
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

        # schedule a job to run at 16 pm
        application.job_queue.run_daily(daily_task, time(hour=18, minute=30))
        # application.job_queue.run_repeating(daily_task, interval=60, first=1)

        # start polling
        application.run_polling()

        return application
    except Exception as e:
        print(f"Unexpected error: {e}")


create_and_start_bot()
