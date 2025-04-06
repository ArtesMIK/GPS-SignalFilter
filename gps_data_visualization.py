# Программа работает с файлами журнала GPS (.log) и файлами данных (.data).
# Она отбирает данные по параметрам частоты и мощности, которые задает пользователь,
# показывает отобранные точки GPS на карте 2D с помощью folium,
# и дает пользователю сохранить отобранные данные, карту в KML и HTML,
# а также повторить отбор с другими параметрами.

# Подключаем нужные библиотеки для работы программы.

try:
    import simplekml
except ImportError:
    # Если simplekml нет, пробуем установить через pip
    print("simplekml не найдена. Устанавливаем...")
    !pip install simplekml
    import simplekml

import random
import os  # Для работы с файловой системой
from datetime import datetime, timedelta  # Для работы с датой и временем
from IPython.display import display  # Для показа объектов в Jupyter Notebook

try:
    import folium
except ImportError:
    # Если folium нет, пробуем установить через pip
    print("folium не найдена. Устанавливаем...")
    !pip install folium
    import folium

from folium.plugins import MarkerCluster  # Для группировки маркеров на карте
import logging  # Для записи событий и ошибок

# --- Настройка записи событий ---

# Устанавливаем уровень записи для информации, предупреждений и ошибок.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Определение постоянных значений ---

# Задаем постоянные для частей имен файлов, чтобы было проще их использовать и менять.
FILTERED_FILE_SUFFIX = "_filtered.data"  # Часть имени для файлов с отобранными данными
KML_FILE_EXTENSION = ".kml"  # Окончание для файлов KML (для геоданных)
MAP_FILE_EXTENSION = ".html"  # Окончание для файлов HTML (для сохранения карты)

# --- Функция для выбора файла ---

def select_file(file_extension):
    """
    Спрашивает у пользователя файл из списка файлов с нужным окончанием
    в текущей папке или позволяет ввести путь самому.
    """
    logging.info(f"Спрашиваем файл с окончанием '{file_extension}'.")
    files = [f for f in os.listdir('.') if f.endswith(file_extension)]  # Список файлов с нужным окончанием

    # Если таких файлов нет, предлагаем ввести путь
    if not files:
        print(f"Нет файлов с окончанием '{file_extension}' в этой папке.")
        manual_path = input(f"Введите путь к файлу '{file_extension}' или Enter для пропуска: ").strip()
        logging.info(f"Введен путь: '{manual_path}'." if manual_path else "Путь не введен.")
        return manual_path if manual_path else None

    # Если файлы есть, показываем список
    print(f"Файлы с окончанием {file_extension}:")
    for i, filename in enumerate(files):
        print(f"{i + 1}. {filename}")

    # Спрашиваем выбор до тех пор, пока не получим правильный
    while True:
        choice = input(f"Выберите номер файла {file_extension} или введите путь: ").strip()
        logging.info(f"Выбор: '{choice}'.")

        # Если ввели номер
        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(files):
                logging.info(f"Выбран файл: '{files[index]}'.")
                return files[index]
            else:
                print("Неверный номер. Попробуйте еще раз.")
                logging.warning("Неверный номер файла.")
        # Если ввели путь
        elif choice:
            if os.path.exists(choice):
                logging.info(f"Выбран файл по пути: '{choice}'.")
                return choice
            else:
                print("Путь не найден. Попробуйте еще раз.")
                logging.warning("Путь не найден.")
        # Если ничего не ввели
        else:
            logging.info("Файл не выбран.")
            return None

# --- Главная функция для работы с логами и создания карты (Вариант 1) ---

