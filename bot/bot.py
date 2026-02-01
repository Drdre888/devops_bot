import logging
import re
import os
import paramiko
import psycopg2
from psycopg2 import Error
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler

load_dotenv()

TOKEN = os.getenv('TOKEN')
RM_HOST = os.getenv('RM_HOST')
RM_PORT = int(os.getenv('RM_PORT', 22))
RM_USER = os.getenv('RM_USER')
RM_PASSWORD = os.getenv('RM_PASSWORD')

# Параметры БД
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT', 5432)
DB_DATABASE = os.getenv('DB_DATABASE')

# Настройка логирования
logging.basicConfig(
    filename='bot_logfile.txt',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

logging.getLogger("paramiko").setLevel(logging.WARNING)


# Функция подключения к БД
def get_db_connection():
    try:
        connection = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_DATABASE
        )
        logger.info("Successfully connected to database")
        return connection
    except (Exception, Error) as error:
        logger.error(f"Error connecting to PostgreSQL: {error}")
        return None


# SSH функция для выполнения команд
def execute_ssh_command(command):
    try:
        logger.info(f"Executing SSH command: {command}")

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD, timeout=30)

        stdin, stdout, stderr = client.exec_command(command, timeout=30)
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        client.close()

        if output:
            logger.info(f"Command executed successfully. Output length: {len(output)} chars")
            return output
        elif error:
            logger.warning(f"Command stderr: {error[:200]}")
            return error
        else:
            logger.warning("Command returned no data")
            return "Нет данных"

    except Exception as e:
        logger.error(f"SSH Connection Error: {str(e)}")
        return f"Ошибка подключения: {str(e)}"


# Базовые команды
def start(update: Update, context):
    user = update.effective_user
    logger.info(f"User {user.username} ({user.id}) started the bot")
    update.message.reply_text(f'Привет, {user.full_name}!\n\n'
                              'Доступные команды:\n'
                              '/find_email - Поиск email адресов\n'
                              '/find_phone_number - Поиск номеров телефонов\n'
                              '/verify_password - Проверка сложности пароля\n'
                              '/get_emails - Показать email из БД\n'
                              '/get_phone_numbers - Показать телефоны из БД\n'
                              '/get_repl_logs - Логи репликации\n'
                              '/get_release - Информация о релизе\n'
                              '/get_uname - Информация о системе\n'
                              '/get_uptime - Время работы системы\n'
                              '/get_df - Состояние файловой системы\n'
                              '/get_free - Состояние памяти\n'
                              '/get_mpstat - Производительность системы\n'
                              '/get_w - Работающие пользователи\n'
                              '/get_auths - Последние 10 входов\n'
                              '/get_critical - Последние 5 критических событий\n'
                              '/get_ps - Запущенные процессы\n'
                              '/get_ss - Используемые порты\n'
                              '/get_apt_list - Установленные пакеты\n'
                              '/get_services - Запущенные сервисы')


# Поиск Email
def find_email_command(update: Update, context):
    logger.info("User requested email search")
    update.message.reply_text('Введите текст для поиска email адресов:')
    return 'find_email'


