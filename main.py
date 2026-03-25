"""
Телеграм-бот: Калькулятор скринінгу раку молочної залози (українська)

Встановлення:  pip install python-telegram-bot==20.7
Запуск:        python bot_ua.py

Вкажіть токен у змінній середовища BOT_TOKEN або вставте безпосередньо нижче.
"""

import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не знайдено в змінних оточення!")
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

AGE, FAMILY, FAMILY_GENTEST, FAMILY_MUTATION, PANCREAS, BIOPSY, BIOPSY_ATYPIA, HISTORY, BRCA_TEST = range(9)

YES_NO_KB = InlineKeyboardMarkup([[
    InlineKeyboardButton("Так", callback_data="yes"),
    InlineKeyboardButton("Ні",  callback_data="no"),
]])

AGE_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("До 35 років",  callback_data="age_lt35"),
     InlineKeyboardButton("35–50 років",  callback_data="age_35_50")],
    [InlineKeyboardButton("51–70 років",  callback_data="age_51_70"),
     InlineKeyboardButton("Старше 70",    callback_data="age_gt70")],
])

AGE_MAP   = {"age_lt35": 30, "age_35_50": 43, "age_51_70": 60, "age_gt70": 75}
AGE_LABEL = {"age_lt35": "до 35 років", "age_35_50": "35–50 років", "age_51_70": "51–70 років", "age_gt70": "старше 70 років"}


def build_recommendations(data: dict) -> str:
    age      = data.get("age", 30)
    family   = data.get("family")
    gen_test = data.get("gen_test")
    mutation = data.get("mutation")
    pancreas = data.get("pancreas")
    atypia   = data.get("atypia")
    history  = data.get("history")
    brca     = data.get("brca")

    lines = ["📋 *Загальні рекомендації*"]
    lines.append(
        "• Проводьте *самообстеження грудей раз на місяць*. "
        "Памʼятайте: самообстеження проводиться не для «пошуку раку», "
        "а щоб переконатись, що у вас усе гаразд!"
    )
    lines.append(
        "• *Раз на рік* просіть сімейного лікаря або гінеколога провести огляд молочних залоз "
        "— не соромтеся нагадати, якщо фахівець не запропонував цього сам."
    )
    lines.append(
        "• При появі будь-яких змін (ущільнення, зміна форми, набряк, виділення) "
        "— *зверніться до лікаря для позапланового огляду*."
    )

    if history != "yes" and family != "yes" and age > 50:
        lines.append("• *Мамографія раз на 2 роки до 70 років* (стандартний віковий скринінг).")
    if history != "yes" and family != "yes" and age <= 50:
        lines.append(
            "• З 50 до 70 років вам буде показана *скринінгова мамографія раз на 2 роки* — обговоріть із сімейним лікарем завчасно. "
            "Європейські рекомендації пропонують розпочинати мамографічний скринінг з 45 років; ви можете обговорити це питання з фахівцем індивідуально."
        )
    if history != "yes" and family == "yes" and age > 35:
        lines.append("• З урахуванням сімейного анамнезу — *щорічна мамографія до 75 років*.")
    if history != "yes" and family == "yes" and age <= 35:
        lines.append("• З урахуванням сімейного анамнезу — *щорічна мамографія з 35 до 75 років*. Обговоріть із лікарем завчасно.")

    individual = []

    if history == "yes":
        if brca == "yes":
            individual.append(
                "🔴 *Скринінг при раніше виявленому РМЗ*\n"
                "*Мамографія та МРТ молочних залоз* — почергово кожні 6 місяців (щорічно кожен метод).\n\n"
                "Рекомендується консультація хірурга-онколога (мамолога) для обговорення варіантів зниження ризику — медикаментозного або хірургічного."
            )
        else:
            individual.append(
                "🔴 *Скринінг при раніше виявленому РМЗ*\n"
                "Рекомендується *консультація лікаря-генетика* для проведення тестування на мутації BRCA.\n\n"
                "Рекомендується *консультація хірурга-онколога (мамолога)* для визначення обсягу та частоти обстежень."
            )
    else:
        if family == "yes" and age > 35:
            individual.append("🟢 *Мамографічний скринінг*\nЗ урахуванням сімейного анамнезу — *щорічна мамографія*.")
        elif family != "yes" and age > 50:
            individual.append("🟢 *Мамографічний скринінг*\nСтандартний скринінг: *мамографія раз на 2 роки до 70 років*.")

    genetics_reasons = []
    if family == "yes" and gen_test == "no":
        genetics_reasons.append("у родині був рак грудей або яєчників, тестування не проводилось")
    if family == "yes" and gen_test == "yes" and mutation == "yes":
        genetics_reasons.append("у хворої родички виявлені генетичні мутації")
    if pancreas == "yes":
        genetics_reasons.append("сімейний анамнез щодо раку підшлункової або передміхурової залози")
    if genetics_reasons:
        individual.append(
            "🔵 *Консультація лікаря-генетика*\n"
            "Рекомендується консультація медичного генетика.\n"
            "_Підстави: " + "; ".join(genetics_reasons) + "._"
        )

    if atypia == "yes" and history != "yes":
        individual.append(
            "🔴 *Консультація хірурга-онколога (мамолога)*\n"
            "За даними біопсії виявлена атипова гіперплазія. "
            "Необхідна консультація онколога або мамолога."
        )

    if individual:
        lines += ["", "📌 *Індивідуальні рекомендації*"] + individual

    lines += ["", "ℹ️ _Калькулятор має інформаційний характер і не замінює консультацію лікаря._"]
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Вітаємо!\n\nЦей калькулятор допоможе визначити оптимальний план скринінгу раку молочної залози.\n\n*Крок 1 з 5*\nОберіть ваш вік:",
        parse_mode="Markdown", reply_markup=AGE_KB,
    )
    return AGE


