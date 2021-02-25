import configparser
import os
import zipfile

import colorama
import requests
from colorama import Back, Fore, Style

colorama.init(autoreset=True)
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "settings.ini"))

server_name = config["Loader"]["server_name"]
print(f'{Fore.GREEN} Имя сервиса: {server_name}')
if config["Loader"]["install"] == 'True':
    print(f'{Fore.GREEN} Начата установка')
    license = config["Loader"]["license_code"]
    print(f'{Fore.GREEN} Код лицензии: {license}')
    response = requests.get(
        config["Loader"]["URLs.path_to_verify_license_code"],
        params={
            'code': license
        }
    )

    if response.json()['ok'] is True:
        file_response = requests.get(
            config["Loader"]["URLs.path_to_download_code"]
        )
        print(f'{Fore.GREEN} Начато скачивание файлов')

        file_open = open(os.path.abspath("LT.zip"), 'wb')
        file_open.write(file_response.content)
        file_open.close()
        print(f'{Fore.GREEN} Завершено скачивание файлов')

        print(f'{Fore.GREEN} Распаковка архива')
        fantasy_zip = zipfile.ZipFile(os.path.abspath("LT.zip"))
        fantasy_zip.extractall(os.getcwd())
        fantasy_zip.close()
        print(f'{Fore.GREEN} Архив распакован')


        os.remove(os.path.abspath("LT.zip"))
        print(f'{Fore.GREEN} Архив удален')

        os.system(f'cd {os.getcwd()}')
        os.system('pip install -r requirements.txt')

        if config["Loader"]["updated"] == 'True':
            print(f'{Fore.GREEN} Обновлено!')
            print(f'{Fore.YELLOW} Перезапустите этот скрипт')
        else:
            print(f'{Fore.GREEN} Параметер install установлен на False')
            print(f'{Fore.YELLOW} Перезапустите этот скрипт')

        config.set('Loader', 'install', 'False')
        config.set('Loader', 'updated', 'False')
        with open(os.path.join(os.path.dirname(__file__), "settings.ini"), 'w') as configfile:
            config.write(configfile)
    else:
        print(f'{Fore.RED} Лицензия не правильная!')
else:
    response = requests.get(
        config["Loader"]["URLs.path_to_get_version"],
    )

    json = response.json()
    if json['version'] != config['Loader']['version']:
        print(f'{Fore.YELLOW} Есть обновление, перезапустите скрипт')
        config.set('Loader', 'install', 'True')
        config.set('Loader', 'updated', 'True')
        config.set('Loader', 'version', json['version'])
        with open(os.path.join(os.path.dirname(__file__), "settings.ini"), 'w') as configfile:
            config.write(configfile)
    else:
        os.system(f'cd {os.getcwd()}')
        os.system('python main.py')
