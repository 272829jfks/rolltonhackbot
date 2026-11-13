FROM python:3.13-slim
WORKDIR /app
COPY telegram_bot.py tokens.json ./
CMD ["python","-u","telegram_bot.py"]
