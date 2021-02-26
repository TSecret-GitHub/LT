# Import modules
import logging
import random
import os
import signal
import time

import colorama
from colorama import Fore, Style
import coloredlogs
import jwt
import requests
import telebot
from telebot import types
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from telethon import TelegramClient

import configparser

logger = logging.getLogger(__name__)
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "settings.ini"))
coloredlogs.install(level=config['Main']['log_level'], logger=logger)
logger.debug('(SET_UP) Импорты выпонены')

# Creating objects and init
colorama.init(autoreset=True)
logger.debug(f'(SET_UP) Созданы объекты и инициализация{Style.RESET_ALL}, текст имеет {Fore.GREEN}ц{Fore.RED}в{Fore.YELLOW}е{Fore.MAGENTA}т')

# Variables
private_key = config['Main']['keys.private_key']
bot = telebot.TeleBot(config['Main']['keys.token'])
private_key = serialization.load_pem_private_key(
    private_key.encode('utf-8'), password=b"w[WyCq8f){('TMJn", backend=default_backend(),
)
logger.debug('(SET_UP) Созданы начальные переменные')

def signal_handler(signal, frame):
    payload = {
        'bot_name': config["Loader"]["server_name"],
    }
    encoded = jwt.encode(payload, private_key, algorithm="RS256")

    response = requests.post(config['Main']['urls.path_to_disconect_bot'], data={
        'encoded_name': encoded
    })

    if response.json()['disconected'] is True:
        logger.info('Отключено от системы CYS')
        logger.info('Команда ctrl+C')
    else:
        logger.critical('(polling) Ошибка отключения от системы CYS!')
    exit()

signal.signal(signal.SIGINT, signal_handler)

# Handler for commands
# |---------------------------
# | /start - register        |
# | /balance - get balance   |
# | /bill - create bill      |
# | /transfer - create check |
# | /info - get ID           |
# | /get_bill - get bill     |
# | /UT - UnderTail          |
# |---------------------------

