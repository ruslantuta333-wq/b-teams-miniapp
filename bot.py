import json
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN, ADMIN_ID, UAH_CARD, RUB_CARD, WEBAPP_URL

PURCHASES_FILE = Path("purchases.json")

PRODUCTS = {
    "zolo": {
        "name": "ZOLO",
        "plans": {
            "1":  {"days": 1,  "uah": 85,   "rub": 170},
            "3":  {"days": 3,  "uah": 180,  "rub": 400},
            "7":  {"days": 7,  "uah": 325,  "rub": 800},
            "14": {"days": 14, "uah": 450,  "rub": 1000},
            "30": {"days": 30, "uah": 690,  "rub": 1500},
            "60": {"days": 60, "uah": 1000, "rub": 2000},
        },
    }
}


def load_purchases():
    try:
        return json.loads(PURCHASES_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_purchases():
    PURCHASES_FILE.write_text(
        json.dumps(PURCHASES, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


PURCHASES = load_purchases()


def main_menu():
    buttons = [
        [
            InlineKeyboardButton("🛒 Каталог софтов", callback_data="catalog"),
        ],
        [
            InlineKeyboardButton("🛍 Мои покупки", callback_data="purchases"),
        ],
    ]

    if WEBAPP_URL and "ВСТАВЬ" not in WEBAPP_URL:
        buttons[0].append(
            InlineKeyboardButton(
                "🌐 Mini App",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        )

    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Добро пожаловать в B Teams Shop!\n\n"
        "Выбери нужный раздел:",
        reply_markup=main_menu()
    )




async def purchases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    items = PURCHASES.get(user_id, [])

    if not items:
        text = "🛍 Мои покупки\n\nУ тебя пока нет покупок."
    else:
        lines = ["🛍 Мои покупки\n"]
        for i, item in enumerate(items, 1):
            lines.append(
                f"💎 Покупка #{i}\n"
                f"📦 {item['product']}\n"
                f"⏱ {item['days']} дней\n"
                f"💰 {item['price']} {item['currency']}\n"
                f"📊 {item['status']}\n"
            )
        text = "\n".join(lines)

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Назад", callback_data="home")]
        ])
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "home":
        await query.edit_message_text(
            "🏠 Главное меню:",
            reply_markup=main_menu()
        )

    elif data == "catalog":
        await query.edit_message_text(
            "🛒 Каталог софтов:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 ZOLO", callback_data="product:zolo")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="home")]
            ])
        )

    elif data == "purchases":
        await purchases(update, context)

    elif data == "product:zolo":
        buttons = []

        for plan_id, plan in PRODUCTS["zolo"]["plans"].items():
            buttons.append([
                InlineKeyboardButton(
                    f'💎 {plan["days"]} Day — {plan["rub"]} ₽ / {plan["uah"]} ₴',
                    callback_data=f"plan:zolo:{plan_id}"
                )
            ])

        buttons.append([
            InlineKeyboardButton("⬅️ Назад", callback_data="catalog")
        ])

        await query.edit_message_text(
            "💎 ZOLO\n\nВыбери срок:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("plan:"):
        _, product_id, plan_id = data.split(":")
        product = PRODUCTS[product_id]
        plan = product["plans"][plan_id]

        await query.edit_message_text(
            f"💎 {product['name']}\n"
            f"⏱ {plan['days']} дней\n\n"
            f"🇷🇺 {plan['rub']} ₽\n"
            f"🇺🇦 {plan['uah']} ₴\n\n"
            "Выбери валюту:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🇷🇺 RUB",
                        callback_data=f"pay:RUB:{product_id}:{plan_id}"
                    ),
                    InlineKeyboardButton(
                        "🇺🇦 UAH",
                        callback_data=f"pay:UAH:{product_id}:{plan_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ Назад",
                        callback_data=f"product:{product_id}"
                    )
                ]
            ])
        )

    elif data.startswith("pay:"):
        _, currency, product_id, plan_id = data.split(":")
        product = PRODUCTS[product_id]
        plan = product["plans"][plan_id]

        price = plan["rub"] if currency == "RUB" else plan["uah"]
        details = RUB_CARD if currency == "RUB" else UAH_CARD

        order = {
            "product": product["name"],
            "days": plan["days"],
            "price": price,
            "currency": currency,
            "payment_details": details
        }

        context.user_data["order"] = order
        context.bot_data.setdefault("orders", {})
        context.bot_data["orders"][str(query.from_user.id)] = order

        await query.edit_message_text(
            f"💳 ОПЛАТА\n\n"
            f"📦 {order['product']}\n"
            f"⏱ {order['days']} дней\n"
            f"💰 {order['price']} {order['currency']}\n\n"
            f"💳 Реквизиты:\n<code>{details}</code>\n\n"
            "После оплаты нажми «✅ Я оплатил».",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Я оплатил", callback_data="paid")],
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"plan:{product_id}:{plan_id}")]
            ])
        )

    elif data == "paid":
        order = context.user_data.get("order")

        if not order:
            order = context.bot_data.get("orders", {}).get(str(query.from_user.id))

        if not order:
            await query.edit_message_text(
                "❌ Заказ не найден.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ В меню", callback_data="home")]
                ])
            )
            return

        context.bot_data.setdefault("orders", {})
        context.bot_data["orders"][str(query.from_user.id)] = order

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "🔔 НОВАЯ ОПЛАТА\n\n"
                f"👤 {query.from_user.full_name}\n"
                f"🆔 ID: {query.from_user.id}\n"
                f"📦 {order['product']}\n"
                f"⏱ {order['days']} дней\n"
                f"💰 {order['price']} {order['currency']}\n\n"
                "📸 Жду чек."
            )
        )

        await query.edit_message_text(
            "✅ Заявка создана.\n\n"
            "📸 Отправь фото чека сюда.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ В меню", callback_data="home")]
            ])
        )

    elif data.startswith("approve:"):
        if query.from_user.id != ADMIN_ID:
            await query.answer("❌ Нет доступа.", show_alert=True)
            return

        user_id = data.split(":")[1]
        order = context.bot_data.get("orders", {}).get(user_id)

        if not order:
            await query.answer("❌ Заказ не найден.", show_alert=True)
            return

        context.bot_data["pending_product"] = {
            "user_id": int(user_id),
            "order": order
        }

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "✅ Заказ одобрен.\n\n"
                f"👤 ID покупателя: {user_id}\n"
                f"📦 {order['product']}\n"
                f"⏱ {order['days']} дней\n\n"
                "📎 Теперь отправь сюда товар файлом."
            )
        )

        await context.bot.send_message(
            chat_id=int(user_id),
            text=(
                "✅ Заказ проверен!\n\n"
                "⏳ Ваш заказ принят и проверен администратором.\n\n"
                "📦 Товар появится в разделе «Мои покупки» "
                "в течение 5 минут.\n\n"
                "Пожалуйста, ожидайте. Спасибо за покупку! 💎"
            )
        )

        await query.edit_message_caption(
            caption=(query.message.caption or "") + "\n\n✅ ЗАКАЗ ОДОБРЕН"
        )

    elif data.startswith("reject:"):
        if query.from_user.id != ADMIN_ID:
            await query.answer("❌ Нет доступа.", show_alert=True)
            return

        user_id = int(data.split(":")[1])

        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Оплата не подтверждена."
        )

        await query.edit_message_caption(
            caption=(query.message.caption or "") + "\n\n❌ ЗАКАЗ ОТКЛОНЁН"
        )


