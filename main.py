from telegram import Update, ChatAdministratorRights, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.constants import ChatMemberStatus
import requests
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    PollAnswerHandler,
    filters
)
from db_agent import add_user, get_daily_goals_check, get_goals,user_check, get_user_by_telegram_id, get_user_stats_message, add_session, delete_session, get_user_prod_hours, update_user_rank, show_demo_db, edit_prep, updateGoal, cron_seed, destroy_user, mark_as_done
import asyncio, os, json
from dotenv import load_dotenv
from datetime import datetime
from userGoals import UserGoals

MAIN_GOAL, SUB_GOALS, EDIT_GOAL, SET_CRON, SET_CRON_TIME, SET_CRON_WEEKDAY, EDIT_CRON_TIME, EXTRA_MAIN_GOALS, EXTRA_SUB_GOALS = range(9)

base_dir = os.path.dirname(__file__)
json_path = os.path.join(base_dir, 'ranks.json')

with open(json_path, encoding='utf-8') as f:
    ranks = json.load(f)

default_rank = next(iter(ranks))
load_dotenv('/home/OussamaNoobie/purpose_ally_bot/.env')
BOT_TOKEN = os.getenv("BOT_TOKEN")

application = Application.builder().token(BOT_TOKEN).build()

commands = [
    BotCommand("start", 'البدأ'),
    BotCommand("add_goals", "إضافة أهداف"),
    BotCommand("goal_achieved", 'أنجزت هدف؟'),
]

async def set_command_menu(update, context):
    await application.bot.set_my_commands(commands)

async def signup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    telegram_id = user.id
    name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "NoName"
    username = user.username or None
    existing_user = await asyncio.to_thread(get_user_by_telegram_id, telegram_id)

    if existing_user:
        await update.message.reply_text("أنت مُسجل بالفعل ✅")
    else:
        # إضافة المستخدم للقاعدة مع الرتبة الافتراضية
        res = await asyncio.to_thread(add_user, telegram_id, username ,name, default_rank)
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

        if new_rank != current_rank and telegram_id != 7965405588:
            print(f"we are about to update custom_title")
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    telegram_id = user.id
    name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "NoName"
    response_code, result = user_check(telegram_id, name, default_rank)
    print(response_code, result)
    if response_code == 200:
        message = result.get("message", "An error occurred.")
        reply_markup = result.get("reply_markup")
        await update.message.reply_text(
            text=message,
            parse_mode='HTML',
            reply_markup=reply_markup,
        )
    elif response_code == 201:
        projectName = 'شريك الهمّة'

        keyboard = [
            # [InlineKeyboardButton('🤖 تعريف شريك الهمة',
            #                       callback_data='identification')],
            # [InlineKeyboardButton('🤔 كيف أحدّد أهدافي',
            #                       callback_data='how_to_set_goals')],
            [InlineKeyboardButton('📋 تسجيل أهدافي الخاصة',
                                  callback_data='set_goals')],
            # [InlineKeyboardButton('📚 الاطلاع على مسارات طلب العلم',
            #                       callback_data='learning_tracks')],
            # [InlineKeyboardButton('📥 الاتصال بنا', callback_data='contact_us')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f'🌹السلام عليكم <b>{name}</b>\n'
            '\n'
            f'مرحباً بكم معنا في <b>{projectName}</b> رفيقكم في تحقيق أهدافكم وشريككم نحو مستوى وعي أرقى 🍃\n'
            '\n'
            ' اختر(ي) طلبك من القائمة أسفله واستعن بالله ولا تعجز✔️'
            '\n',
            parse_mode='HTML',
            reply_markup=reply_markup,
        )

async def set_goals(update, context):

    await update.callback_query.edit_message_text(
        text='تم اختيار: <b>تسجيل أهدافي الخاصة📋</b>\n'
             '\n'
             'المرجو كتابة الهدف الرئيسي وإرساله، ومتابعة <b>الإرشادات</b>\n\n'
             'تفضل(ي) 🍃🖋️',
        parse_mode='HTML'
    )

    return MAIN_GOAL

