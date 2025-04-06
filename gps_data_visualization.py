# БЛОК 1: Подключение нужных библиотек
import sys  # Для завершения программы
import os  # Для работы с файлами и папками
from datetime import datetime, timedelta  # Для работы с датами и временем
from IPython.display import display  # Для показа карты в Jupyter
import logging  # Для записи логов (сообщений о работе)

# Установка simplekml, если её нет
try:
    import simplekml  # Для сохранения карты в KML
except ImportError:
    print("simplekml не найдена. Устанавливаем...")
    import subprocess
    subprocess.check_call(["pip", "install", "simplekml"])
    import simplekml

# Установка folium, если её нет
try:
    import folium  # Для создания 2D-карты
except ImportError:
    print("folium не найдена. Устанавливаем...")
    import subprocess
    subprocess.check_call(["pip", "install", "folium"])
    import folium

from folium.plugins import MarkerCluster  # Для группировки точек на карте

# БЛОК 2: Настройка программы
# Устанавливаем формат сообщений логов
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Задаём окончания для файлов
FILTERED_FILE_SUFFIX = "_filtered.data"  # Для сохранённых данных
KML_FILE_EXTENSION = ".kml"  # Для карты в KML
MAP_FILE_EXTENSION = ".html"  # Для карты в HTML

# БЛОК 3: Функции для ввода данных
# Выбор файла с нужным окончанием (.log или .data)
def select_file(file_extension):
    logging.info(f"Спрашиваем файл с окончанием '{file_extension}'.")
    files = [f for f in os.listdir('.') if f.endswith(file_extension)]  # Список файлов в папке
    if not files:
        print(f"Нет файлов с окончанием '{file_extension}' в этой папке.")
        manual_path = input(f"Введите путь к файлу '{file_extension}' или Enter для пропуска (или '/' для выхода): ").strip()
        if manual_path == '/':
            raise SystemExit("Выход из программы по запросу пользователя.")  # Выход по "/"
        logging.info(f"Введен путь: '{manual_path}'." if manual_path else "Путь не введен.")
        return manual_path if manual_path else None  # Возвращаем путь или ничего
    print(f"Файлы с окончанием {file_extension}:")
    for i, filename in enumerate(files):
        print(f"{i + 1}. {filename}")  # Показываем файлы с номерами
    while True:
        choice = input(f"Выберите номер файла {file_extension} или введите путь (или '/' для выхода): ").strip()
        if choice == '/':
            raise SystemExit("Выход из программы по запросу пользователя.")  # Выход по "/"
        logging.info(f"Выбор: '{choice}'.")
        if choice.isdigit():  # Если ввели номер
            index = int(choice) - 1
            if 0 <= index < len(files):
                logging.info(f"Выбран файл: '{files[index]}'.")
                return files[index]  # Возвращаем выбранный файл
            else:
                print("Неверный номер. Попробуйте еще раз.")
                logging.warning("Неверный номер файла.")
        elif choice:  # Если ввели путь
            if os.path.exists(choice):
                logging.info(f"Выбран файл по пути: '{choice}'.")
                return choice  # Возвращаем путь
            else:
                print("Путь не найден. Попробуйте еще раз.")
                logging.warning("Путь не найден.")
        else:
            logging.info("Файл не выбран.")
            return None  # Ничего не выбрано

# Запрос действий (что делать с данными)
def ask_actions():
    while True:
        print("\nВыберите действия (введите номера через запятую или пробел):")
        print("1. Показать все найденные точки")
        print("2. Сохранить отобранные данные в файл data")
        print("3. Сохранить карту как KML")
        print("4. Сохранить карту как HTML")
        print("5. Выбрать всё (1-4)")
        choices_str = input("Введите номера (или '/' для выхода): ").strip()
        if choices_str == '/':
            raise SystemExit("Выход из программы по запросу пользователя.")  # Выход по "/"
        choices = choices_str.replace(',', ' ').split()  # Разделяем ввод
        if all(choice in ['1', '2', '3', '4', '5'] for choice in choices):
            return choices  # Возвращаем список действий
        print("Неверный ввод. Пожалуйста, введите номера от 1 до 5.")

# Показ выбранных действий
def display_actions(actions):
    action_list = {
        '1': "Показать все найденные точки",
        '2': "Сохранить отобранные данные в файл data",
        '3': "Сохранить карту как KML",
        '4': "Сохранить карту как HTML",
        '5': "Выбрать всё (1-4)"
    }
    print("\nТекущие выбранные действия:")
    if '5' in actions:
        print("  - Выбрано всё: " + ", ".join([action_list[a] for a in ['1', '2', '3', '4']]))
    else:
        for action in actions:
            print(f"  - {action_list[action]}")

