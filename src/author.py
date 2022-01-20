from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, KeyboardButton, InlineKeyboardButton
import requests
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import calmap
import asyncio
from crud import recreate_database
from models import User, Book
import asyncpg
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from crud import async_session
import sys
from config import config
import os
import random

bot = Bot(token=config['telegram']['token'])
dp = Dispatcher(bot)

async def brodcast(mes):
    try:
        async with async_session() as s:
            async with s.begin():
                # print(1)
                q = select(User)
                for user in users:
                    await bot.send_message(mes, parse_mode=types.ParseMode.HTML)
    except Exception as e:
        print(e)


async def gen_list(chat_id, t):
    mes = ''
    try:
        async with async_session() as s:
            async with s.begin():
                # print(1)
                q = select(User).where(User.chat_id == chat_id).options(selectinload(t))
                res = await s.execute(q)
                # print()
                user = res.scalars().first()
                books = getattr(user, t)
                if user:


                    for i in range(len(books)):
                        mes += f'{i}) {books[i].title} - {books[i].author_fio}\n'
                else: 
                    mes = 'Вы не зарегистрированы'                  
    except Exception as e:
        print(e)

    return mes

async def gen_reply_list(chat_id, t):
    keyboard = InlineKeyboardMarkup()
    try:
        async with async_session() as s:
            async with s.begin():
                q = select(User).where(User.chat_id == chat_id).options(selectinload(t))
                res = await s.execute(q)
                user = res.scalars().first()
                books = getattr(user, t)
                if user:
                    for i in range(len(books)):
                        button = InlineKeyboardButton(f'{books[i].title}', callback_data=f"rm_{t}_{books[i].id}")
                        keyboard.add(button)                  
    except Exception as e:
        print(e)

    return keyboard

async def periodic(sleep_for):
    while True:
        await asyncio.sleep(sleep_for)
        try:
            async with async_session() as s:
                async with s.begin():
                    q = select(Book).options(selectinload('*'))
                    res = await s.execute(q)
                    books = res.scalars().all()
                    for book in books:
                        ses = requests.session()
                        ses.headers['Authorization'] = 'Bearer guest'   
                        r = ses.get(f'https://api.author.today/v1/work/{book.book_id}/details')
                        info = r.json()
                        chapters = [ch for ch in info['chapters'] if not ch['isDraft']]
                        chapters_count = len(chapters)
                        discount = info['discount'] if info['discount'] else .0
                        if not book.status and chapters_count - book.chapter_count == 1:
                            for user in book.subs_users:
                                keyboard = InlineKeyboardMarkup()
                                button = InlineKeyboardButton(chapters[-1]['title'], url=f'https://author.today/reader/{book.book_id}/{chapters[-1]["id"]}')
                                keyboard.add(button)
                                await bot.send_message(user.chat_id, f"{book.author_fio} обновил произведение {book.title}! Добавлена часть - {chapters[-1]['title']}", reply_markup=keyboard)
                            book.chapter_count = chapters_count
                        if not book.status and info['isFinished']:
                            for user in book.subs_end_users:
                                await bot.send_message(user.chat_id, f"Книга {book.title} завершена! Можно читать)")
                            book.status = info['isFinished']
                        if discount > book.discount:
                            for user in book.subs_users_disc:
                                await bot.send_message(user.chat_id, f"{book.author_fio} сделал скидку на произведение {book.title} в {discount} процентов")
                            book.discount = discount

                        if discount < book.discount:
                            for user in book.subs_users_disc:
                                await bot.send_message(user.chat_id, f"{book.author_fio} убрал скидку с произведения {book.title}")
                            book.discount = discount

        except Exception as e:
            print(e)

@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    try:
        async with async_session() as s:
            async with s.begin():
                s.add(User(chat_id = message.from_user.id))
    except Exception as e:
        print(e)
        await message.reply("Вы уже зарегистрированы)")
        return            
    
    await message.answer("Привет! Я бот для получения уведомлений с сайта author.today")
    await message.answer('Поддержать бота можно по <a href="https://sobe.ru/na/podderzhanie_bota_authortoday">ссылке</a>', parse_mode=types.ParseMode.HTML)

async def process_init_command():
    await recreate_database()
    print("Initializing database completed")

@dp.callback_query_handler(text="remove_watch")
async def process_remove_watch_callback(call: types.CallbackQuery):
    keyboard = await gen_reply_list(call.from_user.id, 'watch_books')
    await call.message.edit_reply_markup(keyboard)

@dp.callback_query_handler(text="remove_watch_end")
async def process_remove_watch_callback(call: types.CallbackQuery):
    keyboard = await gen_reply_list(call.from_user.id, 'watch_end_books')
    await call.message.edit_reply_markup(keyboard)

