import socket
import asyncio
import time
import json
import os
from datetime import datetime

def read_server_ports():
    """Читает порты серверов из файлов"""
    ports = {'async': 8880, 'sync': 8881}
    
    try:
        if os.path.exists('async_server_port.txt'):
            with open('async_server_port.txt', 'r') as f:
                ports['async'] = int(f.read().strip())
    except:
        pass
    
    try:
        if os.path.exists('sync_server_port.txt'):
            with open('sync_server_port.txt', 'r') as f:
                ports['sync'] = int(f.read().strip())
    except:
        pass
    
    return ports

def test_sync_server(pages=[0, 1, 2, 3]):
    """Тестирование многопоточного сервера"""
    start_time = time.time()
    
    try:
        ports = read_server_ports()
        port = ports['sync']
        
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(30)
        client.connect(('127.0.0.1', port))
        
        request = json.dumps({
            'pages': pages,
            'max_products': 20
        })
        client.send(request.encode())
        
        response_data = b""
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            response_data += chunk
        
        client.close()
        
        result = json.loads(response_data.decode())
        elapsed = time.time() - start_time
        
        return {
            'success': 'error' not in result,
            'time': elapsed,
            'result': result,
            'error': result.get('error') if 'error' in result else None
        }
        
    except Exception as e:
        return {
            'success': False,
            'time': time.time() - start_time,
            'error': str(e)
        }

async def test_async_server(pages=[0, 1, 2, 3]):
    """Тестирование асинхронного сервера"""
    start_time = time.time()
    
    try:
        ports = read_server_ports()
        port = ports['async']
        
        reader, writer = await asyncio.open_connection('127.0.0.1', port)
        
        request = json.dumps({
            'pages': pages,
            'max_products': 20
        })
        writer.write(request.encode())
        await writer.drain()
        
        response_data = b""
        while True:
            chunk = await reader.read(4096)
            if not chunk:
                break
            response_data += chunk
        
        writer.close()
        await writer.wait_closed()
        
        result = json.loads(response_data.decode())
        elapsed = time.time() - start_time
        
        return {
            'success': 'error' not in result,
            'time': elapsed,
            'result': result,
            'error': result.get('error') if 'error' in result else None
        }
        
    except Exception as e:
        return {
            'success': False,
            'time': time.time() - start_time,
            'error': str(e)
        }