# БЛОК 4: Функции для вопросов после обработки
# Запрос новых данных
def ask_new_data(filtered_data_points, filtered_lines, m, min_freq, max_freq, min_power, actions):
    while True:
        answer = input("Есть ли новые данные для обработки? (да/нет, или '/' для выхода): ").strip().lower()
        if answer == '/':
            print("Сохраняем по текущему выбору перед выходом...")
            perform_save(filtered_data_points, filtered_lines, m, min_freq, max_freq, min_power, actions)
            raise SystemExit("Выход из программы после сохранения.")  # Выход с сохранением
        if answer in ['да', 'нет']:
            return answer == 'да'  # Да — продолжаем, нет — завершаем
        print("Пожалуйста, введите 'да' или 'нет'.")

# Подтверждение действий
def ask_keep_actions(current_actions, filtered_data_points, filtered_lines, m, min_freq, max_freq, min_power):
    display_actions(current_actions)
    while True:
        answer = input("Оставить так или изменить? (да/нет, или '/' для выхода): ").strip().lower()
        if answer == '/':
            print("Сохраняем по текущему выбору перед выходом...")
            perform_save(filtered_data_points, filtered_lines, m, min_freq, max_freq, min_power, current_actions)
            raise SystemExit("Выход из программы после сохранения.")  # Выход с сохранением
        if answer in ['да', 'нет']:
            return answer == 'да'  # Да — оставляем, нет — меняем
        print("Пожалуйста, введите 'да' или 'нет'.")

# Запрос новых фильтров
def ask_new_filters(filtered_data_points, filtered_lines, m, min_freq, max_freq, min_power, actions):
    while True:
        answer = input("Хотите задать новые параметры фильтрации? (да/нет, или '/' для выхода): ").strip().lower()
        if answer == '/':
            print("Сохраняем по текущему выбору перед выходом...")
            perform_save(filtered_data_points, filtered_lines, m, min_freq, max_freq, min_power, actions)
            raise SystemExit("Выход из программы после сохранения.")  # Выход с сохранением
        if answer in ['да', 'нет']:
            return answer == 'да'  # Да — новые фильтры, нет — дальше
        print("Пожалуйста, введите 'да' или 'нет'.")

