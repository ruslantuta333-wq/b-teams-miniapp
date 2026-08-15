import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from config import (
    BOT_TOKEN,
    ADMIN_ID,
    UAH_CARD,
    RUB_CARD,
    WEBAPP_URL,
)

PRODUCTS = {
    "zolo": {
        "name": "ZOLO",
        "plans": {
            "1":  {"days": 1,  "uah": 100,  "rub": 250},
            "3":  {"days": 3,  "uah": 250,  "rub": 600},
            "7":  {"days": 7,  "uah": 400,  "rub": 950},
            "30": {"days": 30, "uah": 1000, "rub": 2400},
            "60": {"days": 60, "uah": 1700, "rub": 4000},
        },
    }
}


def main_menu():
    buttons = [
        [InlineKeyboardButton("🛒 Каталог софтов", callback_data="catalog")]
    ]

    if WEBAPP_URL and "ВСТАВЬ" not in WEBAPP_URL:
        buttons.append([
            InlineKeyboardButton(
                "🌐 Mini App",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        ])

    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Добро пожаловать в B Teams Shop!\n\n"
        "Выбери нужный раздел:",
        reply_markup=main_menu()
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "catalog":
        await query.edit_message_text(
            "🛒 КАТАЛОГ СОФТОВ\n\n"
            "Выбери софт:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔹 ZOLO", callback_data="product:zolo")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="home")]
            ])
        )

    elif data == "product:zolo":
        product = PRODUCTS["zolo"]
        buttons = []

        for plan_id, plan in product["plans"].items():
            buttons.append([
                InlineKeyboardButton(
                    f'{plan["days"]} дней — {plan["uah"]} UAH / {plan["rub"]} RUB',
                    callback_data=f"plan:zolo:{plan_id}"
                )
            ])

        buttons.append([
            InlineKeyboardButton("⬅️ Назад", callback_data="catalog")
        ])

        await query.edit_message_text(
            "🔹 ZOLO\n\n"
            "Выбери срок подписки:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("plan:"):
        _, product_id, plan_id = data.split(":")

        product = PRODUCTS[product_id]
        plan = product["plans"][plan_id]

        context.user_data["order"] = {
            "product": product["name"],
            "days": plan["days"],
            "uah": plan["uah"],
            "rub": plan["rub"],
        }

        await query.edit_message_text(
            f"🔹 {product['name']}\n"
            f"⏱ Срок: {plan['days']} дней\n\n"
            f"🇺🇦 {plan['uah']} UAH\n"
            f"🇷🇺 {plan['rub']} RUB\n\n"
            "Выбери валюту оплаты:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🇺🇦 Оплата UAH",
                        callback_data=f"currency:UAH:{product_id}:{plan_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🇷🇺 Оплата RUB",
                        callback_data=f"currency:RUB:{product_id}:{plan_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ Назад",
                        callback_data="product:zolo"
                    )
                ]
            ])
        )

    elif data.startswith("currency:"):
        _, currency, product_id, plan_id = data.split(":")

        product = PRODUCTS[product_id]
        plan = product["plans"][plan_id]

        if currency == "UAH":
            price = plan["uah"]
            payment_details = UAH_CARD
            currency_name = "UAH"
        else:
            price = plan["rub"]
            payment_details = RUB_CARD
            currency_name = "RUB"

        context.user_data["order"] = {
            "product": product["name"],
            "days": plan["days"],
            "price": price,
            "currency": currency_name,
            "payment_details": payment_details,
        }

        await query.edit_message_text(
            "💳 ОПЛАТА\n\n"
            f"📦 Товар: {product['name']}\n"
            f"⏱ Срок: {plan['days']} дней\n"
            f"💰 Сумма: {price} {currency_name}\n\n"
            f"💳 Реквизиты:\n"
            f"<code>{payment_details}</code>\n\n"
            "После оплаты нажми кнопку «Я оплатил».",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "✅ Я оплатил",
                        callback_data="paid"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ Назад",
                        callback_data=f"plan:zolo:{plan_id}"
                    )
                ]
            ])
        )

    elif data == "paid":
        order = context.user_data.get("order")

        if not order:
            await query.edit_message_text(
                "❌ Заказ не найден.\n\n"
                "Начни оформление заново через /start."
            )
            return

        user = query.from_user

        if ADMIN_ID:
            admin_text = (
                "🔔 НОВАЯ ЗАЯВКА НА ОПЛАТУ\n\n"
                f"👤 Пользователь: {user.full_name}\n"
                f"🆔 Telegram ID: {user.id}\n"
                f"📦 Товар: {order['product']}\n"
                f"⏱ Срок: {order['days']} дней\n"
                f"💰 Сумма: {order['price']} {order['currency']}\n\n"
                "⏳ Ожидается чек."
            )

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text
            )

        await query.edit_message_text(
            "✅ Заявка создана!\n\n"
            "Теперь отправь сюда чек об оплате.\n"
            "После проверки администратор обработает заказ."
        )

    elif data == "catalog":
        await query.edit_message_text(
            "🛒 КАТАЛОГ СОФТОВ",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔹 ZOLO", callback_data="product:zolo")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="home")]
            ])
        )

    elif data == "home":
        await query.edit_message_text(
            "🏠 Главное меню\n\n"
            "Выбери нужный раздел:",
            reply_markup=main_menu()
        )


async def main():
    if not BOT_TOKEN or "ВСТАВЬ" in BOT_TOKEN:
        raise ValueError(
            "В config.py не указан BOT_TOKEN!"
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("✅ B Teams Bot запущен!")

    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