@dp.callback_query_handler(text="remove_watch_disc")
async def process_remove_watch_callback(call: types.CallbackQuery):
    keyboard = await gen_reply_list(call.from_user.id, 'watch_disc_books')
    await call.message.edit_reply_markup(keyboard)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('rm_watch_books_'))
async def process_remove_watch_callback(call: types.CallbackQuery):
    book_id = int(call.data[call.data.index("books_") + 6:])
    try:
        async with async_session() as s:
            async with s.begin():
                q = select(User).where(User.chat_id == call.from_user.id).options(selectinload('watch_books'))
                res = await s.execute(q)
                user = res.scalars().first()
                books = user.watch_books
                for book in books:
                    if book.id == book_id:
                        user.watch_books.remove(book)
    except Exception as e:
        print(e)

    mes = await gen_list(call.from_user.id, 'watch_books')
    if mes != '':
        keyboard = await gen_reply_list(call.from_user.id, 'watch_books')
        await call.message.edit_text(mes, reply_markup=keyboard)
    else:
        await call.message.edit_text("Вы не следите ни за одной книгой")

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('rm_watch_end_books_'))
async def process_remove_watch_end_callback(call: types.CallbackQuery):
    book_id = int(call.data[call.data.index("books_") + 6:])
    try:
        async with async_session() as s:
            async with s.begin():
                q = select(User).where(User.chat_id == call.from_user.id).options(selectinload('watch_end_books'))
                res = await s.execute(q)
                user = res.scalars().first()
                books = user.watch_end_books
                for book in books:
                    if book.id == book_id:
                        user.watch_end_books.remove(book)
    except Exception as e:
        print(e)

    mes = await gen_list(call.from_user.id, 'watch_end_books')
    if mes != '':
        keyboard = await gen_reply_list(call.from_user.id, 'watch_end_books')
        await call.message.edit_text(mes, reply_markup=keyboard)
    else:
        await call.message.edit_text("Вы не ждете окончания ни одной книги")

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('rm_watch_disc_books_'))
async def process_remove_watch_end_callback(call: types.CallbackQuery):
    book_id = int(call.data[call.data.index("books_") + 6:])
    try:
        async with async_session() as s:
            async with s.begin():
                q = select(User).where(User.chat_id == call.from_user.id).options(selectinload('watch_disc_books'))
                res = await s.execute(q)
                user = res.scalars().first()
                books = user.watch_disc_books
                for book in books:
                    if book.id == book_id:
                        user.watch_disc_books.remove(book)
    except Exception as e:
        print(e)

    mes = await gen_list(call.from_user.id, 'watch_disc_books')
    if mes != '':
        keyboard = await gen_reply_list(call.from_user.id, 'watch_disc_books')
        await call.message.edit_text(mes, reply_markup=keyboard)
    else:
        await call.message.edit_text("Вы не следите за ценой ни одной книги")

@dp.message_handler(commands=['list_watch'])
async def process_list_watch_command(message: types.Message):
    mes = await gen_list(message.from_user.id, 'watch_books')
    
    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton("Удалить книгу из списка", callback_data="remove_watch")
    keyboard.add(button)
        
    if mes != '':
        await message.reply(mes, reply_markup=keyboard)
    else:
        await message.reply("Вы не следите ни за одной книгой")

@dp.message_handler(commands=['list_watch_end'])
async def process_list_watch_end_command(message: types.Message):
    mes = await gen_list(message.from_user.id, 'watch_end_books')

    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton("Удалить книгу из списка", callback_data="remove_watch_end")
    keyboard.add(button)
    
    if mes != '':
        await message.reply(mes, reply_markup=keyboard)
    else:
        await message.reply("Вы не ждете окончания ни одной книги")

@dp.message_handler(commands=['list_watch_disc'])
async def process_list_watch_end_command(message: types.Message):
    mes = await gen_list(message.from_user.id, 'watch_disc_books')

    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton("Удалить книгу из списка", callback_data="remove_watch_disc")
    keyboard.add(button)
    
    if mes != '':
        await message.reply(mes, reply_markup=keyboard)
    else:
        await message.reply("Вы не следите за ценой ни одной книги")

