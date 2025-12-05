# Многопоточнный сервер
import socket
import threading
import time
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

class MultiServer:
    def __init__(self, host='localhost', port=8080, max_workers=10):
        self.host = host
        self.port = port
        self.max_workers = max_workers
        self.products_file = 'products_multi.txt'
        self.total_price = 0.0
        self.lock = threading.Lock()


# Функция, которая парсит страницу товара, возвращает название товара и цену
    def parse_product_page(self, url):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Название товара 
            name_tag = soup.find('h1')
            product_name = name_tag.text.strip() if name_tag else 'Не распознано'
            
            # Цена 
            price_tag = soup.find('span', class_='price') or soup.find('b', class_='price')
            price_text = price_tag.text.strip() if price_tag else '0'
        
            price = float(''.join(filter(str.isdigit, price_text)) or 0)
            
            return product_name, price
        except Exception as e:
            print(f"Ошибка при парсинге {url}: {e}")
            return None, 0.0

# Функция, которая обрабатываем сам запрос
    def handle_client(self, client_socket):
        request = client_socket.recv(1024).decode('utf-8')
        if not request:
            client_socket.close()
            return
        
        # Извлекаем путь из HTTP-запроса
        path = request.split()[1] if len(request.split()) > 1 else '/'
        
        if path.startswith('/catalog/'):
            full_url = f'https://dental-first.ru{path}'
            product_name, price = self.parse_product_page(full_url)
            
            if product_name:
                with self.lock:
                    with open(self.products_file, 'a', encoding='utf-8') as f:
                        f.write(f'{product_name} - {price} руб.\n')
                    self.total_price += price
                
                response = f'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n'
                response += f'<html><body><h1>Товар: {product_name}</h1><p>Цена: {price} руб.</p></body></html>'
            else:
                response = 'HTTP/1.1 404 Not Found\r\n\r\nТовар не найден'
        else:
            response = 'HTTP/1.1 400 Bad Request\r\n\r\nНекорректный запрос'
        
        client_socket.send(response.encode('utf-8'))
        client_socket.close()

# Запуск сервера
    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.host, self.port))
        server.listen(5)
        print(f'Многопоточный сервер запущен на {self.host}:{self.port}')
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while True:
                client_socket, addr = server.accept()
                executor.submit(self.handle_client, client_socket)

if __name__ == '__main__':
    server = MultiServer(max_workers=20)
    server.start()