@bot.message_handler(commands=['start', 'balance', 'bill', 'transfer', 'info', 'get_bill', 'UT', 'search'])
def commands_handler(message):
    if message.text.lower() == '/start':
        name = bot.send_message(
            message.chat.id, 'Привет user, напиши свое имя -->'
        )
        bot.register_next_step_handler(name, next_step_name)

        logger.info(f'(command:start) Пользователь с ID {Fore.BLUE}{message.from_user.id}{Fore.GREEN} ввел команду {Fore.RED}/start')
    elif message.text.lower() == '/balance':
        payload = {
            'user_id': message.from_user.id
        }
        encoded = jwt.encode(payload, private_key, algorithm="RS256")

        logger.debug(f'(command:balance) payload: {Fore.MAGENTA}{payload}')
        logger.debug(f'(command:balance) encoded: {Fore.MAGENTA}{encoded}')

        resp = requests.post(config['Main']['urls.path_to_get_balance'], data={
            'token': encoded
        })

        logger.debug(f'(command:balance) response: {Fore.MAGENTA}{resp}')
        try:
            logger.debug(f'(command:balance) response JSON: {Fore.MAGENTA}{resp.json()}')
        except ValueError:
            logger.critical('(command:balance) Json don\'t working!', exc_info=True)

        balance = resp.json().get('balance', False)
        logger.info(f'(command:balance) Баланс: {Fore.MAGENTA}{balance}, ID - {Fore.MAGENTA}{message.from_user.id}')

        if resp.json()['error'] == 'Not registred':
            bot.send_message(
                message.chat.id, 'Вы не зарегистрированы, используйте команду /start'
            )
            logger.debug(
                f'(command:balance) Юзер не зарегестрирован - ID: {Fore.MAGENTA}{message.from_user.id}'
            )
        elif resp.json()['error'] == 'Banned':
            bot.send_message(message.chat.id, f'Вы заблокированы!')
            logger.debug(f'(command:balance) Юзер заблокирован - ID: {Fore.MAGENTA}{message.from_user.id}')
        else:
            bot.send_message(
                message.chat.id, f'Ваш баланс составляет {balance} Логиков'
            )
    elif message.text.lower() == '/search':
        keyboard = types.InlineKeyboardMarkup()
        callback_button = types.InlineKeyboardButton(text="Все пользователи", callback_data="all_users")
        callback_button1 = types.InlineKeyboardButton(text="Конкретный пользователь (Скоро...)", callback_data="curent_user")
        keyboard.add(callback_button)
        keyboard.add(callback_button1)

        bot.send_message(message.chat.id, 'Выбери режим поиска:', reply_markup=keyboard)
    elif message.text.lower() == '/transfer':
        id = bot.send_message(message.chat.id, 'Введите id для первода -->')
        bot.register_next_step_handler(id, next_step_id)

        logger.info(f'(command:transfer) Начало перевода - ID: {Fore.MAGENTA}{message.from_user.id}')
    elif message.text.lower() == '/info':
        bot.send_message(
            message.chat.id, f'Вот ваш ID: {message.from_user.id} \nОн используется для перевода и создания счетов =)'
        )
        logger.debug(
            f'{Fore.GREEN}/info - ID: {Fore.MAGENTA}{message.from_user.id}'
        )
    elif message.text.lower() == '/bill':
        bot.send_message(message.chat.id, f'Счет - насильно-согласованое отбирание логиков.')
        id = bot.send_message(message.chat.id, 'Введите ID получателя -->')

        bot.register_next_step_handler(id, next_step_bill_id)
        logger.info(f'(command:bill) Начало счета - ID: {Fore.MAGENTA}{message.from_user.id}')
    elif message.text.lower() == '/get_bill':
        proof = bot.send_message(message.chat.id, 'Отправьте proof -->')
        bot.register_next_step_handler(proof, next_step_get_bill_proof)
    elif message.text == '/UT':
        image = config['Main']['urls.path_to_ut_easter_egg']
        bot.send_photo(message.chat.id, image)
        time.sleep(3)
        bot.send_message(
            message.chat.id,
            config['Main']['message_ut_easter_egg'],
            parse_mode='Markdown'
        )

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == "all_users":
        response = requests.get(config['Main']['urls.path_to_get_users'])
        data = response.json()
        iter = 0

        for i in range(len(data)):
            data_for_message = data[str(iter)]
            username = data_for_message['username']
            name = data_for_message['name']
            balance = data_for_message['balance']
            banned = 'Да' if data_for_message['banned'] else 'Нет' 
            chat_id = data_for_message['chat_id']

            bot.send_message(call.message.chat.id, f'Username - {username} \nИмя - {name} \nБаланс - {balance} \nЗаблокирован? - {banned} \nID - {chat_id}')
            iter += 1
# Functions from bot.register_next_step_handler
def next_step_name(message):
    bot.send_message(message.chat.id, f'Привет {message.text}')
    bot.send_message(message.chat.id, f'Сейчас все будет готово...')
    logger.debug(f'(func:next_step_name) Ввод пользователя: {Fore.MAGENTA}{message.text}')

    payload = {
        'chat_id': message.chat.id,
        'user_id': message.from_user.id,
        'name': message.text,
        'username': message.from_user.username 
    }
    encoded = jwt.encode(payload, private_key, algorithm="RS256")

    logger.debug(f'(func:next_step_name) payload: {Fore.MAGENTA}{payload}')
    logger.debug(f'(func:next_step_name) encoded: {Fore.MAGENTA}{encoded}')

    resp = requests.post(config['Main']['urls.path_to_start'], data={
        'token': encoded
    })

    logger.debug(f'(func:next_step_name) response: {Fore.MAGENTA}{resp}')
    try:
        logger.debug(f'(func:next_step_name) response JSON: {Fore.MAGENTA}{resp.json()}')
    except ValueError:
        logger.error('(func:next_step_name) Json don\'t working!', exc_info=True)


    if resp.json()['created'] == 'ok':
        logger.debug(f'(func:next_step_name) Создан аккаунт - ID {Fore.MAGENTA}{message.from_user.id}')

        bot.send_message(message.chat.id, 'Все готово!')
        time.sleep(0.5)
        bot.send_message(message.chat.id, 'Теперь, тебе доступны такие команды:')
        bot.send_message(message.chat.id, '/bill - создать счет')
        time.sleep(0.5)
        bot.send_message(message.chat.id, '/transfer - перевод')
        time.sleep(0.5)
        bot.send_message(message.chat.id, '/balance - баланс')
        time.sleep(0.5)
        bot.send_message(message.chat.id, '/info - Инфо')
        time.sleep(0.5)
        bot.send_message(
            message.chat.id, '\nДа, не много... \nНо! Все еще это классно!'
        )
    elif resp.json()['error'] == 'Alredy exsists':
        bot.send_message(message.chat.id, 'Вы уже зарегистрированы!')
        logger.warning(f'(func:next_step_name) Уже зарегистрирован аккаунт - ID {Fore.MAGENTA}{message.from_user.id}')
    else:
        bot.send_message(message.chat.id, 'Произошла внутреняя ошибка... :(')
        logger.critical(f'(func:next_step_name) Внутреняя ошибка - Chat ID {Fore.MAGENTA}{message.chat.id}')