async def main_goal_req(update, context):
    user_id = update.message.from_user.id
    main_goal = update.message.text

    # Store user data in context.user_data using user_id as a key
    if user_id not in context.user_data:
        context.user_data[user_id] = UserGoals(user_id)

    # Store the main goal in the user's goal data
    context.user_data[user_id].add_main_goal(user_id, main_goal)

    await update.message.reply_text(
        'تم تسجيل الهدف الرئيسي تحت عنوان:\n\n'
        f"<blockquote>{main_goal}</blockquote>\n\n"
        ' <b>تفضل(ي)</b> بتحديد الهدف الفرعي \n\n',
        parse_mode='HTML'
    )
    # Store main goal in user_data for later reference
    context.user_data[user_id].current_main_goal = main_goal

    return SUB_GOALS

async def sub_goal_req(update, context):
    user_id = update.message.from_user.id
    sub_goal = update.message.text

    if user_id not in context.user_data:
        await update.message.reply_text("يبدو أنك لم تحدد هدفًا رئيسيًا بعد. يرجى البدء بتحديد هدفك الرئيسي.")
        return ConversationHandler.END

    if sub_goal.lower() in ["انتهاء", "إنتهاء", "done"]:
        goals_count = context.user_data[user_id].goals_count()
        if len(goals_count.keys()) < 2:
            # Inform user they need at least two goals
            await update.message.reply_text(
                'المرجو تحديد هدفين رئيسيين على الأقل.\n'
                'اكتب(ي) "آخر" لإضافة هدف رئيسي جديد.'
            )
            return SUB_GOALS  # Stay in the same state and avoid sending the next message
        else:
            # Proceed to end the input if goals count is sufficient
            stt_code, goals_seed = context.user_data[user_id].launch(user_id)
            if stt_code == 200:
                keyboard = [[InlineKeyboardButton(
                    "كيف ستبدو أهدافك؟", callback_data="show_demo")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    '<blockquote>تم إنهاء الإدخال 🎉</blockquote>\n',
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    f"❌ حدث خطأ أثناء تسجيل الأهداف: {goals_seed}"
                )
            return ConversationHandler.END
    elif sub_goal.lower() in ["آخر", "اخر"]:
        # Handle adding a new main goal
        await update.message.reply_text(
            'تفضل(ي) بتحديد الهدف الرئيسي الآخر📝\n',
            parse_mode='HTML'
        )
        return MAIN_GOAL

    # Otherwise, add the sub-goal under the current main goal
    main_goal = context.user_data[user_id].current_main_goal
    context.user_data[user_id].add_sub_goal(user_id, main_goal, sub_goal)

    # Only send the confirmation message when a sub-goal is added successfully
    await update.message.reply_text(
        'تم تسجيل الهدف الفرعي تحت عنوان:\n'
        f"<blockquote>{sub_goal}</blockquote>\n"
        'الأهداف الحالية:\n'
        f"{context.user_data[user_id].get_goals_list()}\n\n"
        'اكتب(ي) "انتهاء" لإنهاء الإدخال\n'
        'أكتب(ي) "آخر" من أجل إضافة هدف رئيسي آخر',
        parse_mode='HTML'
    )

    return SUB_GOALS

async def show_demo(update, context):
    user_id = update.callback_query.from_user.id
    goals_list = show_demo_db(user_id)
    main_goals = list(goals_list.keys())  # Collect all main goals as options

    await context.bot.send_poll(
        chat_id=update.effective_chat.id,
        question="سجّل مهامك اليومية أثابك الله",
        options=main_goals,
        is_anonymous=False,
        allows_multiple_answers=True,
    )
    keyboard = [
        [InlineKeyboardButton("تعديل نص الأهداف", callback_data="edit_op")],
        # [InlineKeyboardButton("تحديد وقت إرسال المهمات",
        #                       callback_data="set_cron_opt_call")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(
        '<blockquote>استعن بالله ولا تعجز 🍃</blockquote>\n',
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def edit_op(update, context):
    user_id = update.callback_query.from_user.id
    goals_list = edit_prep(user_id)

    keyboard = [
        [InlineKeyboardButton(
            goal["text"], callback_data=f'{goal["type"]}***{goal["id"]}***{goal["text"]}')]
        for goal in goals_list
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(
        '<blockquote>اختر ما تريد تعديله</blockquote>\n',
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def edit_goal_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("⏳ معالجة طلبك...", parse_mode="HTML")

    
    if "***" in query.data:
        goal_type, goal_id, goal_text = query.data.split("***")
        context.user_data['goal_type'] = goal_type
        context.user_data['goal_id'] = goal_id
        context.user_data['old_goal_text'] = goal_text

        await query.edit_message_text(
            f'<blockquote>تم اختيار 🎯</blockquote>\n{goal_text}\n'
            '<b>أكتب نص الهدف الصحيح</b>',
            parse_mode='HTML'
        )
        return EDIT_GOAL

async def edit_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):

    new_goal_text = update.message.text
    goal_type = context.user_data.get('goal_type')
    goal_id = context.user_data.get('goal_id')
    old_goal_text = context.user_data.get('old_goal_text')

    result = updateGoal(update.message.from_user.id,
                        new_goal_text, goal_type, goal_id, old_goal_text)
    await update.message.reply_text(result, parse_mode='HTML')

    return ConversationHandler.END

async def set_cron_opt(update, context):
    keyboard = [
        [InlineKeyboardButton("يوميًا", callback_data="cronOption:daily")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(
        '<blockquote>تحديد وقت الإرسال  ⏲️</blockquote>\n',
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return SET_CRON

async def set_cron(update, context):
    selected_option = update.callback_query.data.split(":")[1]
    if selected_option == "daily":
        await update.callback_query.message.reply_text(
            text="<blockquote>أكتب الساعة والدقيقة التي تُريد</blockquote><b>مثال: 22:30</b>",
            parse_mode="HTML"
        )
        cron_type = context.user_data['cron_settings'] = "daily"
        return SET_CRON_TIME
    elif selected_option == "weekly":
        days_of_week = [
            "الأحد",  # Sunday
            "الإثنين",  # Monday
            "الثلاثاء",  # Tuesday
            "الأربعاء",  # Wednesday
            "الخميس",  # Thursday
            "الجمعة",  # Friday
            "السبت"  # Saturday
        ]
        keyboard = [InlineKeyboardButton(
            day, callback_data="weekday") for day in days_of_week]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.reply_text(
            "اختر اليوم الذي تريد تحديده للموعد الأسبوعي:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return SET_CRON_WEEKDAY

    elif selected_option == "custom":
        await update.callback_query.message.reply_text("تم تحديد الإرسال حسب التخصيص.")
    else:
        await update.callback_query.message.reply_text("خيارات غير معروفة.")

async def set_cron_time(update, context):
    keyboard = [[  InlineKeyboardButton("تعديل", callback_data="edit_cron_launch")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    time = update.message.text
    user_id = update.message.from_user.id
    cron_type = context.user_data.get('cron_settings')
    res = cron_seed(user_id, cron_type, time)
    if res == True:
        await update.message.reply_text(
        "<blockquote>تم تحديد وقت الإرسال ⏰</blockquote>\n"
        f"<b>يومياً على الساعة:  {time}</b> ",
        reply_markup=reply_markup,
        parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
        "<blockquote>لا يمكن تحديد التوقيت</blockquote>\n"
        f"<b>خطأ داخلي</b> ",
        reply_markup=reply_markup,
        parse_mode='HTML'
        )
    return ConversationHandler.END

async def edit_cron(update, context):
    await update.callback_query.message.reply_text(
    "المرجو كتابة التوقيت بدقّة (مثال: 06:00)"
    )
    return EDIT_CRON_TIME

async def edit_cron_time(update, context):
    user_id = update.message.from_user.id
    new_cron_time = update.message.text
    cron_type = context.user_data.get('cron_settings')
    res = cron_seed(user_id, cron_type, new_cron_time)
    if res == True:
        cron_command(user_id,new_cron_time)
        await update.message.reply_text(f"تم التحديث إلى:  {new_cron_time}")
    else:
        await update.message.reply_text("لا يمكن تحديث التوقيت في الوقت الراهن")

    return ConversationHandler.END

async def cron_command(user_id, time):
    # PythonAnywhere API URL
    api_url = "https://www.pythonanywhere.com/api/v0/user/ElkhamlichiOussa/scheduled_tasks/"
    
    # Your PythonAnywhere API key
    api_key = "a41772ed5416f9eab35151f7ab443c797562ba6a"
    
    # Cron job details
    command = f"python3 /home/ElkhamlichiOussama/purpose_ally/scheduled/tasks.py {user_id}"
    # Schedule cron job to run daily at 8 AM

    time_obj = datetime.strptime(time, "%H:%M")
    
    # Extract hour and minute
    hour = time_obj.hour
    minute = time_obj.minute
    
    # Convert to cron format: minute hour * * *
    schedule = f"{minute} {hour} * * *"

    print(schedule)    
    # return cron_format
    
    # Create headers with API key for authentication
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json"
    }
    
    # Data to create a new cron job
    data = {
        "enabled": True,
        "command": command,
        "schedule": schedule,
    }
    
    # Make the API request to create the cron job
    response = requests.post(api_url, headers=headers, data=json.dumps(data))
    
    # Check if the cron job was created successfully
    if response.status_code == 201:
        print("Cron job created successfully.")
    else:
        print(f"Failed to create cron job: {response.status_code}")
        print(response.text)

async def cancel(update, context):
    # Envoie un message à l'utilisateur pour lui confirmer l'annulation
    update.message.reply_text("La conversation a été annulée. N'hésitez pas à me recontacter plus tard.")
    
    # Termine la conversation en renvoyant la constante ConversationHandler.END
    return ConversationHandler.END

async def maingoal_achieved(update, context):
    user_id = update.message.from_user.id
    stt_code, res = await asyncio.to_thread(get_goals,user_id)  
    # await update.message.reply_text(res)
    if(len(res) == 0):
        await context.bot.send_message(user_id,
            "<blockquote>يبدو أنه ليس لديك أية أهداف</blockquote>\n\n",
            parse_mode='HTML'
        )
    else:
        message_text = "<b>أهدافك 🎯</b>\n\n"
        keyboard = []
        if stt_code == 200:
            for main_goal, data in res.items():
                if data['main_status'] != 'done':
                    message_text += f"<b>الهدف الرئيسي:</b> {main_goal}\n"

                    keyboard.append([InlineKeyboardButton(
                        f"✅ تم إنجاز الهدف الرئيسي: {main_goal}",
                        callback_data=f"done_main_{data['goal_id']}"
                    )])
                else:
                    message_text += f"<b>الهدف الرئيسي:</b> {main_goal} ✅\n"

                    keyboard.append([InlineKeyboardButton(
                        f"✅ تم إنجاز الهدف الرئيسي: {main_goal}",
                        callback_data=f"done_main_{data['goal_id']}"
                    )])

                for subgoal in data['subgoals']:
                    if subgoal['status'] != 'done':
                        message_text += f"    • <b>الهدف الفرعي:</b> {subgoal['subgoal_title']} \n"

                        keyboard.append([InlineKeyboardButton(
                            f"✅ تم إنجاز الهدف الفرعي: {subgoal['subgoal_title']}",
                            callback_data=f"done_sub_{subgoal['subgoal_id']}"
                        )])
                    else:
                        message_text += f"    • <b>الهدف الفرعي:</b> {subgoal['subgoal_title']} ✅\n"

                        keyboard.append([InlineKeyboardButton(
                            f"✅ تم إنجاز الهدف الفرعي: {subgoal['subgoal_title']}",
                            callback_data=f"done_sub_{subgoal['subgoal_id']}"
                        )])

                message_text += "\n" 

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                message_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            print("X____x")

async def old_goals(update, context):
    await update.callback_query.answer()
    user_id = update.callback_query.from_user.id
    goals_list = show_demo_db(user_id)
    unformatted_list = edit_prep(user_id)
    keyboard = [
        [InlineKeyboardButton("تعديل/حذف نص الأهداف", callback_data="edit_op")],
    ]
    formatted_text = ""
    main_goal_indent = "🎯 " 
    sub_goal_indent = "    • "

    for item in unformatted_list:
        if item["type"] == "main":
            formatted_text += main_goal_indent + item['text'] + "\n"
        elif item["type"] == "sub":
            formatted_text += sub_goal_indent + item['text'] + "\n"
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(
        '<blockquote>تفاصيل الأهداف🍃</blockquote>\n'
        f"\n{formatted_text}\n"
        f"<b>الإرسال اليومي على الساعة:</b> 00:00 \n",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def new_start(update, context):
    await update.callback_query.answer()
    user = update.effective_user
    name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "NoName"
    username=user.username or None
    res = await asyncio.to_thread(destroy_user,user.id)

    if res != 200:
        await update.callback_query.message.reply_text("Failed to reset user data. Please try again later.")
        return  

    result = await asyncio.to_thread(add_user, user.id, username, name, default_rank)
    if result is None:
        await update.callback_query.message.reply_text("Failed to initialize user data. Please try again later.")
        return  

    project_name = 'شريك الهمّة'
    keyboard = [
        # [InlineKeyboardButton('🤖 تعريف شريك الهمة', callback_data='identification')],
        # [InlineKeyboardButton('🤔 كيف أحدّد أهدافي', callback_data='how_to_set_goals')],
        [InlineKeyboardButton('📋 تسجيل أهدافي الخاصة', callback_data='set_goals')],
        # [InlineKeyboardButton('📚 الاطلاع على مسارات طلب العلم', callback_data='learning_tracks')],
        # [InlineKeyboardButton('📥 الاتصال بنا', callback_data='contact_us')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the welcome message
    await update.callback_query.message.reply_text(
        f'🌹السلام عليكم <b>{name}</b>\n'
        '\n'
        f'مرحباً بكم معنا في <b>{project_name}</b> رفيقكم في تحقيق أهدافكم وشريككم نحو مستوى وعي أرقى 🍃\n'
        '\n'
        ' اختر(ي) طلبك من القائمة أسفله واستعن بالله ولا تعجز✔️'
        '\n',
        parse_mode='HTML',
        reply_markup=reply_markup,
    )

async def update_goals(update, context):
    user_id = update.callback_query.from_user.id
    query = update.callback_query
    await query.answer()  

    callback_data = query.data
    if callback_data.startswith("done_main_"):
        goal_id = callback_data.split("_")[2] 
        res = await asyncio.to_thread(mark_as_done, "maingoal", goal_id, user_id)
        await query.message.reply_text(f"تم إنجاز الهدف الرئيسي ✅")

    elif callback_data.startswith("done_sub_"):
        subgoal_id = callback_data.split("_")[2] 
        res = await asyncio.to_thread(mark_as_done,"subgoal", subgoal_id, user_id)
        await query.message.reply_text(f"تم إنجاز الهدف الفرعي✅")

async def add_goals(update,context):
    await update.message.reply_text(
        text='<b>إدخال أهداف رئيسية أخرى📋</b>\n'
             '\n'
             'المرجو كتابة الهدف الرئيسي وإرساله، ومتابعة <b>الإرشادات</b>\n\n'
             'تفضل(ي) 🍃🖋️',
        parse_mode='HTML'
    )

    return EXTRA_MAIN_GOALS

async def extra_maingoals(update, context):
    user_id = update.message.from_user.id
    main_goal = update.message.text

    if user_id not in context.user_data:
        context.user_data[user_id] = UserGoals(user_id)

    context.user_data[user_id].add_extra_maingoals(user_id, main_goal)

    await update.message.reply_text(
        'تم تسجيل الهدف الرئيسي تحت عنوان:\n\n'
        f"<blockquote>{main_goal}</blockquote>\n\n"
        ' <b>تفضل(ي)</b> بتحديد الهدف الفرعي \n\n',
        parse_mode='HTML'
    )
    context.user_data[user_id].current_extra_main_goal = main_goal

    return EXTRA_SUB_GOALS

async def extra_subgoals(update, context):
    user_id = update.message.from_user.id
    sub_goal = update.message.text

    if user_id not in context.user_data:
        await update.message.reply_text("يبدو أنك لم تحدد هدفًا رئيسيًا بعد. يرجى البدء بتحديد هدفك الرئيسي.")
        return ConversationHandler.END

    if sub_goal.lower() in ["انتهاء", "إنتهاء", "done"]:
        goals_count = context.user_data[user_id].extra_goals_count()
        # if len(goals_count.keys()) < 2:
        #     # Inform user they need at least two goals
        #     await update.message.reply_text(
        #         'المرجو تحديد هدفين رئيسيين على الأقل.\n'
        #         'اكتب(ي) "آخر" لإضافة هدف رئيسي جديد.'
        #     )
        #     return SUB_GOALS  # Stay in the same state and avoid sending the next message
        # else:
        # Proceed to end the input if goals count is sufficient
        goals_seed = context.user_data[user_id].extra_launch(user_id)
        keyboard = [[InlineKeyboardButton(
            "كيف ستبدو أهدافك؟", callback_data="show_new_goals")]]
        # reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            '<blockquote>تم إنهاء الإدخال 🎉</blockquote>\n',
            # reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return ConversationHandler.END
    elif sub_goal.lower() in ["آخر", "اخر"]:
        # Handle adding a new main goal
        await update.message.reply_text(
            'تفضل(ي) بتحديد الهدف الرئيسي الآخر📝\n',
            parse_mode='HTML'
        )
        return EXTRA_MAIN_GOALS

    # Otherwise, add the sub-goal under the current main goal
    main_goal = context.user_data[user_id].current_extra_main_goal
    context.user_data[user_id].add_extra_subgoals(user_id, main_goal, sub_goal)

    # Only send the confirmation message when a sub-goal is added successfully
    await update.message.reply_text(
        'تم تسجيل الهدف الفرعي تحت عنوان:\n'
        f"<blockquote>{sub_goal}</blockquote>\n"
        'الأهداف الحالية:\n'
        f"{context.user_data[user_id].get_extra_goals_list()}\n\n"
        'اكتب(ي) "انتهاء" لإنهاء الإدخال\n'
        'أكتب(ي) "آخر" من أجل إضافة هدف رئيسي آخر',
        parse_mode='HTML'
    )

    return EXTRA_SUB_GOALS

async def show_new_goals(update, context):
    await update.callback_query.answer()
    user_id = update.callback_query.from_user.id
    keyboard = [
        [InlineKeyboardButton("تعديل/حذف نص الأهداف", callback_data="edit_op")],
    ]
    unformatted_list = edit_prep(user_id)
    formatted_text = ""
    main_goal_indent = "🎯 " 
    sub_goal_indent = "    • "

    for item in unformatted_list:
        if item["type"] == "main":
            formatted_text += main_goal_indent + item['text'] + "\n"
        elif item["type"] == "sub":
            formatted_text += sub_goal_indent + item['text'] + "\n"
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(
        '<blockquote>تفاصيل الأهداف🍃</blockquote>\n'
        f"\n{formatted_text}\n"
        f"<b>الإرسال اليومي على الساعة:</b> 00:00 ",
        # reply_markup=reply_markup,
        parse_mode='HTML'
    )
    keyboard = [
        [InlineKeyboardButton("تعديل/حذف نص الأهداف", callback_data="edit_op")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(
        '<blockquote>استعن بالله ولا تعجز 🍃</blockquote>\n',
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def daily_goals_checking(update, context):
    poll_answer = update.poll_answer
    poll_id = poll_answer.poll_id
    option_ids = poll_answer.option_ids
    user_id = poll_answer.user.id

    res = await asyncio.to_thread(get_daily_goals_check, user_id, poll_id, option_ids)

    if res:
         context.bot.send_message(
            chat_id=user_id,
            text="تم تسجيل مهامك اليومية بنجاح ✨"
        )
    else:
        context.bot.send_message(
            chat_id=user_id,
            text="حدث خطأ أثناء تسجيل مهامك اليومية. يرجى المحاولة مرة أخرى لاحقًا."
        )
        
convo_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("goal_achieved", maingoal_achieved),
            CommandHandler("test", set_command_menu),
            CommandHandler("add_goals", add_goals),
            CallbackQueryHandler(set_goals, pattern='set_goals'),
            CallbackQueryHandler(edit_op, pattern='edit_op'),
            CallbackQueryHandler(edit_goal_selection, pattern=".*\*\*\*.*"),
            CallbackQueryHandler(set_cron_opt, pattern='set_cron_opt_call'),
            CallbackQueryHandler(edit_cron, pattern='edit_cron_launch'),
            CallbackQueryHandler(show_demo, pattern='show_demo'),
            CallbackQueryHandler(old_goals, pattern='indeed'),
            CallbackQueryHandler(new_start, pattern='new_start'),
            CallbackQueryHandler(update_goals, pattern="done_"),
            CallbackQueryHandler(show_new_goals, pattern='show_new_goals'),

        ],
        states={
            MAIN_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_goal_req)],
            SUB_GOALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, sub_goal_req)],
            EDIT_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_goal)],
            SET_CRON: [CallbackQueryHandler(set_cron, pattern='cronOption:*')],
            SET_CRON_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_cron_time)],
            EDIT_CRON_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_cron_time)],
            SET_CRON_WEEKDAY: [CallbackQueryHandler(set_cron, pattern='weekday')],
            EXTRA_MAIN_GOALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, extra_maingoals)],
            EXTRA_SUB_GOALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, extra_subgoals)],

        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

application.add_handler(convo_handler)
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^#تسجيل'), signup))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^#إضافة_حصة'), handle_add_session))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^#استثماراتي'), handle_stats))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^#حذف_حصة'), handle_delete_session))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^#عرض_الخصائص'), show_commands))
application.add_handler(PollAnswerHandler(daily_goals_checking))


