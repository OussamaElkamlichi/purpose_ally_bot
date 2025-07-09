from telegram import Update, ChatAdministratorRights
from telegram.constants import ChatMemberStatus
import telegram
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from db_agent import add_user, get_user_by_telegram_id, get_user_stats_message, add_session, delete_session, get_user_prod_hours, update_user_rank
import asyncio, os, json

base_dir = os.path.dirname(__file__)
json_path = os.path.join(base_dir, 'ranks.json')

with open(json_path, encoding='utf-8') as f:
    ranks = json.load(f)

default_rank = next(iter(ranks))

BOT_TOKEN = "8147668562:AAGEAgFhF2ghuRXYp3q4-AtPLoHhsYfQ2Sc"

application = Application.builder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(telegram.__version__)
    user = update.effective_user
    telegram_id = user.id
    name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "NoName"

    existing_user = await asyncio.to_thread(get_user_by_telegram_id, telegram_id)

    if existing_user:
        await update.message.reply_text("أنت مُسجل بالفعل ✅")
    else:
        # إضافة المستخدم للقاعدة مع الرتبة الافتراضية
        res = await asyncio.to_thread(add_user, telegram_id, name, default_rank)
        chat_id = update.effective_chat.id
        welcome_message = (
            f"مرحبًا بك يا {res} 🌟\n\n"
            "حياكم الله، سُعداء بوجودكم معنا ✨\n"
            "أحببت أن أذكر نفسي وإياكم باستحضار النية للعمل واستثمار الدقائق والثواني،\n"
            "بل والأنفاس.\n"
            "وأن مآل الغد يكون من حال الآن، فاستعن بالله ولا تعجز 🤍"
        )
        await update.message.reply_text(welcome_message)
        await context.bot.promote_chat_member(
            chat_id=chat_id,
            user_id=telegram_id,
            is_anonymous=False,
            can_manage_chat=True,  # MUST be True for titles
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=True,  # Recommended
            can_post_messages=False,
            can_edit_messages=False,
            can_pin_messages=False,
            can_post_stories=False,
            can_edit_stories=False,
            can_delete_stories=False,
        )

        # 2. Set title (after successful promotion)
        print("Message:", update.message)
        await context.bot.set_chat_administrator_custom_title(
            chat_id=chat_id,
            user_id=telegram_id,
            custom_title=default_rank
        )
        # await context.bot.send_message(chat_id=chat_id, text=welcome_message)


async def handle_add_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    telegram_id = user.id
    chat_id = update.effective_chat.id
    try:
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("❌ استخدم الصيغة: #إضافة_حصة 45")
            return

        duration_minutes = int(parts[1])
        stt_code, today_sessions = await asyncio.to_thread(add_session, telegram_id, duration_minutes)
        prod_hours, current_rank = await asyncio.to_thread(get_user_prod_hours, telegram_id)

        if stt_code == 401:
            await update.message.reply_text(today_sessions)
            return
        eligible_ranks = [rank for rank, hours in ranks.items() if prod_hours >= hours]
        if not eligible_ranks:
            await update.message.reply_text(f"✅ تقدمك اليوم: {today_sessions} دقيقة.")
            return

        new_rank = eligible_ranks[-1]
        print(f"user new rank is {new_rank}")

        if new_rank != current_rank and telegram_id != 5264787237:
            print(f"we are about to update custom_title")
            await context.bot.set_chat_administrator_custom_title(
                chat_id=chat_id,
                user_id=telegram_id,
                custom_title=new_rank
            )
            await asyncio.to_thread(update_user_rank, telegram_id, new_rank)
            await update.message.reply_text(f"✅ تقدمك اليوم: {today_sessions} دقيقة.\n🎉 مبارك لك الترقية إلى رتبة {new_rank}!")
            return

        await update.message.reply_text(f"✅ تقدمك اليوم: {today_sessions} دقيقة.")
    except ValueError:
        await update.message.reply_text("❌ الرقم غير صالح. أرسل مثل: #إضافة_حصة 45")

async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    stats_message = get_user_stats_message(telegram_id)
    if update.message:
        await update.message.reply_markdown(stats_message)
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=stats_message,
            parse_mode="Markdown"
        )

async def handle_delete_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text.strip()
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("❌ استخدم الصيغة: #حذف_حصة 30")
            return

        minutes_to_delete = int(parts[1])
        telegram_id = update.effective_user.id
        res = await asyncio.to_thread(delete_session,telegram_id, minutes_to_delete)
        await update.message.reply_text(f"{res}")
    except ValueError:
        await update.message.reply_text("❌ الرقم غير صالح. أرسل مثل: #حذف_حصة 30")

async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands_text = (
        "#تسجيل — بدء التسجيل\n\n"
        "#إضافة_حصة — إضافة حصة جديدة\n\n"
        "#استثماراتي — عرض الإحصائيات الخاصة بك\n\n"
        "#حذف_حصة — حذف حصة\n\n"
        "#عرض_الخصائص — عرض قائمة الأوامر\n"
    )

    await update.message.reply_text(commands_text)
# async def echo_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await update.message.reply_text("✅ I got your message!")

# application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_all))

application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^#تسجيل'), start))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^#إضافة_حصة'), handle_add_session))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^#استثماراتي'), handle_stats))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^#حذف_حصة'), handle_delete_session))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^#عرض_الخصائص'), show_commands))



# import asyncio
# async def init_app():
#     await application.initialize()

# asyncio.run(init_app())