# БЛОК 5: Обработка данных и создание карты
def log_to_kml_v1(log_file, kml_output_base, data_file, min_frequency, max_frequency, min_power_db, actions):
    logging.info("Начало работы с данными.")
    print("Начало работы с данными...")
    if not os.path.exists(log_file):  # Проверка файла логов
        logging.error(f"Файл журнала '{log_file}' не найден.")
        print(f"Ошибка: Файл журнала '{log_file}' не найден.")
        return None, None, None
    gps_coords_with_altitude = []  # Список координат
    time_stamps = []  # Список времени
    logging.info("Чтение точек GPS из файла журнала...")
    print("Чтение точек GPS из файла журнала...")
    with open(log_file, 'r') as file:
        for line in file:
            if not line.startswith("GPS"):  # Только строки с GPS
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 15:
                continue
            try:
                status = int(parts[3])
                if status < 3:  # Пропускаем плохие данные
                    continue
                latitude = float(parts[8])
                longitude = float(parts[9])
                altitude = float(parts[10])
                time_us = int(parts[1])
                base_dt = datetime(2025, 1, 28)  # Базовая дата
                ts = base_dt + timedelta(seconds=time_us / 1_000_000)
                gps_coords_with_altitude.append((latitude, longitude, altitude))
                time_stamps.append(ts)
            except (ValueError, IndexError):
                logging.warning(f"Ошибка в строке GPS: '{line.strip()}'")
                continue
    if not gps_coords_with_altitude:
        logging.warning("Нет данных GPS для карты.")
        print("Нет данных GPS для карты.")
        return None, None, None
    logging.info(f"Прочитано {len(gps_coords_with_altitude)} точек GPS.")
    filtered_data_points = []  # Отобранные точки
    matches = 0  # Счётчик совпадений
    filtered_lines = []  # Отобранные строки
    first_gps_time = time_stamps[0] if time_stamps else None
    logging.info("Обработка файла данных и отбор...")
    print("Обработка файла данных и отбор...")
    if os.path.isfile(data_file):  # Проверка файла данных
        with open(data_file, 'r') as df:
            data_lines = df.readlines()
            first_valid_index = None
            first_valid_time = None
            logging.info("Поиск первого правильного времени в файле данных...")
            print("Поиск первого правильного времени в файле данных...")
            for index, line in enumerate(data_lines, start=1):
                values = line.strip().split(':')
                if len(values) < 4:
                    logging.warning(f"Строка {index} в файле данных неправильная: '{line.strip()}'")
                    continue
                try:
                    t_data = float(values[0])
                    if t_data > 0:
                        first_valid_index = index - 1
                        first_valid_time = t_data
                        break
                except (ValueError, IndexError):
                    logging.warning(f"Ошибка в строке {index} файла данных: '{line.strip()}'")
                    continue
            if first_valid_index is None:
                logging.error("Нет правильного времени в файле данных.")
                print("Нет правильного времени в файле данных.")
                return None, None, None
            logging.info("Отбор данных...")
            print("Отбор данных...")
            for index, line in enumerate(data_lines[first_valid_index:], start=first_valid_index + 1):
                values = line.strip().split(':')
                if len(values) < 4:
                    logging.warning(f"Строка {index} в файле данных неправильная: '{line.strip()}'")
                    continue
                try:
                    t_data = float(values[0])
                    freq_min = int(values[1])
                    freq_max = int(values[2])
                    power_values = list(map(float, values[3].split()))
                    valid_powers = [p for p in power_values if p > min_power_db]
                    if not valid_powers:
                        continue
                    if first_gps_time:
                        relative_time = t_data - first_valid_time
                        measurement_time = first_gps_time + timedelta(seconds=relative_time)
                        gps_times_seconds = [(ts - first_gps_time).total_seconds() for ts in time_stamps]
                        target_sec = (measurement_time - first_gps_time).total_seconds()
                        closest_idx = min(range(len(gps_times_seconds)), key=lambda i: abs(gps_times_seconds[i] - target_sec))
                        time_diff = abs(gps_times_seconds[closest_idx] - target_sec)
                        if time_diff <= 1.0 and min_frequency <= freq_min <= max_frequency and min_frequency <= freq_max <= max_frequency:
                            filtered_data_points.append({
                                "coords": gps_coords_with_altitude[closest_idx],
                                "timestamp": measurement_time,
                                "freq_min": freq_min,
                                "freq_max": freq_max,
                                "powers": valid_powers
                            })
                            matches += 1
                            formatted_powers = " ".join(f"{p:.1f}" for p in valid_powers)
                            formatted_freq_min = f"{freq_min:04d}"
                            formatted_freq_max = f"{freq_max:04d}"
                            filtered_lines.append(
                                f"{relative_time:.3f}:{formatted_freq_min}:{formatted_freq_max}: {formatted_powers}\n"
                            )
                except (ValueError, IndexError):
                    logging.warning(f"Ошибка в строке данных {index}: '{line.strip()}'")
                    continue
    else:
        logging.error(f"Файл данных '{data_file}' не найден.")
        print(f"Файл данных '{data_file}' не найден.")
        return None, None, None
    logging.info("Создание карты 2D...")
    print("Создание карты 2D...")
    map_center = filtered_data_points[0]['coords'][:2] if filtered_data_points else [0, 0]
    m = folium.Map(location=map_center, zoom_start=12, tiles=None)  # Пустая карта
    folium.TileLayer(  # Добавляем слой карты
        'https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}{r}.png',
        attr='© <a href="https://stadiamaps.com/">Stadia Maps</a> © <a href="https://openmaptiles.org/">OpenMapTiles</a> © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        name='Stadia Maps Alidade Smooth',
        control=True
    ).add_to(m)
    logging.info("Добавление точек на карту...")
    print("Добавление точек на карту...")
    marker_cluster = MarkerCluster().add_to(m)  # Группировка точек
    for i, data in enumerate(filtered_data_points):
        lat, lon, alt = data['coords']
        tooltip_text = f"Точка {i + 1}<br>"
        tooltip_text += f"Параметры отбора:<br>Мин. частота: {min_frequency} МГц<br>Макс. частота: {max_frequency} МГц<br>Мин. мощность: {min_power_db} дБ<br><br>"
        tooltip_text += f"Координаты: Широта {lat:.6f}, Долгота {lon:.6f}, Высота {alt:.2f} м<br>"
        tooltip_text += f"Время: {data['timestamp'].strftime('%H:%M:%S')}<br>"
        tooltip_text += f"Частоты: {data['freq_min']} - {data['freq_max']} МГц<br>"
        tooltip_text += f"Мощности: {', '.join(map(str, data['powers']))} дБ"
        folium.Marker((lat, lon), tooltip=tooltip_text).add_to(marker_cluster)
    logging.info("Показ карты...")
    print("Показ карты...")
    display(m)  # Показываем карту в Jupyter
    logging.info("Работа с данными завершена.")
    print("Работа с данными завершена.")
    logging.info(f"Найдено {matches} точек по параметрам отбора.")
    print(f"Найдено {matches} точек по параметрам отбора.")
    if filtered_lines:
        logging.info(f"Отобрано {len(filtered_lines)} строк данных.")
        print(f"Отобранные данные (первые 10 строк):")
        for i, line in enumerate(filtered_lines[:10]):
            print(line.strip())
            if i == 9:
                break
        if len(filtered_lines) > 10:
            print(f"... и еще {len(filtered_lines) - 10} строк.")
    return filtered_data_points, filtered_lines, m  # Возвращаем данные и карту

