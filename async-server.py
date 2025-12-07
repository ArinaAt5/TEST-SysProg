import socket
import threading
import requests
from bs4 import BeautifulSoup
import json
import time
import re

class SyncParserServer:
    def __init__(self):
        self.base_url = "https://dental-first.ru/catalog"
        self.lock = threading.Lock()
    
    def find_free_port(self, start_port=8881):
        """Находит свободный порт"""
        port = start_port
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('127.0.0.1', port))
                sock.close()
                return port
            except OSError:
                port += 1
                if port > 8899:
                    raise Exception("Не удалось найти свободный порт")
    
    def parse_page(self, page_num):
        """Парсинг одной страницы"""
        try:
            if page_num == 0:
                url = self.base_url
            else:
                url = f"{self.base_url}?PAGEN_1={page_num}#nav_start"
            
            print(f"Парсинг страницы {page_num}: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            items = soup.select(".set-card.block")
            if not items:
                items = soup.select(".product-card")
            if not items:
                items = soup.select(".catalog-item")
            if not items:
                items = soup.find_all("div", class_=lambda x: x and any(word in str(x) for word in ['product', 'item', 'card']))
            
            print(f"  На странице {page_num} найдено элементов: {len(items)}")
            
            page_products = []
            
            for card in items:
                try:
                    name = "NONAME"
                    name_selectors = ["a.di_b.c_b", ".product-name", ".title", "h3", "h4"]
                    
                    for selector in name_selectors:
                        name_tag = card.select_one(selector)
                        if name_tag and name_tag.text.strip():
                            name = name_tag.text.strip()
                            break
                    
                    price = 0
                    price_selectors = [".set-card__price", ".price", ".product-price", ".cost"]
                    
                    for selector in price_selectors:
                        price_tag = card.select_one(selector)
                        if price_tag and price_tag.text.strip():
                            price_text = price_tag.text.strip()
                            numbers = re.findall(r'[\d\s]+', price_text)
                            if numbers:
                                price_text = numbers[0].replace(' ', '').replace(',', '.')
                                try:
                                    price = float(price_text)
                                except:
                                    price = 0
                            break
                    
                    page_products.append({
                        'name': name[:100],
                        'price': price,
                        'page': page_num
                    })
                    
                except Exception:
                    continue
            
            return page_products
            
        except Exception as e:
            print(f"Ошибка парсинга страницы {page_num}: {e}")
            return []
    
    def parse_pages_threaded(self, pages):
        """Многопоточный парсинг страниц"""
        start_time = time.time()
        
        threads = []
        results = {}
        
        def worker(page_num, result_dict):
            result_dict[page_num] = self.parse_page(page_num)
        
        for page in pages:
            thread = threading.Thread(target=worker, args=(page, results))
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join()
        
        all_products = []
        total_price = 0
        
        for page_products in results.values():
            all_products.extend(page_products)
            total_price += sum(p['price'] for p in page_products)
        
        unique_products = []
        seen_names = set()
        for product in all_products:
            if product['name'] not in seen_names:
                seen_names.add(product['name'])
                unique_products.append(product)
        
        execution_time = time.time() - start_time
        
        return {
            'products_count': len(unique_products),
            'total_price': total_price,
            'execution_time': execution_time,
            'products': unique_products[:20]
        }
    
    def handle_client(self, client_socket):
        """Обработка клиента"""
        try:
            data = client_socket.recv(4096).decode().strip()
            if not data:
                return
            
            try:
                request_data = json.loads(data)
                pages = request_data.get('pages', [0])
                max_products = request_data.get('max_products', 20)
            except:
                pages = [0]
                max_products = 20
            
            print(f"Получен запрос на парсинг страниц: {pages}")
            
            result = self.parse_pages_threaded(pages)
            
            if 'products' in result:
                result['products'] = result['products'][:max_products]
            
            response = json.dumps(result, ensure_ascii=False, indent=2)
            client_socket.send(response.encode())
            
        except Exception as e:
            error_response = json.dumps({'error': str(e)})
            client_socket.send(error_response.encode())
        finally:
            client_socket.close()
    
    def run_server(self):
        """Запуск сервера"""
        port = self.find_free_port(8881)
        
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('127.0.0.1', port))
        server.listen(5)
        
        print(f'='*60)
        print(f'Многопоточный сервер запущен на 127.0.0.1:{port}')
        print(f'Порт: {port}')
        print(f'Готов принимать запросы...')
        print(f'='*60)
        
        with open('sync_server_port.txt', 'w') as f:
            f.write(str(port))
        
        while True:
            try:
                client_socket, addr = server.accept()
                print(f"Подключение от {addr}")
                
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket,)
                )
                client_thread.start()
                
            except KeyboardInterrupt:
                print("\nСервер остановлен")
                break
            except Exception as e:
                print(f"Ошибка приема соединения: {e}")

def main():
    parser_server = SyncParserServer()
    parser_server.run_server()

if __name__ == "__main__":
    print("Запуск многопоточного сервера...")
    main()
