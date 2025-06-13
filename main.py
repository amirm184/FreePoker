from contextlib import asynccontextmanager
from http import HTTPStatus
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from fastapi import FastAPI, Request, Response
import os, random

TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app_bot = Application.builder().token(TOKEN).updater(None).build()

def draw_card():
    return random.choice(["A","2","3","4","5","6","7","8","9","10","J","Q","K"])

def calc_score(hand):
    score, aces = 0, 0
    for c in hand:
        if c in ["J","Q","K"]:
            score += 10
        elif c == "A":
            aces += 1
        else:
            score += int(c)
    score += aces
    while aces and score + 10 <= 21:
        score += 10; aces -= 1
    return score

players = {}

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎲 خوش‌آمدی! برای شروع /play کن.")

async def play(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    players[user.id] = {"hand":[draw_card(), draw_card()], "done":False}
    hand = players[user.id]["hand"]
    score = calc_score(hand)
    buttons = [[InlineKeyboardButton("Hit 🃏", "hit"), InlineKeyboardButton("Stand ✋", "stand")]]
    await update.message.reply_text(f"کارت‌هات: {' '.join(hand)} (مجموع: {score})", reply_markup=InlineKeyboardMarkup(buttons))

async def hit_or_stand(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    pl = players.get(q.from_user.id)
    if not pl or pl["done"]:
        return await q.edit_message_text("⛔ بازی نیست یا تموم شده.")
    if q.data=="hit":
        pl["hand"].append(draw_card())
        score = calc_score(pl["hand"])
        if score>21:
            pl["done"]=True
            await q.edit_message_text(f"‌{' '.join(pl['hand'])} مجموع: {score} – 💥 باخت!")
        else:
            buttons = [[InlineKeyboardButton("Hit 🃏","hit"), InlineKeyboardButton("Stand ✋","stand")]]
            await q.edit_message_text(f"‌{' '.join(pl['hand'])} مجموع: {score}", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        pl["done"]=True
        score = calc_score(pl["hand"])
        await q.edit_message_text(f"✅ کارت‌هات: {' '.join(pl['hand'])} (مجموع: {score})")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await app_bot.bot.set_webhook(WEBHOOK_URL)
    async with app_bot: await app_bot.start(); yield; await app_bot.stop()

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def webhook(request: Request):
    upd = Update.de_json(await request.json(), app_bot.bot)
    await app_bot.process_update(upd)
    return Response(status_code=HTTPStatus.OK)

@app.get("/health")
async def health(): return {"status":"ok"}

app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(CommandHandler("play", play))
app_bot.add_handler(CallbackQueryHandler(hit_or_stand))