async def webapp_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.web_app_data:
        return

    try:
        data = json.loads(update.message.web_app_data.data)
    except json.JSONDecodeError:
        await update.message.reply_text("❌ Ошибка данных Mini App.")
        return

    if (
        data.get("product") != "ZOLO"
        or data.get("currency") not in ("RUB", "UAH")
        or not data.get("days")
        or not data.get("price")
    ):
        await update.message.reply_text("❌ Некорректный заказ.")
        return

    order = {
        "product": "ZOLO",
        "days": int(data["days"]),
        "price": int(data["price"]),
        "currency": data["currency"],
        "payment_details": RUB_CARD if data["currency"] == "RUB" else UAH_CARD
    }

    context.user_data["order"] = order
    context.bot_data.setdefault("orders", {})
    context.bot_data["orders"][str(update.effective_user.id)] = order

    await update.message.reply_text(
        f"💳 ОПЛАТА\n\n"
        f"💎 ZOLO\n"
        f"⏱ {order['days']} дней\n"
        f"💰 {order['price']} {order['currency']}\n\n"
        f"💳 Реквизиты:\n<code>{order['payment_details']}</code>\n\n"
        "После оплаты нажми «✅ Я оплатил».",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я оплатил", callback_data="paid")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="home")]
        ])
    )


