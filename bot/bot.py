import logging
import re
import os
import paramiko
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

load_dotenv()

TOKEN = os.getenv('TOKEN')
RM_HOST = os.getenv('RM_HOST')
RM_PORT = int(os.getenv('RM_PORT', 22))
RM_USER = os.getenv('RM_USER')
RM_PASSWORD = os.getenv('RM_PASSWORD')

# Настройка логирования
logging.basicConfig(
    filename='bot_logfile.txt',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

logging.getLogger("paramiko").setLevel(logging.WARNING)


# SSH функция для выполнения команд
def execute_ssh_command(command):
    try:
        logger.info(f"Executing SSH command: {command}")

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD)

        stdin, stdout, stderr = client.exec_command(command)
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
    return ConversationHandler.END


# Поиск номеров телефонов
def find_phone_number_command(update: Update, context):
    logger.info("User requested phone number search")
    update.message.reply_text('Введите текст для поиска номеров телефонов:')
    return 'find_phone_number'


def find_phone_number(update: Update, context):
    user_input = update.message.text
    logger.info(f"Searching for phone numbers in text (length: {len(user_input)} chars)")

    # Регулярное выражение для различных форматов
    phone_regex = re.compile(
        r'(?:\+7|8)'  # Начинается с +7 или 8
        r'[\s\-]?'  # Опциональный пробел или дефис
        r'(?:\(\d{3}\)|\d{3})'  # (XXX) или XXX
        r'[\s\-]?'  # Опциональный пробел или дефис
        r'\d{3}'  # XXX
        r'[\s\-]?'  # Опциональный пробел или дефис
        r'\d{2}'  # XX
        r'[\s\-]?'  # Опциональный пробел или дефис
        r'\d{2}'  # XX
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
    return ConversationHandler.END


# Проверка сложности пароля
def verify_password_command(update: Update, context):
    logger.info("User requested password verification")
    update.message.reply_text('Введите пароль для проверки:')
    return 'verify_password'


def verify_password(update: Update, context):
    password = update.message.text
    logger.info(f"Verifying password (length: {len(password)})")

    # Проверка требований к паролю
    password_regex = re.compile(
        r'^(?=.*[A-Z])'  # Минимум одна заглавная буква
        r'(?=.*[a-z])'  # Минимум одна строчная буква
        r'(?=.*\d)'  # Минимум одна цифра
        r'(?=.*[!@#$%^&*()])'  # Минимум один спецсимвол
        r'.{8,}$'  # Минимум 8 символов
    )

    if password_regex.match(password):
        update.message.reply_text('Пароль сложный')
        logger.info("Password verification: STRONG")
    else:
        update.message.reply_text('Пароль простой')
        logger.info("Password verification: WEAK")

    return ConversationHandler.END


# Мониторинг Linux системы

# 4.1 Информация о релизе
def get_release(update: Update, context):
    logger.info("Command: /get_release")
    result = execute_ssh_command('cat /etc/os-release')
    update.message.reply_text(result[:4000])
    logger.info("Response sent to user")


# 4.2 Информация о системе
def get_uname(update: Update, context):
    logger.info("Command: /get_uname")
    result = execute_ssh_command('uname -a')
    update.message.reply_text(result)
    logger.info("Response sent to user")


# 4.3 Время работы
def get_uptime(update: Update, context):
    logger.info("Command: /get_uptime")
    result = execute_ssh_command('uptime')
    update.message.reply_text(result)
    logger.info("Response sent to user")


# 4.4 Файловая система
def get_df(update: Update, context):
    logger.info("Command: /get_df")
    result = execute_ssh_command('df -h')
    update.message.reply_text(result[:4000])
    logger.info("Response sent to user")


# 4.5 Оперативная память
def get_free(update: Update, context):
    logger.info("Command: /get_free")
    result = execute_ssh_command('free -h')
    update.message.reply_text(result)
    logger.info("Response sent to user")


# 4.6 Производительность
def get_mpstat(update: Update, context):
    logger.info("Command: /get_mpstat")
    result = execute_ssh_command('mpstat 2>/dev/null')
    update.message.reply_text(result[:4000])
    logger.info("Response sent to user")


# 4.7 Работающие пользователи
def get_w(update: Update, context):
    logger.info("Command: /get_w")
    result = execute_ssh_command('w')
    update.message.reply_text(result[:4000])
    logger.info("Response sent to user")


# 4.8 Последние входы
def get_auths(update: Update, context):
    logger.info("Command: /get_auths")
    result = execute_ssh_command('last -n 10 2>/dev/null')
    update.message.reply_text(result[:4000])
    logger.info("Response sent to user")


# 4.9 Критические события
def get_critical(update: Update, context):
    logger.info("Command: /get_critical")
    result = execute_ssh_command('journalctl -p crit -n 5 --no-pager 2>/dev/null')
    update.message.reply_text(result[:4000])
    logger.info("Response sent to user")


# 4.10 Запущенные процессы
def get_ps(update: Update, context):
    logger.info("Command: /get_ps")
    result = execute_ssh_command('ps aux | head -20')
    update.message.reply_text(result[:4000])
    logger.info("Response sent to user")


# 4.11 Используемые порты
def get_ss(update: Update, context):
    logger.info("Command: /get_ss")
    result = execute_ssh_command('ss -tuln')
    update.message.reply_text(result[:4000])
    logger.info("Response sent to user")


# 4.12 Установленные пакеты
def get_apt_list_command(update: Update, context):
    logger.info("Command: /get_apt_list - waiting for user input")
    update.message.reply_text('Введите название пакета для поиска или "all" для вывода всех пакетов:')
    return 'get_apt_list'


def get_apt_list(update: Update, context):
    user_input = update.message.text.strip()
    logger.info(f"Searching for package: '{user_input}'")

    if user_input.lower() == 'all':
        result = execute_ssh_command('apt list --installed 2>/dev/null')
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


# 4.13 Запущенные сервисы
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
        },
        fallbacks=[]
    )

    conv_handler_phone = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', find_phone_number_command)],
        states={
            'find_phone_number': [MessageHandler(Filters.text & ~Filters.command, find_phone_number)],
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