def next_step_id(message):
    logger.info(f'(func:next_step_id) Начало перевода к {Fore.MAGENTA}{message.text}{Fore.GREEN} - ID: {Fore.MAGENTA}{message.from_user.id}')

    to_user = message.text
    amount_message = bot.send_message(
        message.chat.id, 'Теперь введите количество:'
    )
    bot.register_next_step_handler(amount_message, next_step_amount, to_user)


def next_step_amount(message, to_user):
    amount = message.text
    try:
        int(amount)
    except:
        bot.send_message(message.chat.id, f'Нельзя поставить в количество не число!')
        logger.info(f'(func:next_step_amount) Не цифры - ID: {Fore.MAGENTA}{message.from_user.id} к {Fore.MAGENTA}{message.text} с количеством {Fore.MAGENTA}{amount}')
        return

    logger.info(f'(func:next_step_amount) Начало перевода к {Fore.MAGENTA}{to_user}{Fore.GREEN} с количеством {Fore.MAGENTA}{message.text}{Fore.GREEN} - ID: {Fore.MAGENTA}{message.from_user.id}')


    payload = {
        'user_id': message.from_user.id,
        'from_user': message.from_user.id,
        'to_user': to_user,
        'amount': amount,
    }
    encoded = jwt.encode(payload, private_key, algorithm="RS256")

    logger.debug(f'(func:next_step_amount) payload: {Fore.MAGENTA}{payload}')
    logger.debug(f'(func:next_step_amount) encoded: {Fore.MAGENTA}{encoded}')

    resp = requests.post(config['Main']['urls.path_to_transfer'], data={
        'token': encoded
    })

    logger.debug(f'(func:next_step_amount) response: {Fore.MAGENTA}{resp}')
    try:
        logger.debug(f'(func:next_step_amount) response JSON: {Fore.MAGENTA}{resp.json()}')
    except:
        logger.error(f'(func:next_step_amount) Json don\'t working!', exc_info=True)

    if resp.json()['error'] == 'Banned':
        bot.send_message(message.chat.id, f'Вы заблокированы!')
        logger.debug(f'(func:next_step_amount) Пользователь заблокирован: {Fore.MAGENTA}{message.from_user.id}')
    elif resp.json()['error'] == 'From user not found':
        bot.send_message(
            message.chat.id, f'Вы не зарегистрированы, используйте команду /start'
        )
        logger.debug(f'(func:next_step_amount) Пользователь не зарегестрирован: {Fore.MAGENTA}{message.from_user.id}')
    elif resp.json()['error'] == 'To user not found':
        bot.send_message(
            message.chat.id, f'Пользователя с ID {to_user} не существует...'
        )
        logger.info(f'(func:next_step_amount) Пользователь(получатель) не существует: from-ID {Fore.MAGENTA}{to_user}, ID {Fore.MAGENTA}{message.from_user.id}')
    elif resp.json()['error'] == 'To user banned':
        bot.send_message(
            message.chat.id, f'Пользователь с ID {to_user} заблокирован...'
        )
        logger.debug(f'(func:next_step_amount) Пользователь(получатель) заблокирован: from-ID {Fore.MAGENTA}{to_user}, ID {Fore.MAGENTA}{message.from_user.id}')
    elif resp.json()['error'] == 'The user does not call logics':
        bot.send_message(
            message.chat.id, f'У вас недостаточно средств что-бы перевести {amount} Логиков'
        )
        logger.debug(f'(func:next_step_amount) Пользователь не имеет необходимое количество средств: {Fore.MAGENTA}{message.from_user.id}')
    elif resp.json()['error'] == 'Amount less than zero':
        bot.send_message(
            message.chat.id, f'Сумма перевода не может быть меньше нуля!'
        )
        logger.debug(f'(func:next_step_amount) Игра со знаками: {Fore.MAGENTA}{message.from_user.id}')
    elif resp.json()['error'] == 'External error':
        bot.send_message(message.chat.id, f'Произошла внутреняя ошибка... :(')
        logger.critical(f'(func:next_step_amount) Внутреняя ошибка: {Fore.MAGENTA}{message.from_user.id}')
    else:
        bot.send_message(
            message.chat.id, f'Готово! \nПользователю с ID {to_user} переведено {amount} Логиков'
        )
        bot.send_message(
            to_user, f'Пользователь с ID {message.chat.id} перевел вам {amount} Логиков'
        )
        logger.info(f'(func:next_step_amount) Перевод успешен: From-ID - {Fore.MAGENTA}{to_user}, ID - {Fore.MAGENTA}{message.from_user.id}, Amount - {Fore.MAGENTA}{amount}')