@dp.message_handler(commands=['help'])
async def process_help_command(message: types.Message):
    await message.reply("""Здравствуйте! Я бот уведомлений для сайта author.today!
Поддерживаемые команды уведомлений:
/watch <url книги> - после исполнения этой команды Вам будут приходить уведомления, когда автор обновит книгу. (Пример /watch https://author.today/work/144417)
/watch_end <url книги> - после исполнения этой команды, Вам придет уведомление, когда книга будет завершена. (Пример /watch_end https://author.today/work/144417)
/list_watch - список книг, за которыми Вы следите
/list_watch_end - список книг, окончания которых Вы ждете
Также я умею строить графики регулярности выкладки глав в книге/серии
Поддерживаемые команды графиков:
/graphic <url книги> - после исполнения этой команды Вам будет отправлен график выхода глав в данной книге.
(Пример /graphic https://author.today/work/144417)
/graphic_ser <url книги> - после исполнения этой команды Вам будет отправлен график выхода глав в серии книг, в которую входит данная книга.
(Пример /graphic_ser https://author.today/work/144417)""")
    await message.answer('Поддержать бота можно по <a href="https://sobe.ru/na/podderzhanie_bota_authortoday">ссылке</a>', parse_mode=types.ParseMode.HTML)

@dp.message_handler(commands=['watch'])
async def process_watch_command(message: types.Message):
    book_url = message.text.split(' ')[1]
    book_id = int(book_url[book_url.index('work/') + 5:])
    s = requests.session()
    s.headers['Authorization'] = 'Bearer guest'   
    r = s.get(f'https://api.author.today/v1/work/{book_id}/details')
    info = r.json()
    if info['isFinished']:
        await message.reply("Книга уже закончена!")
        return
    else:
        chapters_count = len([ch for ch in info['chapters'] if not ch['isDraft']])
        discount = info['discount'] if info['discount'] else .0
        try:
            async with async_session() as s:
                async with s.begin():
                    q = select(User).where(User.chat_id == message.from_user.id)
                    res = await s.execute(q)
                    user = res.scalars().first()        
                    q = select(Book).where(Book.book_id == book_id).options(selectinload(Book.subs_users))
                    res = await s.execute(q)
                    book = res.scalars().first()
                    if not book:
                        book = Book(book_id = book_id, status=info['isFinished'], title=info['title'], author_fio=info['authorFIO'], chapter_count=chapters_count, discount=discount)            
                    
                    if not user in book.subs_users:
                        book.subs_users.append(user)
                        await s.merge(book)
                        await s.commit()
                        await message.reply(f"Теперь вам придет уведомление, когда книга {info['title']} будет обновлена!")
                    else:
                        await message.reply("Вы уже следите за этой книгой")

        except Exception as e:
            print(e)

@dp.message_handler(commands=['watch_end'])
async def process_watch_end_command(message: types.Message):
    book_url = message.text.split(' ')[1]
    book_id = int(book_url[book_url.index('work/') + 5:])
    s = requests.session()
    s.headers['Authorization'] = 'Bearer guest'   
    r = s.get(f'https://api.author.today/v1/work/{book_id}/details')
    info = r.json()

    if info['isFinished']:
        await message.reply("Книга уже закончена!")
        return
    else:
        chapters_count = len([ch for ch in info['chapters'] if not ch['isDraft']])
        discount = info['discount'] if info['discount'] else .0
        try:
            async with async_session() as s:
                async with s.begin():
                    q = select(User).where(User.chat_id == message.from_user.id)
                    res = await s.execute(q)
                    user = res.scalars().first()        
                    # print(user)
                    # print(book_id)
                    q = select(Book).where(Book.book_id == book_id).options(selectinload(Book.subs_end_users))
                    res = await s.execute(q)
                    book = res.scalars().first()
                    # print(book)
                    # print(dir(books))
                    if not book:
                        book = Book(book_id = book_id, status=info['isFinished'], title=info['title'], author_fio=info['authorFIO'], chapter_count=chapters_count, discount=discount)            
                    
                    if not user in book.subs_end_users:
                        book.subs_end_users.append(user)
                        await s.merge(book)
                        await s.commit()
                        await message.reply(f"Теперь вам придет уведомление, когда книга {info['title']} будет закончена!")
                    else:
                        await message.reply("Вы уже следите за этой книгой")

        except Exception as e:
            print(e)

