Holland House Bot is a user-friendly Telegram bot that delivers daily updates about available houses. It interacts with a designated API to fetch house data and notifies registered users about the available options. Users have complete control over their subscription and can opt in or out of these notifications at any time.


## Privacy Statement

At Holland House Bot, we deeply respect user privacy. The bot does not collect or store any user data beyond what is needed to deliver notifications. Furthermore, we do not share any information with third parties. User privacy is our utmost priority.


## Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.


## Prerequisites

Ensure that you have the following installed on your system:

 - Python 
 - pip

Then, install the required Python packages:


    pip install python-telegram-bot requests python-dotenv

## Installation

Clone the repository: 

    git clone https://github.com/mhmalek/holland-house-bot.git

Navigate to the project directory: 

    cd holland-house-bot

Create a .env file in the project root and add your Telegram bot token and API base URL:

    TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN
    HOUSE_REMINDER_BASE_URL=YOUR_BASE_URL

Run the bot by executing: 

    python3 bot.py

After the bot is up and running, users can interact with it on Telegram using the following commands:


**/start**: Initiates a session with the bot and displays a welcome message.
**/set_reminder**: Registers the user to receive daily notifications regarding available houses.
**/unset_reminder** : Unregisters the user, thereby stopping the daily notifications.

## Contributing

We appreciate and welcome any contributions made towards the enhancement of this bot.