def next_step_bill_id(message):
    logger.info(f'(func:next_step_bill_id) Начало перевода - ID: {Fore.MAGENTA}{message.from_user.id} к {Fore.MAGENTA}{message.text}')
    id = message.text
    from_id = message.chat.id
    amount = bot.send_message(
        message.chat.id, f'Теперь введите количество счета -->'
    )
    bot.register_next_step_handler(amount, next_step_bill_amount, id, from_id)


def next_step_bill_amount(message, id, from_id):
    amount = message.text
    try:
        int(amount)
    except:
        bot.send_message(message.chat.id, f'Нельзя поставить в количество не число!')
        logger.info(f'(func:next_step_bill_amount) Не цифры - ID: {Fore.MAGENTA}{message.from_user.id} к {Fore.MAGENTA}{message.text} с количеством {Fore.MAGENTA}{amount}')
        return

    to_random_code = str(random.randint(0, 9)) + str(random.randint(0, 9)) + str(random.randint(
        0, 9)) + str(random.randint(0, 9)) + str(random.randint(0, 9)) + str(random.randint(0, 9))

    bot.send_message(message.chat.id, f'Ожидаю подтверждения счета...')
    logger.info(f'(func:next_step_bill_amount) Начало перевода - ID: {Fore.MAGENTA}{message.from_user.id} к {Fore.MAGENTA}{message.text} с количеством {Fore.MAGENTA}{amount}')
    try:
        to_code = bot.send_message(int(
            id), f'Пользователь с ID {from_id} желает создать счет вам на сумму {amount} Логиков, введите код для подтверждения: {to_random_code}. Если вы не хотите создать счет введите: "Reject"')
        logger.debug(f'(func:next_step_bill_amount) Начало перевода - ID: {Fore.MAGENTA}{message.from_user.id} к {Fore.MAGENTA}{message.text} с количеством {Fore.MAGENTA}{amount}: Отправлено сообщение к to_user')
    except:
        bot.send_message(message.chat.id, f'Пользователь не существует!')
        logger.warning(f'(func:next_step_bill_amount) Начало перевода - ID: {Fore.MAGENTA}{message.from_user.id} к {Fore.MAGENTA}{message.text} с количеством {Fore.MAGENTA}{amount}: Отправлено сообщение к to_user, но пользователя не существует')
        return

    bot.register_next_step_handler(
        to_code, next_step_bill_confirm, id, from_id, amount, to_random_code
    )