def log_to_kml_v1(log_file, kml_output_base, data_file, min_frequency, max_frequency, min_power_db):
    """
    Обрабатывает файл журнала GPS и файл данных, отображает отобранные точки GPS на карте 2D с помощью folium (Вариант 1)
    с маркерами, собранными в группы, и деталями для каждой точки. Позволяет выбрать действия после работы.
    Возвращает список отобранных точек или сигнал для повторного отбора.

    Args:
        log_file (str): Путь к файлу журнала GPS.
        kml_output_base (str): Основа имени для файла KML (не используется здесь).
        data_file (str): Путь к файлу данных.
        min_frequency (int): Нижняя граница частоты для отбора (МГц).
        max_frequency (int): Верхняя граница частоты для отбора (МГц).
        min_power_db (float): Нижняя граница мощности для отбора (дБ).

    Returns:
        list: Список словарей с данными отобранных точек GPS или строка 'retry_filter' для повторного отбора.
    """
    logging.info("Начало работы с данными.")
    print("Начало работы с данными...")

    # Проверяем, есть ли файл журнала GPS
    if not os.path.exists(log_file):
        logging.error(f"Файл журнала '{log_file}' не найден.")
        print(f"Ошибка: Файл журнала '{log_file}' не найден.")
        return []

    gps_coords_with_altitude = []
    time_stamps = []

    logging.info("Чтение точек GPS из файла журнала...")
    print("Чтение точек GPS из файла журнала...")
    # Открываем файл журнала и читаем строки для получения точек GPS
    with open(log_file, 'r') as file:
        for line in file:
            # Берем строки, начинающиеся с "GPS"
            if not line.startswith("GPS"):
                continue
            # Разделяем строку по запятой и убираем пробелы
            parts = [p.strip() for p in line.split(',')]
            # Проверяем, хватает ли частей для нужных данных
            if len(parts) < 15:
                continue
            try:
                # Берем статус GPS, широту, долготу, высоту и время
                status = int(parts[3])
                # Пропускаем данные с плохим статусом (меньше 3)
                if status < 3:
                    continue
                latitude = float(parts[8])
                longitude = float(parts[9])
                altitude = float(parts[10])
                time_us = int(parts[1])
                # Переводим время из микросекунд в datetime
                base_dt = datetime(2025, 1, 28)
                ts = base_dt + timedelta(seconds=time_us / 1_000_000)
                # Сохраняем точку и время
                gps_coords_with_altitude.append((latitude, longitude, altitude))
                time_stamps.append(ts)
            except (ValueError, IndexError):
                logging.warning(f"Ошибка в строке GPS: '{line.strip()}'")
                continue

    # Если точек GPS нет, сообщаем и выходим
    if not gps_coords_with_altitude:
        logging.warning("Нет данных GPS для карты.")
        print("Нет данных GPS для карты.")
        return []

    logging.info(f"Прочитано {len(gps_coords_with_altitude)} точек GPS.")

    filtered_data_points = []
    matches = 0
    filtered_lines = []
    first_gps_time = time_stamps[0] if time_stamps else None

    logging.info("Обработка файла данных и отбор...")
    print("Обработка файла данных и отбор...")
    # Проверяем, есть ли файл данных
    if os.path.isfile(data_file):
        # Открываем файл данных и читаем строки
        with open(data_file, 'r') as df:
            data_lines = df.readlines()
            first_valid_index = None
            first_valid_time = None

            logging.info("Поиск первого правильного времени в файле данных...")
            print("Поиск первого правильного времени в файле данных...")
            # Ищем первую строку с временем больше нуля
            for index, line in enumerate(data_lines, start=1):
                values = line.strip().split(':')
                if len(values) < 4:
                    logging.warning(f"Строка {index} в файле данных неправильная: '{line.strip()}'")
                    print(f"Строка {index} в файле данных неправильная.")
                    continue
                try:
                    t_data = float(values[0])
                    if t_data > 0:
                        first_valid_index = index - 1
                        first_valid_time = t_data
                        break
                except (ValueError, IndexError):
                    logging.warning(f"Ошибка в строке {index} файла данных: '{line.strip()}'")
                    print(f"Ошибка в строке {index} файла данных.")
                    continue

            # Если нет правильного времени, выходим
            if first_valid_index is None:
                logging.error("Нет правильного времени в файле данных.")
                print("Нет правильного времени в файле данных.")
                return []

            logging.info("Отбор данных...")
            print("Отбор данных...")
            # Отбираем данные по частоте и мощности
            for index, line in enumerate(data_lines[first_valid_index:], start=first_valid_index + 1):
                values = line.strip().split(':')
                if len(values) < 4:
                    logging.warning(f"Строка {index} в файле данных неправильная: '{line.strip()}'")
                    print(f"Строка {index} в файле данных неправильная.")
                    continue
                try:
                    t_data = float(values[0])
                    freq_min = int(values[1])
                    freq_max = int(values[2])
                    power_values = list(map(float, values[3].split()))
                    # Оставляем мощности больше заданной
                    valid_powers = [p for p in power_values if p > min_power_db]
                    if not valid_powers:
                        continue
                    # Сопоставляем время данных с временем GPS
                    if first_gps_time:
                        relative_time = t_data - first_valid_time
                        measurement_time = first_gps_time + timedelta(seconds=relative_time)
                        # Ищем ближайшее время GPS
                        gps_times_seconds = [(ts - first_gps_time).total_seconds() for ts in time_stamps]
                        target_sec = (measurement_time - first_gps_time).total_seconds()
                        closest_idx = min(range(len(gps_times_seconds)), key=lambda i: abs(gps_times_seconds[i] - target_sec))
                        time_diff = abs(gps_times_seconds[closest_idx] - target_sec)
                        # Если время близко и частоты в диапазоне, добавляем точку
                        if time_diff <= 1.0 and min_frequency <= freq_min <= max_frequency and min_frequency <= freq_max <= max_frequency:
                            filtered_data_points.append({
                                "coords": gps_coords_with_altitude[closest_idx],
                                "timestamp": measurement_time,
                                "freq_min": freq_min,
                                "freq_max": freq_max,
                                "powers": valid_powers
                            })
                            matches += 1
                            # Готовим данные для сохранения
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
        return []

    # --- Создание и показ карты 2D ---

    logging.info("Создание карты 2D...")
    print("Создание карты 2D...")
    # Берем центр карты из первой отобранной точки, если есть
    map_center = filtered_data_points[0]['coords'][:2] if filtered_data_points else [0, 0]
    # Делаем карту folium с центром в этой точке
    m = folium.Map(location=map_center, zoom_start=12, tiles=None)
    # Добавляем слой Stadia Maps Alidade Smooth для карты
    folium.TileLayer(
        'https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}{r}.png',
        attr='© <a href="https://stadiamaps.com/">Stadia Maps</a> © <a href="https://openmaptiles.org/">OpenMapTiles</a> © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        name='Stadia Maps Alidade Smooth',
        control=True
    ).add_to(m)

    logging.info("Добавление точек на карту...")
    print("Добавление точек на карту...")
    # Делаем группу для маркеров, чтобы объединять близкие
    marker_cluster = MarkerCluster().add_to(m)
    # Ставим маркеры для каждой отобранной точки
    for i, data in enumerate(filtered_data_points):
        lat, lon, alt = data['coords']
        # Готовим текст для всплывающей подсказки
        tooltip_text = f"Точка {i + 1}<br>"
        tooltip_text += f"Параметры отбора:<br>Мин. частота: {min_frequency} МГц<br>Макс. частота: {max_frequency} МГц<br>Мин. мощность: {min_power_db} дБ<br><br>"
        tooltip_text += f"Координаты: Широта {lat:.6f}, Долгота {lon:.6f}, Высота {alt:.2f} м<br>"
        tooltip_text += f"Время: {data['timestamp'].strftime('%H:%M:%S')}<br>"
        tooltip_text += f"Частоты: {data['freq_min']} - {data['freq_max']} МГц<br>"
        tooltip_text += f"Мощности: {', '.join(map(str, data['powers']))} дБ"
        # Добавляем маркер с подсказкой
        folium.Marker((lat, lon), tooltip=tooltip_text).add_to(marker_cluster)

    # Показываем карту в Jupyter Notebook
    logging.info("Показ карты...")
    print("Показ карты...")
    display(m)

    logging.info("Работа с данными завершена.")
    print("Работа с данными завершена.")
    logging.info(f"Найдено {matches} точек по параметрам отбора.")
    print(f"Найдено {matches} точек по параметрам отбора.")
    # Показываем информацию об отобранных данных
    if filtered_lines:
        logging.info(f"Отобрано {len(filtered_lines)} строк данных.")
        print(f"Отобранные данные (первые 10 строк):")
        for i, line in enumerate(filtered_lines[:10]):
            print(line.strip())
            if i == 9:
                break
        if len(filtered_lines) > 10:
            print(f"... и еще {len(filtered_lines) - 10} строк.")

    # --- Обработка действий пользователя после отбора ---

    while True:
        print("\nВыберите действие (введите номера через запятую или пробел):")
        print("1. Показать все найденные точки")
        print("2. Сохранить отобранные данные в файл")
        print("3. Сохранить карту как KML")
        print("4. Сохранить карту как HTML")
        print("5. Выйти")
        print("6. Задать новые параметры отбора")  # Новый пункт

        choices_str = input("Введите номера действий: ").strip()
        choices = choices_str.replace(',', ' ').split()

        # Основа имени файла для сохранения
        base_filename = f"filtered_data_minfreq-{min_frequency}_maxfreq-{max_frequency}_minpower-{min_power_db:.2f}"
        exit_flag = False

        # Обрабатываем выбор
        for choice in choices:
            if choice == '1':
                logging.info("Выбрано: Показать все найденные точки.")
                print("\n--- Все найденные точки ---")
                for i, data in enumerate(filtered_data_points):
                    print(f"Точка {i + 1}")
                    print(f"Координаты: Широта {data['coords'][0]:.6f}, Долгота {data['coords'][1]:.6f}, Высота {data['coords'][2]:.2f} м")
                    print(f"Время: {data['timestamp'].strftime('%H:%M:%S')}")
                    print(f"Частоты: {data['freq_min']} - {data['freq_max']} МГц")
                    print(f"Мощности: {', '.join(map(str, data['powers']))} дБ")
                    print("-" * 20)
            elif choice == '2':
                logging.info("Выбрано: Сохранить отобранные данные в файл.")
                filtered_data_filename = base_filename + FILTERED_FILE_SUFFIX
                print(f"Сохранение отобранных данных в файл: {filtered_data_filename} (.data)")
                try:
                    with open(filtered_data_filename, 'w') as f:
                        f.writelines(filtered_lines)
                    logging.info(f"Отобранные данные сохранены в файл: {filtered_data_filename}")
                    print(f"Отобранные данные сохранены.")
                except Exception as e:
                    logging.error(f"Ошибка при сохранении данных: {e}")
                    print(f"Ошибка при сохранении данных: {e}")
            elif choice == '3':
                logging.info("Выбрано: Сохранить карту как KML.")
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
            elif choice == '4':
                logging.info("Выбрано: Сохранить карту как HTML.")
                map_filename = f"map_{base_filename}{MAP_FILE_EXTENSION}"
                print(f"Сохранение карты как HTML в файл: {map_filename}")
                try:
                    m.save(map_filename)
                    logging.info(f"Карта сохранена как HTML в файл: {map_filename}")
                    print(f"Карта сохранена как HTML.")
                except Exception as e:
                    logging.error(f"Ошибка при сохранении HTML: {e}")
                    print(f"Ошибка при сохранении HTML: {e}")
            elif choice == '5':
                logging.info("Выбрано: Выход.")
                exit_flag = True
                break
            elif choice == '6':
                logging.info("Выбрано: Задать новые параметры отбора.")
                return 'retry_filter'  # Сигнал для повторного отбора
            elif choice:
                logging.warning(f"Неверный выбор: '{choice}'.")
                print(f"Неверный ввод: '{choice}'. Выберите из списка.")

        # Если выбрали выход, выходим из цикла
        if exit_flag:
            break

    # Возвращаем список отобранных точек
    return filtered_data_points

