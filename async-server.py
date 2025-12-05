# Асинхронный сервер

import asyncio
import aiohttp
import aiofiles
from aiohttp import web
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class AsyncServer:
    def __init__(self, host='localhost', port=8081):
        self.host = host
        self.port = port
        self.products_file = 'products_async.txt'
        self.total_price = 0.0
        self.lock = asyncio.Lock()

#Функция для асинхронного парсинга страницы
    async def parse_product_page(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        return None, 0.0
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'lxml')

                    name_tag = soup.find('h1')
                    product_name = name_tag.text.strip() if name_tag else 'Не распознано'
 
                    price_tag = soup.find('span', class_='price') or soup.find('b', class_='price')
                    price_text = price_tag.text.strip() if price_tag else '0'
                    price = float(''.join(filter(str.isdigit, price_text)) or 0)
                    
                    return product_name, price        
        except Exception as e:
            print(f"Ошибка при парсинге {url}: {e}")
            return None, 0.0

    async def handle_request(self, request):
        path = request.path
        
        if path.startswith('/catalog/'):
            full_url = f'https://dental-first.ru{path}'
            product_name, price = await self.parse_product_page(full_url)
            
            if product_name:
                async with self.lock:
                    async with aiofiles.open(self.products_file, 'a', encoding='utf-8') as f:
                        await f.write(f'{product_name} - {price} руб.\n')
                    self.total_price += price
                
                return web.Response(
                    text=f'<html><body><h1>Товар: {product_name}</h1><p>Цена: {price} руб.</p></body></html>',
                    content_type='text/html'
                )
            else:
                return web.Response(text='Товар не найден', status=404)
        else:
            return web.Response(text='Некорректный запрос', status=400)

#Запуск асинхронного сервера
    async def start_server(self):
        app = web.Application()
        app.router.add_get('/{tail:.*}', self.handle_request)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        
        print(f'Асинхронный сервер запущен на {self.host}:{self.port}')
        await site.start()
        
        await asyncio.Event().wait()

    def run(self):
        asyncio.run(self.start_server())

if __name__ == '__main__':
    server = AsyncServer()
    server.run()