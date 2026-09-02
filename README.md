# Cricbuzzs Telegram Auto News Bot

This bot posts short cricket-news links from RSS feeds to the Telegram channel
`@cricbuzzscom` using the Telegram Bot API.

## GitHub Secret

Add this repository secret:

- `BOT_TOKEN` = your BotFather token

Never put the token directly in `bot.py`.

## Run manually

GitHub → Actions → Cricbuzzs Auto News → Run workflow.

The workflow also runs automatically every 30 minutes.

## Important

The bot posts the headline, source and a link to the original article rather than copying the full article.