# --- Функция для ввода путей к файлам и параметров отбора ---

def get_file_paths_and_filter_params_v1():
    """
    Спрашивает у пользователя пути к файлам журнала и данных, а также параметры отбора (Вариант 1).
    Обрабатывает ошибки ввода и позволяет повторить отбор с другими параметрами.
    """
    print("Вариант 1:")
    # Спрашиваем путь к файлу журнала GPS
    log_file_path = select_file('.log')
    if not log_file_path:
        print("Путь к файлу журнала не указан. Программа остановлена.")
        return

    # Спрашиваем путь к файлу данных
    data_file_path = select_file('.data')
    if not data_file_path:
        print("Путь к файлу данных не указан. Программа остановлена.")
        return

    # Спрашиваем параметры отбора в цикле для правильного ввода
    while True:
        while True:
            try:
                min_freq = int(input("Введите минимальную частоту (МГц): "))
                break
            except ValueError:
                print("Ошибка: Введите целое число для минимальной частоты.")

        while True:
            try:
                max_freq = int(input("Введите максимальную частоту (МГц): "))
                if min_freq > max_freq:
                    print("Ошибка: Максимальная частота должна быть не меньше минимальной.")
                else:
                    break
            except ValueError:
                print("Ошибка: Введите целое число для максимальной частоты.")

        while True:
            try:
                min_power = float(input("Введите минимальную мощность (дБ): "))
                break
            except ValueError:
                print("Ошибка: Введите число для минимальной мощности.")

        logging.info(f"Параметры отбора: мин. частота={min_freq} МГц, макс. частота={max_freq} МГц, мин. мощность={min_power:.2f} дБ")
        # Вызываем функцию для отбора и создания карты
        result = log_to_kml_v1(log_file_path, None, data_file_path, min_freq, max_freq, min_power)

        # Обрабатываем результат
        if result == 'retry_filter' or not result:
            # Если нет результатов или пользователь хочет повторить
            if not result:
                answer = input("Отбор не дал результатов. Попробовать с другими параметрами? (да/нет): ").strip().lower()
                if answer != 'да':
                    break
            continue  # Спрашиваем новые параметры
        else:
            break  # Выходим, если все хорошо

# --- Основной блок программы ---

if __name__ == "__main__":
    logging.info("Старт программы.")
    # Запускаем функцию для ввода путей и параметров
    get_file_paths_and_filter_params_v1()
    logging.info("Программа завершена.")