async def receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:
        return

    user_id = str(update.effective_user.id)
    order = context.user_data.get("order")

    if not order:
        order = context.bot_data.get("orders", {}).get(user_id)

    if not order:
        await update.message.reply_text(
            "❌ Активный заказ не найден."
        )
        return

    context.bot_data.setdefault("orders", {})
    context.bot_data["orders"][user_id] = order

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=(
            "🧾 ЧЕК\n\n"
            f"👤 {update.effective_user.full_name}\n"
            f"🆔 ID: {user_id}\n"
            f"📦 {order['product']}\n"
            f"⏱ {order['days']} дней\n"
            f"💰 {order['price']} {order['currency']}"
        ),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Одобрить",
                    callback_data=f"approve:{user_id}"
                ),
                InlineKeyboardButton(
                    "❌ Отклонить",
                    callback_data=f"reject:{user_id}"
                )
            ]
        ])
    )

    await update.message.reply_text(
        "✅ Чек отправлен администратору.\n\n"
        "⏳ Ожидай проверки."
    )


async def admin_product_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_user.id != ADMIN_ID:
        return

    pending = context.bot_data.get("pending_product")

    if not pending:
        return

    user_id = pending["user_id"]
    order = pending["order"]

    if update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"

        await context.bot.send_document(
            chat_id=user_id,
            document=file_id,
            caption=(
                "🎁 Ваш товар готов!\n\n"
                f"💎 {order['product']}\n"
                f"⏱ {order['days']} дней\n\n"
                "Товар добавлен в «🛍 Мои покупки»."
            )
        )

    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"

        await context.bot.send_photo(
            chat_id=user_id,
            photo=file_id,
            caption=(
                "🎁 Ваш товар готов!\n\n"
                f"💎 {order['product']}\n"
                f"⏱ {order['days']} дней\n\n"
                "Товар добавлен в «🛍 Мои покупки»."
            )
        )

    elif update.message.video:
        file_id = update.message.video.file_id
        file_type = "video"

        await context.bot.send_video(
            chat_id=user_id,
            video=file_id,
            caption=(
                "🎁 Ваш товар готов!\n\n"
                f"💎 {order['product']}\n"
                f"⏱ {order['days']} дней\n\n"
                "Товар добавлен в «🛍 Мои покупки»."
            )
        )
    else:
        await update.message.reply_text(
            "❌ Отправь товар файлом, фото или видео."
        )
        return

    PURCHASES.setdefault(str(user_id), [])
    PURCHASES[str(user_id)].append({
        "product": order["product"],
        "days": order["days"],
        "price": order["price"],
        "currency": order["currency"],
        "file_id": file_id,
        "file_type": file_type,
        "status": "Активен"
    })

    save_purchases()
    context.bot_data.pop("pending_product", None)

    await update.message.reply_text(
        "✅ Товар отправлен покупателю и добавлен в «Мои покупки»."
    )


def main():
    if not BOT_TOKEN or "ВСТАВЬ" in BOT_TOKEN:
        raise ValueError("Укажи BOT_TOKEN в config.py")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(
            filters.StatusUpdate.WEB_APP_DATA,
            webapp_data_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO & (~filters.COMMAND),
            receipt_handler
        )
    )

    app.add_handler(
        MessageHandler(
            (filters.Document.ALL | filters.VIDEO) & (~filters.COMMAND),
            admin_product_handler
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            button_handler,
            pattern=r"^(home|catalog|purchases|product:|plan:|pay:|paid|approve:|reject:)"
        )
    )

    print("✅ B Teams Bot запущен!")
    print("✅ Mini App URL:", WEBAPP_URL)

    app.run_polling()


if __name__ == "__main__":
    main()