# БЛОК 6: Сохранение результатов
def perform_save(filtered_data_points, filtered_lines, m, min_frequency, max_frequency, min_power_db, actions):
    base_filename = f"filtered_data_minfreq-{min_frequency}_maxfreq-{max_frequency}_minpower-{min_power_db:.2f}"
    all_actions = ['1', '2', '3', '4']
    actions_to_perform = all_actions if '5' in actions else [a for a in actions if a in all_actions]
    for action in actions_to_perform:
        if action == '1':  # Показать точки
            print("\n--- Все найденные точки ---")
            for i, data in enumerate(filtered_data_points):
                print(f"Точка {i + 1}")
                print(f"Координаты: Широта {data['coords'][0]:.6f}, Долгота {data['coords'][1]:.6f}, Высота {data['coords'][2]:.2f} м")
                print(f"Время: {data['timestamp'].strftime('%H:%M:%S')}")
                print(f"Частоты: {data['freq_min']} - {data['freq_max']} МГц")
                print(f"Мощности: {', '.join(map(str, data['powers']))} дБ")
                print("-" * 20)
        elif action == '2':  # Сохранить данные
            filtered_data_filename = base_filename + FILTERED_FILE_SUFFIX
            print(f"Сохранение отобранных данных в файл: {filtered_data_filename}")
            try:
                with open(filtered_data_filename, 'w') as f:
                    f.writelines(filtered_lines)
                logging.info(f"Отобранные данные сохранены в файл: {filtered_data_filename}")
                print(f"Отобранные данные сохранены.")
            except Exception as e:
                logging.error(f"Ошибка при сохранении данных: {e}")
                print(f"Ошибка при сохранении данных: {e}")
        elif action == '3':  # Сохранить KML
            kml = simplekml.Kml()
            for i, data in enumerate(filtered_data_points):
                lat, lon, alt = data['coords']
                pnt = kml.newpoint(name=f"Точка {i + 1}", coords=[(lon, lat, alt)])
                pnt.description = f"Время: {data['timestamp'].strftime('%H:%M:%S')}\nЧастоты: {data['freq_min']}-{data['freq_max']} МГц\nМощности: {', '.join(map(str, data['powers']))} дБ\nВысота: {alt:.2f} м"
            kml_filename = base_filename + KML_FILE_EXTENSION
            try:
                kml.save(kml_filename)
                logging.info(f"Карта сохранена как KML в файл: {kml_filename}")
                print(f"Карта сохранена как KML.")
            except Exception as e:
                logging.error(f"Ошибка при сохранении KML: {e}")
                print(f"Ошибка при сохранении KML: {e}")
        elif action == '4':  # Сохранить HTML
            map_filename = f"map_{base_filename}{MAP_FILE_EXTENSION}"
            print(f"Сохранение карты как HTML в файл: {map_filename}")
            try:
                m.save(map_filename)
                logging.info(f"Карта сохранена как HTML в файл: {map_filename}")
                print(f"Карта сохранена как HTML.")
            except Exception as e:
                logging.error(f"Ошибка при сохранении HTML: {e}")
                print(f"Ошибка при сохранении HTML: {e}")