def save_results_to_file(async_results, sync_results, filename="test_results.txt"):
    """Сохранение результатов в один файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        f.write("="*60 + "\n")
        f.write(f"РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ - {timestamp}\n")
        f.write("="*60 + "\n\n")
        
        # Результаты асинхронного сервера
        f.write("1. АСИНХРОННЫЙ СЕРВЕР:\n")
        f.write("-"*40 + "\n")
        
        if async_results['success']:
            f.write(f"Статус: УСПЕШНО ✓\n")
            f.write(f"Время выполнения: {async_results['time']:.3f} секунд\n")
            f.write(f"Найдено товаров: {async_results['result'].get('products_count', 0)}\n")
            f.write(f"Суммарная стоимость: {async_results['result'].get('total_price', 0):.2f} руб.\n")
            
            f.write("\nТОВАРЫ (первые 10):\n")
            products = async_results['result'].get('products', [])[:10]
            for i, product in enumerate(products, 1):
                f.write(f"{i:2}. {product.get('name', 'N/A')[:50]:50} - {product.get('price', 0):8.2f} руб.\n")
        else:
            f.write(f"Статус: ОШИБКА ✗\n")
            f.write(f"Ошибка: {async_results.get('error', 'Unknown error')}\n")
        
        f.write("\n" + "="*60 + "\n\n")
        
        # Результаты синхронного сервера
        f.write("2. МНОГОПОТОЧНЫЙ СЕРВЕР:\n")
        f.write("-"*40 + "\n")
        
        if sync_results['success']:
            f.write(f"Статус: УСПЕШНО ✓\n")
            f.write(f"Время выполнения: {sync_results['time']:.3f} секунд\n")
            f.write(f"Найдено товаров: {sync_results['result'].get('products_count', 0)}\n")
            f.write(f"Суммарная стоимость: {sync_results['result'].get('total_price', 0):.2f} руб.\n")
            
            f.write("\nТОВАРЫ (первые 10):\n")
            products = sync_results['result'].get('products', [])[:10]
            for i, product in enumerate(products, 1):
                f.write(f"{i:2}. {product.get('name', 'N/A')[:50]:50} - {product.get('price', 0):8.2f} руб.\n")
        else:
            f.write(f"Статус: ОШИБКА ✗\n")
            f.write(f"Ошибка: {sync_results.get('error', 'Unknown error')}\n")
        
        f.write("\n" + "="*60 + "\n\n")
        
        # Сравнение
        f.write("3. СРАВНЕНИЕ ПРОИЗВОДИТЕЛЬНОСТИ:\n")
        f.write("="*60 + "\n")
        
        if async_results['success'] and sync_results['success']:
            async_time = async_results['time']
            sync_time = sync_results['time']
            
            f.write(f"Время асинхронного сервера: {async_time:.3f} сек\n")
            f.write(f"Время многопоточного сервера: {sync_time:.3f} сек\n")
            f.write("\n")
            
            if async_time < sync_time:
                diff = sync_time - async_time
                ratio = sync_time / async_time
                f.write(f"Асинхронный сервер быстрее на {diff:.3f} секунд\n")
                f.write(f"Это в {ratio:.2f} раз быстрее!\n")
            else:
                diff = async_time - sync_time
                ratio = async_time / sync_time
                f.write(f"Многопоточный сервер быстрее на {diff:.3f} секунд\n")
                f.write(f"Это в {ratio:.2f} раз быстрее!\n")
            
            # Сравнение количества товаров
            async_count = async_results['result'].get('products_count', 0)
            sync_count = sync_results['result'].get('products_count', 0)
            
            f.write(f"\nКоличество товаров:\n")
            f.write(f"  Асинхронный: {async_count}\n")
            f.write(f"  Многопоточный: {sync_count}\n")
            
            if async_count != sync_count:
                f.write(f"\n⚠ Внимание: серверы нашли разное количество товаров!\n")
                f.write(f"  Разница: {abs(async_count - sync_count)} товаров\n")
            
            # Сравнение стоимости
            async_price = async_results['result'].get('total_price', 0)
            sync_price = sync_results['result'].get('total_price', 0)
            
            f.write(f"\nСуммарная стоимость:\n")
            f.write(f"  Асинхронный: {async_price:.2f} руб.\n")
            f.write(f"  Многопоточный: {sync_price:.2f} руб.\n")
            
            if abs(async_price - sync_price) > 0.01:
                f.write(f"\n⚠ Внимание: разница в суммарной стоимости!\n")
                f.write(f"  Разница: {abs(async_price - sync_price):.2f} руб.\n")
            
        else:
            f.write("Не удалось сравнить - есть ошибки в работе серверов\n")
        
        f.write("\n" + "="*60 + "\n")
        f.write("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО\n")
        f.write("="*60 + "\n")

async def main():
    print("="*60)
    print("ТЕСТИРОВАНИЕ СЕРВЕРОВ ПАРСИНГА")
    print("="*60)
    
    # Страницы для парсинга
    pages_to_parse = [0, 1, 2, 3]
    
    print(f"\nБудет парситься {len(pages_to_parse)} страниц:")
    for i, page in enumerate(pages_to_parse):
        if page == 0:
            print(f"  Страница {i+1}: https://dental-first.ru/catalog")
        else:
            print(f"  Страница {i+1}: https://dental-first.ru/catalog?PAGEN_1={page}#nav_start")
    
    print("\n" + "="*60)
    
    # Тестируем многопоточный сервер
    print("\n1. Тестирую многопоточный сервер...")
    sync_result = test_sync_server(pages_to_parse)
    
    if sync_result['success']:
        print(f"   ✓ Успешно! Время: {sync_result['time']:.3f} сек")
        print(f"   ✓ Товаров: {sync_result['result'].get('products_count', 0)}")
        print(f"   ✓ Сумма: {sync_result['result'].get('total_price', 0):.2f} руб.")
    else:
        print(f"   ✗ Ошибка: {sync_result.get('error', 'Unknown error')}")
    
    # Тестируем асинхронный сервер
    print("\n2. Тестирую асинхронный сервер...")
    async_result = await test_async_server(pages_to_parse)
    
    if async_result['success']:
        print(f"   ✓ Успешно! Время: {async_result['time']:.3f} сек")
        print(f"   ✓ Товаров: {async_result['result'].get('products_count', 0)}")
        print(f"   ✓ Сумма: {async_result['result'].get('total_price', 0):.2f} руб.")
    else:
        print(f"   ✗ Ошибка: {async_result.get('error', 'Unknown error')}")
    
    print("\n" + "="*60)
    print("СРАВНЕНИЕ РЕЗУЛЬТАТОВ:")
    print("="*60)
    
    if sync_result['success'] and async_result['success']:
        async_time = async_result['time']
        sync_time = sync_result['time']
        
        if async_time < sync_time:
            diff = sync_time - async_time
            ratio = sync_time / async_time
            print(f"\n✓ Асинхронный сервер быстрее на {diff:.3f} сек")
            print(f"✓ Это в {ratio:.2f} раз быстрее!")
        else:
            diff = async_time - sync_time
            ratio = async_time / sync_time
            print(f"\n✓ Многопоточный сервер быстрее на {diff:.3f} сек")
            print(f"✓ Это в {ratio:.2f} раз быстрее!")
    
    # Сохраняем результаты в файл
    save_results_to_file(async_result, sync_result)
    print(f"\n✓ Результаты сохранены в 'test_results.txt'")
    
    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
    print("="*60)

if __name__ == "__main__":
    # Для Windows
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