def next_step_bill_confirm(message, id, from_id, amount, to_random_code):
    if message.text.lower() == 'reject' or message.text.lower() == '"reject"':
        logger.info(f'(func:next_step_bill_confirm) Начало перевода - ID: {Fore.MAGENTA}{message.from_user.id} к {Fore.MAGENTA}{message.text} с количеством {Fore.MAGENTA}{amount}: Отправлено сообщение к to_user, счет отменен')
        bot.send_message(int(id), 'Счет отменен...')
        bot.send_message(from_id, 'Пользователь отменил счет...')
    elif message.text == to_random_code:
        logger.info(f'(func:next_step_bill_confirm) Начало перевода - ID: {Fore.MAGENTA}{message.from_user.id} к {Fore.MAGENTA}{message.text} с количеством {Fore.MAGENTA}{amount}: Отправлено сообщение к to_user, счет подтвержден')
        bot.send_message(int(id), 'Счет подтвержден!')
        bot.send_message(from_id, 'Пользователь подтвердил счет...')

        bot.send_message(int(id), 'Создаю счет...')
        bot.send_message(from_id, 'Создаю счет...')

        payload = {
            'from_user': from_id,
            'to_user': id,
            'amount': amount,
            'code': to_random_code
        }
        encoded = jwt.encode(payload, private_key, algorithm="RS256")

        logger.debug(f'(func:next_step_bill_confirm) payload: {Fore.MAGENTA}{payload}')
        logger.debug(f'(func:next_step_bill_confirm) encoded: {Fore.MAGENTA}{encoded}')

        resp = requests.post(config['Main']['urls.path_to_create_bill'], data={
            'token': encoded
        })

        logger.debug(f'(func:next_step_bill_confirm) response: {Fore.MAGENTA}{resp}')
        try:
            logger.debug(f'(func:next_step_bill_confirm) response JSON: {Fore.MAGENTA}{resp.json()}')
        except:
            logger.error(f'(func:next_step_bill_confirm) Json don\'t working!', exc_info=True)

        if resp.json()['error'] == 'From user not found':
            bot.send_message(
                from_id, f'Вы не зарегистрированы, используйте команду /start')
            logger.debug(f'(func:next_step_bill_confirm) Пользователь не зарегистрирован: {Fore.MAGENTA}{from_id}')
        elif resp.json()['error'] == 'To user not found':
            bot.send_message(
                from_id, f'Пользователя с ID {to_user} не существует...')

            logger.debug(f'(func:next_step_bill_confirm) Пользователь(получатель) не существует: from-id {Fore.MAGENTA}{from_id}, to-id {Fore.MAGENTA}{id}')
        elif resp.json()['error'] == 'To user banned':
            bot.send_message(
                from_id, f'Пользователь с ID {to_user} заблокирован...')
            logger.debug(f'(func:next_step_bill_confirm) Пользователь(получатель) заблокирован: from-id {Fore.MAGENTA}{from_id}, to-id {Fore.MAGENTA}{id}')
        elif resp.json()['error'] == 'Banned':
            bot.send_message(from_id, f'Вы заблокированы!')
            logger.debug(f'(func:next_step_bill_confirm) Пользователь заблокирован: {Fore.MAGENTA}{from_id}')
        elif resp.json()['error'] == 'Amount less than zero':
            bot.send_message(
                from_id, f'Сумма счета не может быть меньше нуля!')
            logger.debug(f'(func:next_step_bill_confirm) Игра со знаками: {Fore.MAGENTA}{from_id}')
        else:
            proof = str(resp.json()['bill'])
            bot.send_message(
                from_id, f'Счет создан! \nЧто-бы исполнить платеж напишите команду /get_bill и введите это как proof:')
            bot.send_message(from_id, f'`{str(proof)}`', parse_mode='Markdown')
    else:
        bot.send_message(int(id), f'Код подтверждения не верный!')
        bot.send_message(int(id), f'Счет отменен, повторите снова...')
        bot.send_message(from_id, f'Пользователь неправильно ввел код...')