# БЛОК 7: Главная функция для запуска
def get_file_paths_and_filter_params_v1():
    print("Вариант 1:")
    actions = ask_actions()  # Запрашиваем действия
    display_actions(actions)
    
    while True:
        log_file_path = select_file('.log')  # Выбираем файл логов
        if not log_file_path:
            print("Путь к файлу журнала не указан. Программа завершена.")
            break
        data_file_path = select_file('.data')  # Выбираем файл данных
        if not data_file_path:
            print("Путь к файлу данных не указан. Программа завершена.")
            break
        
        while True:
            # Ввод фильтров
            while True:
                min_freq_input = input("Введите минимальную частоту (МГц) (или '/' для выхода): ").strip()
                if min_freq_input == '/':
                    raise SystemExit("Выход из программы по запросу пользователя.")
                try:
                    min_freq = int(min_freq_input)
                    break
                except ValueError:
                    print("Ошибка: Введите целое число для минимальной частоты.")
            while True:
                max_freq_input = input("Введите максимальную частоту (МГц) (или '/' для выхода): ").strip()
                if max_freq_input == '/':
                    raise SystemExit("Выход из программы по запросу пользователя.")
                try:
                    max_freq = int(max_freq_input)
                    if min_freq > max_freq:
                        print("Ошибка: Максимальная частота должна быть не меньше минимальной.")
                    else:
                        break
                except ValueError:
                    print("Ошибка: Введите целое число для максимальной частоты.")
            while True:
                min_power_input = input("Введите минимальную мощность (дБ) (или '/' для выхода): ").strip()
                if min_power_input == '/':
                    raise SystemExit("Выход из программы по запросу пользователя.")
                try:
                    min_power = float(min_power_input)
                    break
                except ValueError:
                    print("Ошибка: Введите число для минимальной мощности.")
            
            print(f"\nВыбранные параметры:")
            print(f"  - Файл журнала GPS: {log_file_path}")
            print(f"  - Файл данных: {data_file_path}")
            print(f"  - Минимальная частота: {min_freq} МГц")
            print(f"  - Максимальная частота: {max_freq} МГц")
            print(f"  - Минимальная мощность: {min_power} дБ")
            display_actions(actions)
            
            logging.info(f"Параметры отбора: мин. частота={min_freq} МГц, макс. частота={max_freq} МГц, мин. мощность={min_power:.2f} дБ")
            filtered_data_points, filtered_lines, m = log_to_kml_v1(log_file_path, None, data_file_path, min_freq, max_freq, min_power, actions)
            
            if filtered_data_points is None:
                print("Обработка данных не удалась. Программа завершена.")
                return
            
            # Спрашиваем про действия
            if ask_keep_actions(actions, filtered_data_points, filtered_lines, m, min_freq, max_freq, min_power):
                perform_save(filtered_data_points, filtered_lines, m, min_freq, max_freq, min_power, actions)
            else:
                actions = ask_actions()
                display_actions(actions)
                perform_save(filtered_data_points, filtered_lines, m, min_freq, max_freq, min_power, actions)
            
            # Спрашиваем про новые фильтры
            if not ask_new_filters(filtered_data_points, filtered_lines, m, min_freq, max_freq, min_power, actions):
                break
        
        # Спрашиваем про новые данные
        if ask_new_data(filtered_data_points, filtered_lines, m, min_freq, max_freq, min_power, actions):
            continue
        else:
            if ask_keep_actions(actions, filtered_data_points, filtered_lines, m, min_freq, max_freq, min_power):
                print(f"\nИтоговые параметры:")
                print(f"  - Файл журнала GPS: {log_file_path}")
                print(f"  - Файл данных: {data_file_path}")
                print(f"  - Минимальная частота: {min_freq} МГц")
                print(f"  - Максимальная частота: {max_freq} МГц")
                print(f"  - Минимальная мощность: {min_power} дБ")
                display_actions(actions)
                print("Программа завершена с текущими параметрами сохранения.")
                break
            else:
                actions = ask_actions()
                print(f"\nИтоговые параметры:")
                print(f"  - Файл журнала GPS: {log_file_path}")
                print(f"  - Файл данных: {data_file_path}")
                print(f"  - Минимальная частота: {min_freq} МГц")
                print(f"  - Максимальная частота: {max_freq} МГц")
                print(f"  - Минимальная мощность: {min_power} дБ")
                display_actions(actions)
                print("Программа завершена с новым выбором действий.")
                break

# БЛОК 8: Запуск программы
if __name__ == "__main__":
    logging.info("Старт программы.")
    try:
        get_file_paths_and_filter_params_v1()  # Запускаем главную функцию
    except SystemExit as e:
        print(e)  # Показываем сообщение при выходе
    logging.info("Программа завершена.")