async def age_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    context.user_data["age"] = AGE_MAP[q.data]
    context.user_data["age_label"] = AGE_LABEL[q.data]
    await q.edit_message_text(
        f"✅ Вік: _{AGE_LABEL[q.data]}_\n\n*Крок 2 з 5*\nУ вашій родині були випадки раку грудей або яєчників?",
        parse_mode="Markdown", reply_markup=YES_NO_KB,
    )
    return FAMILY


async def family_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    context.user_data["family"] = q.data
    if q.data == "no":
        await q.edit_message_text("*Крок 3 з 5*\nУ вашій родині були випадки раку підшлункової залози або раку передміхурової залози у чоловіків?", parse_mode="Markdown", reply_markup=YES_NO_KB)
        return PANCREAS
    await q.edit_message_text("*Уточнювальне запитання*\nЧи проводилось генетичне тестування хворої?", parse_mode="Markdown", reply_markup=YES_NO_KB)
    return FAMILY_GENTEST


async def family_gentest_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    context.user_data["gen_test"] = q.data
    if q.data == "no":
        await q.edit_message_text("*Крок 3 з 5*\nУ вашій родині були випадки раку підшлункової залози або раку передміхурової залози у чоловіків?", parse_mode="Markdown", reply_markup=YES_NO_KB)
        return PANCREAS
    await q.edit_message_text("*Уточнювальне запитання*\nЧи були виявлені генетичні мутації у хворої родички?", parse_mode="Markdown", reply_markup=YES_NO_KB)
    return FAMILY_MUTATION


async def family_mutation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    context.user_data["mutation"] = q.data
    await q.edit_message_text("*Крок 3 з 5*\nУ вашій родині були випадки раку підшлункової залози або раку передміхурової залози у чоловіків?", parse_mode="Markdown", reply_markup=YES_NO_KB)
    return PANCREAS


async def pancreas_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    context.user_data["pancreas"] = q.data
    await q.edit_message_text(
        "*Крок 4 з 5*\nВам раніше виконувались біопсії молочної залози?\n\n_Операції з приводу фіброаденом та аспірація кіст не вважаються біопсією._",
        parse_mode="Markdown", reply_markup=YES_NO_KB,
    )
    return BIOPSY


async def biopsy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    context.user_data["biopsy"] = q.data
    if q.data == "no":
        await q.edit_message_text("*Крок 5 з 5*\nВам раніше діагностували рак молочної залози?", parse_mode="Markdown", reply_markup=YES_NO_KB)
        return HISTORY
    await q.edit_message_text("*Уточнювальне запитання*\nЧи була у висновку біопсії фраза про наявність *атипової гіперплазії*?", parse_mode="Markdown", reply_markup=YES_NO_KB)
    return BIOPSY_ATYPIA


async def biopsy_atypia_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    context.user_data["atypia"] = q.data
    await q.edit_message_text("*Крок 5 з 5*\nВам раніше діагностували рак молочної залози?", parse_mode="Markdown", reply_markup=YES_NO_KB)
    return HISTORY


async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    context.user_data["history"] = q.data
    if q.data == "yes":
        await q.edit_message_text(
            "*Уточнювальне запитання*\nЧи проводилось вам генетичне тестування на наявність мутацій BRCA?",
            parse_mode="Markdown", reply_markup=YES_NO_KB,
        )
        return BRCA_TEST
    restart_kb = InlineKeyboardMarkup([[InlineKeyboardButton("↺ Пройти знову", callback_data="restart")]])
    await q.edit_message_text(build_recommendations(context.user_data), parse_mode="Markdown", reply_markup=restart_kb)
    return ConversationHandler.END


async def brca_test_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    context.user_data["brca"] = q.data
    restart_kb = InlineKeyboardMarkup([[InlineKeyboardButton("↺ Пройти знову", callback_data="restart")]])
    await q.edit_message_text(build_recommendations(context.user_data), parse_mode="Markdown", reply_markup=restart_kb)
    return ConversationHandler.END


async def restart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    context.user_data.clear()
    await q.edit_message_text("*Крок 1 з 5*\nОберіть ваш вік:", parse_mode="Markdown", reply_markup=AGE_KB)
    return AGE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Діалог завершено. Щоб почати знову, введіть /start.")
    return ConversationHandler.END


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start), CallbackQueryHandler(restart_handler, pattern="^restart$")],
        states={
            AGE:             [CallbackQueryHandler(age_handler,             pattern="^age_")],
            FAMILY:          [CallbackQueryHandler(family_handler,          pattern="^(yes|no)$")],
            FAMILY_GENTEST:  [CallbackQueryHandler(family_gentest_handler,  pattern="^(yes|no)$")],
            FAMILY_MUTATION: [CallbackQueryHandler(family_mutation_handler, pattern="^(yes|no)$")],
            PANCREAS:        [CallbackQueryHandler(pancreas_handler,        pattern="^(yes|no)$")],
            BIOPSY:          [CallbackQueryHandler(biopsy_handler,          pattern="^(yes|no)$")],
            BIOPSY_ATYPIA:   [CallbackQueryHandler(biopsy_atypia_handler,   pattern="^(yes|no)$")],
            HISTORY:         [CallbackQueryHandler(history_handler,         pattern="^(yes|no)$")],
            BRCA_TEST:       [CallbackQueryHandler(brca_test_handler,       pattern="^(yes|no)$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True, 
    )
    app.add_handler(conv)
    logger.info("Бот (UA) запущено. Ctrl+C для зупинки.")