def next_step_get_bill_proof(message):
    payload = {
        'proof': message.text,
    }
    encoded = jwt.encode(payload, private_key, algorithm="RS256")

    resp = requests.post(config['Main']['urls.path_to_get_bill'], data={
        'token': encoded
    })

    if resp.json()['error'] == 'Changed proof':
        bot.send_message(message.chat.id, f'Неверный proof!')
    elif resp.json()['error'] == 'Expired proof':
        bot.send_message(message.chat.id, f'Недействительный proof!')
    elif resp.json()['error'] == 'Bill deactivate':
        bot.send_message(message.chat.id, f'Счет неактивен!')
    else:
        bot.send_message(message.chat.id, f'Счет выполнен!')


# Bot polling
while True:
    response = requests.get(config['Main']['urls.path_to_all_bots_in_cys_system'])
    if response.json()['CYS'] is True:
        payload = {
            'bot_name': config["Loader"]["server_name"],
        }
        encoded = jwt.encode(payload, private_key, algorithm="RS256")

        response = requests.post(config['Main']['urls.path_to_start_bot'], data={
            'encoded_name': encoded
        })

        if response.json()['started'] is True:
            while True:
                try:
                    logger.info('(polling) Polling работает')
                    bot.polling(none_stop=True)
                except SystemExit:
                    quit()
                except:
                    logger.critical(f'(polling) ОШИБКА! \nПопытка подключения...', exc_info=True)

                    logger.info(f'(polling) Переподключение через 3...')
                    time.sleep(1)
                    logger.info(f'(polling) Переподключение через 2...')
                    time.sleep(1)
                    logger.info(f'(polling) Переподключение через 1...')
                    time.sleep(1)

                    response = requests.post('https://tsecret-website.herokuapp.com/LT/working_bots/bot/disabled', data={
                        'encoded_name': encoded
                    })

                    if response.json()['disconected'] is True:
                        continue
                    else:
                        logger.critical('(polling) Ошибка отключения от системы CYS!')
                        continue
        else:
            logger.critical('(polling) Ошибка подключения к системе CYS!')
            continue
    else:
        # Use your own values from my.telegram.org
        api_id = 3293577
        api_hash = '7597e07d96b6dd58cea320e9fee7c0f9'

        test_message = None
        good_message = "Вот ваш ID: 1557297295 \nОн используется для перевода и создания счетов =)"

        # The first parameter is the .session file name (absolute paths allowed)
        client = TelegramClient('anon', api_id, api_hash)

        async def main():
            message = await client.send_message('transacrions_bot', '/info')
            messages = client.iter_messages('transacrions_bot', limit=1, max_id=message.id)
            async for x in messages:  # show the 10 messages
                test_message = x.text

            if test_message == good_message:
                logger.info('Бот работает')
            else:
                logger.warning('Бот не работает')
                payload = {
                    'bot': 'don\'t works'
                }
                encoded = jwt.encode(payload, private_key, algorithm="RS256")

                response = requests.post(config['Main']['urls.path_to_re-verify_bots'], data={
                    'encoded': encoded
                })

                if response.json()['bots'] == 're-verifired':
                    logger.info('Сообщение о перепроверке было принято')
                else:
                    logger.warning('Сообщение о перепроверке не было принято')

        with client:
            client.loop.run_until_complete(main())
        
        logger.info('(polling) Уже один бот работает, повтор через 10 секунд...')
        time.sleep(1)
        logger.info('(polling) Повтор через 9 секунд...')
        time.sleep(1)
        logger.info('(polling) Повтор через 8 секунд...')
        time.sleep(1)
        logger.info('(polling) Повтор через 7 секунд...')
        time.sleep(1)
        logger.info('(polling) Повтор через 6 секунд...')
        time.sleep(1)
        logger.info('(polling) Повтор через 5 секунд...')
        time.sleep(1)
        logger.info('(polling) Повтор через 4 секунд...')
        time.sleep(1)
        logger.info('(polling) Повтор через 3 секунд...')
        time.sleep(1)
        logger.info('(polling) Повтор через 2 секунд...')
        time.sleep(1)
        logger.info('(polling) Повтор через 1 секунд...')
        time.sleep(1)

        continue
