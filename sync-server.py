import socket
import threading
import requests
from bs4 import BeautifulSoup
import json
import time

class MultithreadedParserServer:
    def __init__(self):
        self.base_url = "https://dental-first.ru/catalog"
        self.lock = threading.Lock()
    
    def parse_page(self, page_num):
        """Парсинг одной страницы (синхронно)"""
        try:
            if page_num == 0:
                url = self.base_url
            else:
                url = f"{self.base_url}?PAGEN_1={page_num}#nav_start"
            
            # Загружаем страницу
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем карточки товаров
            items = soup.select(".set-card.block")
            page_products = []
            
            for card in items:
                # Название товара
                name_tag = card.select_one("a.di_b.c_b")
                name = name_tag.get_text(strip=True) if name_tag else "NONAME"
                
                # Цена товара
                price_tag = card.select_one(".set-card__price")
                if price_tag:
                    price_text = price_tag.get_text(strip=True)
                    price_text = price_text.replace(" ", "").replace("₽", "").replace(",", ".")
                    try:
                        price = float(price_text)
                    except:
                        price = 0
                else:
                    price = 0
                
                page_products.append({
                    'name': name,
                    'price': price,
                    'page': page_num
                })
            
            return page_products
            
        except Exception as e:
            print(f"Error parsing page {page_num}: {e}")
            return []
    
    def parse_pages_threaded(self, pages):
        """Многопоточный парсинг страниц"""
        start_time = time.time()
        all_products = []
        total_price = 0
        
        # Создаем потоки для каждой страницы
        threads = []
        results = {}
        
        def worker(page_num, result_dict):
            result_dict[page_num] = self.parse_page(page_num)
        
        for page in pages:
            thread = threading.Thread(target=worker, args=(page, results))
            thread.start()
            threads.append(thread)
        
        # Ждем завершения всех потоков
        for thread in threads:
            thread.join()
        
        # Собираем результаты
        for page_products in results.values():
            all_products.extend(page_products)
            total_price += sum(p['price'] for p in page_products)
        
        execution_time = time.time() - start_time
        
        return {
            'products_count': len(all_products),
            'total_price': total_price,
            'execution_time': execution_time,
            'products': all_products[:10]  # Первые 10 товаров
        }
    
    def handle_client(self, client_socket):
        """Обработка клиента"""
        try:
            # Получаем запрос
            data = client_socket.recv(4096).decode().strip()
            
            # Парсим JSON запрос
            try:
                request_data = json.loads(data)
                pages = request_data.get('pages', [0])
                max_products = request_data.get('max_products', 10)
            except:
                pages = [0]
                max_products = 10
            
            # Выполняем парсинг
            result = self.parse_pages_threaded(pages)
            
            # Ограничиваем количество товаров
            if 'products' in result:
                result['products'] = result['products'][:max_products]
            
            # Отправляем ответ
            response = json.dumps(result, ensure_ascii=False)
            client_socket.send(response.encode())
            
        except Exception as e:
            error_response = json.dumps({'error': str(e)})
            client_socket.send(error_response.encode())
        finally:
            client_socket.close()
    
    def run_server(self, host='127.0.0.1', port=8889):
        """Запуск сервера"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((host, port))
        server.listen(5)
        
        print(f"Multithreaded parsing server started on {host}:{port}")
        
        while True:
            client_socket, addr = server.accept()
            print(f"Connection from {addr}")
            
            # Создаем поток для обработки клиента
            client_thread = threading.Thread(
                target=self.handle_client,
                args=(client_socket,)
            )
            client_thread.start()

def main():
    parser_server = MultithreadedParserServer()
    parser_server.run_server()

if __name__ == "__main__":
    main()