def find_email(update: Update, context):
    user_input = update.message.text
    logger.info(f"Searching for emails in text (length: {len(user_input)} chars)")

    email_regex = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    email_list = email_regex.findall(user_input)

    if not email_list:
        logger.info("No emails found")
        update.message.reply_text('Email адреса не найдены')
        return ConversationHandler.END

    emails = ''
    for i in range(len(email_list)):
        emails += f'{i + 1}. {email_list[i]}\n'

    update.message.reply_text(emails)
    logger.info(f"Found {len(email_list)} emails: {email_list}")

    # Сохраняем найденные email в контексте
    context.user_data['found_emails'] = email_list

    # Предлагаем сохранить в БД
    keyboard = [
        [
            InlineKeyboardButton("Да", callback_data='save_emails_yes'),
            InlineKeyboardButton("Нет", callback_data='save_emails_no')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Сохранить найденные email адреса в базу данных?', reply_markup=reply_markup)

    return 'save_email_choice'


def save_emails_handler(update: Update, context):
    query = update.callback_query
    query.answer()

    if query.data == 'save_emails_no':
        query.edit_message_text("Данные не сохранены.")
        logger.info("User declined to save emails")
        return ConversationHandler.END

    email_list = context.user_data.get('found_emails', [])

    connection = get_db_connection()
    if not connection:
        query.edit_message_text("Ошибка подключения к базе данных.")
        logger.error("Failed to connect to database for saving emails")
        return ConversationHandler.END

    try:
        cursor = connection.cursor()
        saved_count = 0

        for email in email_list:
            cursor.execute("SELECT id FROM emails WHERE email = %s", (email,))
            if cursor.fetchone() is None:
                cursor.execute("INSERT INTO emails (email) VALUES (%s)", (email,))
                saved_count += 1
                logger.info(f"Email saved to database: {email}")
            else:
                logger.info(f"Email already exists in database: {email}")

        connection.commit()
        cursor.close()
        connection.close()

        query.edit_message_text(f"Успешно сохранено {saved_count} email адресов в базу данных.")
        logger.info(f"Successfully saved {saved_count} emails to database")

    except (Exception, Error) as error:
        query.edit_message_text(f"Ошибка при сохранении в базу данных: {error}")
        logger.error(f"Error saving emails to database: {error}")
        if connection:
            connection.close()

    return ConversationHandler.END


# Поиск номеров телефонов
def find_phone_number_command(update: Update, context):
    logger.info("User requested phone number search")
    update.message.reply_text('Введите текст для поиска номеров телефонов:')
    return 'find_phone_number'


def find_phone_number(update: Update, context):
    user_input = update.message.text
    logger.info(f"Searching for phone numbers in text (length: {len(user_input)} chars)")

    phone_regex = re.compile(
        r'(?:\+7|8)'
        r'[\s\-]?'
        r'(?:\(\d{3}\)|\d{3})'
        r'[\s\-]?'
        r'\d{3}'
        r'[\s\-]?'
        r'\d{2}'
        r'[\s\-]?'
        r'\d{2}'
    )

    phone_list = phone_regex.findall(user_input)

    if not phone_list:
        logger.info("No phone numbers found")
        update.message.reply_text('Телефонные номера не найдены')
        return ConversationHandler.END

    phones = ''
    for i in range(len(phone_list)):
        phones += f'{i + 1}. {phone_list[i]}\n'

    update.message.reply_text(phones)
    logger.info(f"Found {len(phone_list)} phone numbers: {phone_list}")

    # Сохраняем найденные телефоны в контексте
    context.user_data['found_phones'] = phone_list

    # Предлагаем сохранить в БД
    keyboard = [
        [
            InlineKeyboardButton("Да", callback_data='save_phones_yes'),
            InlineKeyboardButton("Нет", callback_data='save_phones_no')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Сохранить найденные номера телефонов в базу данных?', reply_markup=reply_markup)

    return 'save_phone_choice'


def save_phones_handler(update: Update, context):
    query = update.callback_query
    query.answer()

    if query.data == 'save_phones_no':
        query.edit_message_text("Данные не сохранены.")
        logger.info("User declined to save phone numbers")
        return ConversationHandler.END

    phone_list = context.user_data.get('found_phones', [])

    connection = get_db_connection()
    if not connection:
        query.edit_message_text("Ошибка подключения к базе данных.")
        logger.error("Failed to connect to database for saving phones")
        return ConversationHandler.END

    try:
        cursor = connection.cursor()
        saved_count = 0

        for phone in phone_list:
            cursor.execute("SELECT id FROM phone_numbers WHERE phone_number = %s", (phone,))
            if cursor.fetchone() is None:
                cursor.execute("INSERT INTO phone_numbers (phone_number) VALUES (%s)", (phone,))
                saved_count += 1
                logger.info(f"Phone number saved to database: {phone}")
            else:
                logger.info(f"Phone number already exists in database: {phone}")

        connection.commit()
        cursor.close()
        connection.close()

        query.edit_message_text(f"Успешно сохранено {saved_count} номеров телефонов в базу данных.")
        logger.info(f"Successfully saved {saved_count} phone numbers to database")

    except (Exception, Error) as error:
        query.edit_message_text(f"Ошибка при сохранении в базу данных: {error}")
        logger.error(f"Error saving phone numbers to database: {error}")
        if connection:
            connection.close()

    return ConversationHandler.END


# Проверка сложности пароля
def verify_password_command(update: Update, context):
    logger.info("User requested password verification")
    update.message.reply_text('Введите пароль для проверки:')
    return 'verify_password'


def verify_password(update: Update, context):
    password = update.message.text
    logger.info(f"Verifying password (length: {len(password)})")

    password_regex = re.compile(
        r'^(?=.*[A-Z])'
        r'(?=.*[a-z])'
        r'(?=.*\d)'
        r'(?=.*[!@#$%^&*()])'
        r'.{8,}$'
    )

    if password_regex.match(password):
        update.message.reply_text('Пароль сложный')
        logger.info("Password verification: STRONG")
    else:
        update.message.reply_text('Пароль простой')
        logger.info("Password verification: WEAK")

    return ConversationHandler.END


# Получение данных из БД

# Получить все email из БД
def get_emails(update: Update, context):
    logger.info("Command: /get_emails")

    connection = get_db_connection()
    if not connection:
        update.message.reply_text("Ошибка подключения к базе данных.")
        logger.error("Failed to connect to database")
        return

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT id, email FROM emails ORDER BY id")
        emails = cursor.fetchall()

        cursor.close()
        connection.close()

        if not emails:
            update.message.reply_text("В базе данных нет сохраненных email адресов.")
            logger.info("No emails found in database")
            return

        response = "Email адреса из базы данных:\n\n"
        for email_id, email in emails:
            response += f"{email_id}. {email}\n"

        update.message.reply_text(response)
        logger.info(f"Retrieved {len(emails)} emails from database")

    except (Exception, Error) as error:
        update.message.reply_text(f"Ошибка при получении данных: {error}")
        logger.error(f"Error retrieving emails from database: {error}")
        if connection:
            connection.close()


# Получить все телефоны из БД
def get_phone_numbers(update: Update, context):
    logger.info("Command: /get_phone_numbers")

    connection = get_db_connection()
    if not connection:
        update.message.reply_text("Ошибка подключения к базе данных.")
        logger.error("Failed to connect to database")
        return

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT id, phone_number FROM phone_numbers ORDER BY id")
        phones = cursor.fetchall()

        cursor.close()
        connection.close()

        if not phones:
            update.message.reply_text("В базе данных нет сохраненных номеров телефонов.")
            logger.info("No phone numbers found in database")
            return

        response = "Номера телефонов из базы данных:\n\n"
        for phone_id, phone in phones:
            response += f"{phone_id}. {phone}\n"

        update.message.reply_text(response)
        logger.info(f"Retrieved {len(phones)} phone numbers from database")

    except (Exception, Error) as error:
        update.message.reply_text(f"Ошибка при получении данных: {error}")
        logger.error(f"Error retrieving phone numbers from database: {error}")
        if connection:
            connection.close()


# Получить логи репликации
def get_repl_logs(update: Update, context):
    logger.info("Command: /get_repl_logs")
    
    result = execute_ssh_command('docker exec postgres_replica bash -c "cat /var/lib/postgresql/data/log/postgresql-*.log"')
    
    if not result or result == "Нет данных":
        result = "Логи репликации не найдены."
        logger.warning("Replication logs not found")

    chunk_size = 3500
    if len(result) > chunk_size:
        parts_sent = 0
        for i in range(0, len(result), chunk_size):
            chunk = result[i:i + chunk_size]
            parts_sent += 1
            if i == 0:
                update.message.reply_text(f"Логи репликации (часть {parts_sent}):\n\n{chunk}")
            else:
                update.message.reply_text(f"Часть {parts_sent}:\n\n{chunk}")
        logger.info(f"Replication logs sent in {parts_sent} parts")
    else:
        update.message.reply_text(result[:4000])
        logger.info("Replication logs sent to user")


# Мониторинг Linux системы

def get_release(update: Update, context):
    logger.info("Command: /get_release")
    result = execute_ssh_command('cat /etc/os-release')
    update.message.reply_text(result[:4000])
    logger.info("Response sent to user")


def get_uname(update: Update, context):
    logger.info("Command: /get_uname")
    result = execute_ssh_command('uname -a')
    update.message.reply_text(result)
    logger.info("Response sent to user")


def get_uptime(update: Update, context):
    logger.info("Command: /get_uptime")
    result = execute_ssh_command('uptime')
    update.message.reply_text(result)
    logger.info("Response sent to user")


def get_df(update: Update, context):
    logger.info("Command: /get_df")
    result = execute_ssh_command('df -h')
    update.message.reply_text(result[:4000])
    logger.info("Response sent to user")


def get_free(update: Update, context):
    logger.info("Command: /get_free")
    result = execute_ssh_command('free -h')
    update.message.reply_text(result)
    logger.info("Response sent to user")


def get_mpstat(update: Update, context):
    logger.info("Command: /get_mpstat")
    result = execute_ssh_command('mpstat 2>/dev/null')
    update.message.reply_text(result[:4000])
    logger.info("Response sent to user")


def get_w(update: Update, context):
    logger.info("Command: /get_w")
    result = execute_ssh_command('w')
    update.message.reply_text(result[:4000])
    logger.info("Response sent to user")


def get_auths(update: Update, context):
    logger.info("Command: /get_auths")
    result = execute_ssh_command('last -n 10 2>/dev/null')
    update.message.reply_text(result[:4000])
    logger.info("Response sent to user")


def get_critical(update: Update, context):
    logger.info("Command: /get_critical")
    result = execute_ssh_command('journalctl -p crit -n 5 --no-pager 2>/dev/null')
    update.message.reply_text(result[:4000])
    logger.info("Response sent to user")


def get_ps(update: Update, context):
    logger.info("Command: /get_ps")
    result = execute_ssh_command('ps aux | head -20')
    update.message.reply_text(result[:4000])
    logger.info("Response sent to user")


def get_ss(update: Update, context):
    logger.info("Command: /get_ss")
    result = execute_ssh_command('ss -tuln')
    update.message.reply_text(result[:4000])
    logger.info("Response sent to user")


def get_apt_list_command(update: Update, context):
    logger.info("Command: /get_apt_list - waiting for user input")
    update.message.reply_text('Введите название пакета для поиска или "all" для вывода всех пакетов:')
    return 'get_apt_list'


def get_apt_list(update: Update, context):
    user_input = update.message.text.strip()
    logger.info(f"Searching for package: '{user_input}'")

    if user_input.lower() == 'all':
        result = execute_ssh_command('apt list --installed 2>/dev/null')

        # Разбиваем на части по 3500 символов
        chunk_size = 3500
        parts_sent = 0
        for i in range(0, len(result), chunk_size):
            chunk = result[i:i + chunk_size]
            parts_sent += 1
            if i == 0:
                update.message.reply_text(f"Установленные пакеты (часть {parts_sent}):\n\n{chunk}")
            else:
                update.message.reply_text(f"Часть {parts_sent}:\n\n{chunk}")

        logger.info(f"Sent all packages in {parts_sent} parts")
    else:
        result = execute_ssh_command(f'apt list --installed 2>/dev/null | grep -i {user_input}')

        if result and result.strip() and result != "Нет данных":
            header = "Найденные пакеты:\n\n"
            max_length = 4000 - len(header)
            update.message.reply_text(header + result[:max_length])
            logger.info(f"Package '{user_input}' found and sent to user")
        else:
            update.message.reply_text(f'Пакет "{user_input}" не найден')
            logger.info(f"Package '{user_input}' not found")

    return ConversationHandler.END


def get_services(update: Update, context):
    logger.info("Command: /get_services")
    result = execute_ssh_command('systemctl list-units --type=service --state=running | head -20')
    update.message.reply_text(result[:4000])
    logger.info("Response sent to user")


def get_services(update: Update, context):
    logger.info("Command: /get_services")
    result = execute_ssh_command('systemctl list-units --type=service --state=running | head -20')
    update.message.reply_text(result[:4000])
    logger.info("Response sent to user")


def main():
    logger.info("=" * 50)
    logger.info("Bot starting...")
    logger.info(f"Connecting to remote host: {RM_HOST}:{RM_PORT}")

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Обработчики диалогов
    conv_handler_email = ConversationHandler(
        entry_points=[CommandHandler('find_email', find_email_command)],
        states={
            'find_email': [MessageHandler(Filters.text & ~Filters.command, find_email)],
            'save_email_choice': [CallbackQueryHandler(save_emails_handler, pattern='^save_emails_')]
        },
        fallbacks=[]
    )

    conv_handler_phone = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', find_phone_number_command)],
        states={
            'find_phone_number': [MessageHandler(Filters.text & ~Filters.command, find_phone_number)],
            'save_phone_choice': [CallbackQueryHandler(save_phones_handler, pattern='^save_phones_')]
        },
        fallbacks=[]
    )

    conv_handler_password = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verify_password_command)],
        states={
            'verify_password': [MessageHandler(Filters.text & ~Filters.command, verify_password)],
        },
        fallbacks=[]
    )

    conv_handler_apt = ConversationHandler(
        entry_points=[CommandHandler('get_apt_list', get_apt_list_command)],
        states={
            'get_apt_list': [MessageHandler(Filters.text & ~Filters.command, get_apt_list)],
        },
        fallbacks=[]
    )

    # Регистрация обработчиков
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(conv_handler_email)
    dp.add_handler(conv_handler_phone)
    dp.add_handler(conv_handler_password)
    dp.add_handler(conv_handler_apt)

    # Команды работы с БД
    dp.add_handler(CommandHandler("get_emails", get_emails))
    dp.add_handler(CommandHandler("get_phone_numbers", get_phone_numbers))
    dp.add_handler(CommandHandler("get_repl_logs", get_repl_logs))

    # Команды мониторинга
    dp.add_handler(CommandHandler("get_release", get_release))
    dp.add_handler(CommandHandler("get_uname", get_uname))
    dp.add_handler(CommandHandler("get_uptime", get_uptime))
    dp.add_handler(CommandHandler("get_df", get_df))
    dp.add_handler(CommandHandler("get_free", get_free))
    dp.add_handler(CommandHandler("get_mpstat", get_mpstat))
    dp.add_handler(CommandHandler("get_w", get_w))
    dp.add_handler(CommandHandler("get_auths", get_auths))
    dp.add_handler(CommandHandler("get_critical", get_critical))
    dp.add_handler(CommandHandler("get_ps", get_ps))
    dp.add_handler(CommandHandler("get_ss", get_ss))
    dp.add_handler(CommandHandler("get_services", get_services))

    # Запуск бота
    logger.info("Bot is ready and polling for updates")
    logger.info("=" * 50)
    updater.start_polling()
    updater.idle()

    logger.info("Bot stopped")


if __name__ == '__main__':
    main()