@dp.message_handler(commands=['watch_disc'])
async def process_watch_disc_command(message: types.Message):
    book_url = message.text.split(' ')[1]
    book_id = int(book_url[book_url.index('work/') + 5:])
    s = requests.session()
    s.headers['Authorization'] = 'Bearer guest'   
    r = s.get(f'https://api.author.today/v1/work/{book_id}/details')
    info = r.json()
    print('hit')
    chapters_count = len([ch for ch in info['chapters'] if not ch['isDraft']])
    discount = info['discount'] if info['discount'] else .0
    try:
        async with async_session() as s:
            async with s.begin():
                q = select(User).where(User.chat_id == message.from_user.id)
                res = await s.execute(q)
                user = res.scalars().first()        
                q = select(Book).where(Book.book_id == book_id).options(selectinload(Book.subs_users_disc))
                res = await s.execute(q)
                book = res.scalars().first()
                if not book:
                    book = Book(book_id = book_id, status=info['isFinished'], title=info['title'], author_fio=info['authorFIO'], chapter_count=chapters_count, discount=discount)            
                    
                if not user in book.subs_users_disc:
                    book.subs_users_disc.append(user)
                    await s.merge(book)
                    await s.commit()
                    await message.reply(f"Теперь вам придет уведомление, когда на книге {info['title']} изментся скидка скидку!")
                else:
                    await message.reply("Вы уже следите за этой книгой")

    except Exception as e:
        print(e)
        
@dp.message_handler(commands=['graphic'])
async def get_graphic(message: types.Message):
    book_url = message.text.split(' ')[1]
    # print(book_url)
    book_id = int(book_url[book_url.index('work/') + 5:])
    s = requests.session()
    s.headers['Authorization'] = 'Bearer guest'   
    r = s.get(f'https://api.author.today/v1/work/{book_id}/details')
    info = r.json()
    chapters = info['chapters']

    date_time = np.array([])
    activity = np.array([])

    for chapter in chapters:
        if not chapter["isDraft"]:
            d = datetime.strptime(chapter["publishTime"], "%Y-%m-%dT%H:%M:%S.%fZ")
            date_time = np.append(date_time, d)
            activity = np.append(activity, chapter["textLength"])

    df = pd.DataFrame()
    df["date_time"] = date_time
    df["activity"] = activity

    df = df.set_index('date_time')

    plt.figure(figsize=(20,10))
    calmap.yearplot(df['activity'], cmap='YlGn', fillcolor='lightgrey',daylabels='MTWTFSS',dayticks=True,
                linewidth=2)

    rand = random.randint(0, 65536)
    plt.savefig(f'/tmp/graphic_{rand}.png')
    await bot.send_photo(chat_id = message.from_user.id, photo=open(f'/tmp/graphic_{rand}.png', 'rb'))
    os.remove(f'/tmp/graphic_{rand}.png')

@dp.message_handler(commands=['graphic_ser'])
async def get_graphic_ser(message: types.Message):
    book_url = message.text.split(' ')[1]
    # print(book_url)
    book_id = int(book_url[book_url.index('work/') + 5:])

    s = requests.session()
    s.headers['Authorization'] = 'Bearer guest'   
    r = s.get(f'https://api.author.today/v1/work/{book_id}/details')
    info = r.json()
    chapters = []

    for bid in info['seriesWorkIds']:
        r = s.get(f'https://api.author.today/v1/work/{bid}/details')
        i = r.json()
        chapters += i["chapters"]

    date_time = np.array([])
    activity = np.array([])

    for chapter in chapters:
        if not chapter["isDraft"]:
            try:
                d = datetime.strptime(chapter["publishTime"], "%Y-%m-%dT%H:%M:%S.%fZ")
            except Exception:
                d = datetime.strptime(chapter["publishTime"], "%Y-%m-%dT%H:%M:%SZ")

            # print(d)
            date_time = np.append(date_time, d)
            activity = np.append(activity, chapter["textLength"])

    # print(activity)
    # print(date_time)
    df = pd.DataFrame()
    df["date_time"] = date_time
    df["activity"] = activity

    df = df.set_index('date_time')

    plt.figure(figsize=(20,10))
    calmap.calendarplot(df['activity'], cmap='YlGn', fillcolor='lightgrey',daylabels='MTWTFSS',dayticks=True,
                linewidth=2)

    rand = random.randint(0, 65536)
    plt.savefig(f'/tmp/graphic_ser_{rand}.png')
    await bot.send_photo(chat_id = message.from_user.id, photo=open(f'/tmp/graphic_ser_{rand}.png', 'rb'))
    os.remove(f'/tmp/graphic_ser_{rand}.png')

if __name__ == '__main__':

    loop = asyncio.get_event_loop()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'init' and config['db']['initialized'] == "False":
            coroutine = process_init_command()
            loop.run_until_complete(coroutine)
            config['db']['initialized'] = "True"
            with open('author_bot.ini', 'w') as configfile:
                config.write(configfile)
            exit()

        if sys.argv[1] == 'broadcast':
            with open(sys.argv[2], 'r') as f:
                coroutine = broadcast(f.read())
            loop.run_until_complete(coroutine)
            exit()

    loop.create_task(periodic(10))
    executor.start_polling(dp, loop=loop)