# Питончик

Питончик - программа, нацеленная на облегчение трудовой рутины, уменьшению времени на рабочие процессы и автоматизацию повторяющихся действий.

Для работы, переместите exe-файл себе на компьютер, желательно в отдельной папке, т.к. все выходные файлы будут сохраняться туда, где находится сам exe-файл.

**ВАЖНО!** После того как поработали с файлами выхода, желательно их удалять, т.к. при будущем запуске того же скрипта, могут возникать ошибки.

{% cut "Последнюю версию можно скачать тут" %}

{% file src="/edadeal/pitonchik-informacija-2-dcceeb/.files/pitonchik-8.exe" name="Питончик.exe" type="application/x-msdownload" %}

{% endcut %}

## Последние обновления

* Исправлена функция матчинга координат, считает только уникальные координаты
* Добавлена функция сбора адресов и координат к ним, из поля target_shops_coords
* Добавлена функция скачивания фида
* Добавлена функция сравнения остатков по магазинам

## Функционал

1. {% cut "Собрать адреса из json" %}

   Бывает, что нам необходимо собрать адреса из файла/ов json, для того, чтобы сопоставить покрытие.

   {% endcut %}

2. {% cut "Сжать картинки в 2 раза" %}

   Если нам для загрузки каталога excel необходимо уменьшить размер архива изображений.

   {% endcut %}

3. {% cut "Проверить матчинг адресов с координатами" %}

   Если какие-то адреса не матчатся с адресами в базааре, одна из причин - это несоответствие значения в поле target_shops с ключом в поле target_shops_coords. Программа скажет, есть ли ошибка в этом.

   {% endcut %}

4. {% cut "Собрать barcode из json" %}

   Если ритейлер передает товарный фид из штрихкодов, бывает так, что они матчатся с нашей базой. Для создания задачи на датапрод программа вытащит все штрихкоды.

   {% endcut %}

5. {% cut "Показать кол-во уникальных офферов, сколько всего" %}

   Если у вас фид по магазинам и необходимо узнать сколько всего уникальных офферов.

   {% endcut %}

6. {% cut "Записать тестовый json" %}

   Записывает сокращенный json файл, для тестов загрузки. Загрузить тестовый json, внести изменения, попробовать загрузить можно по [ссылке](https://getpantry.cloud/).

   {% endcut %}

7. {% cut "Поменять формат картинкам" %}

   Поможет, если вам присылают картинки товаров в невалидном формате.

   {% endcut %}

8. {% cut "Сравнить цены" %}

   Помогает понять разницу цен между магазинами, сделать вывод, о возможности замены target_shops на target_regions.

   {% endcut %}

Функционал можно расширять, либо корректировать непосредственно под вас, может вы нашли баг, обратитесь к [svirin-da](https://staff.yandex-team.ru/svirin-da).

## Подробное описание функций

### 1. Собрать адреса из json

**Вход**: 1+ json файл.

**Что делает**: Поочередно открывает каждый выбранный файл json и забирает оттуда значение полей target_shops и target_regions, с приоритетом на target_regions.

**Выход**: CSV файл со списком адресов.

{% cut "Пример" %}

![Пример 1](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image.png =400x400)  ![Пример 2](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-1.png =400x400) ![Пример 3](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-2.png =400x400)

{% endcut %}

### 2. Сжать картинки в 2 раза

**Вход**: 1+ изображение (поддерживаемые форматы: PNG, JPG, WEBP, TIF).

**Что делает**: Проходит по каждому выбранному изображению, уменьшает размер в 2 раза и оптимизирует качество.

**Выход**: ZIP-архив с уменьшенными изображениями в формате PNG.

{% cut "Пример" %}

![Пример 1](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-3.png =400x400)  ![Пример 2](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-4.png =400x400)  ![Пример 3](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-5.png =400x400)

{% endcut %}

### 3. Проверить матчинг адресов с координатами

**Вход**: 1+ json файл.

**Что делает**: Поочередно открывает каждый выбранный файл json, забирает все адреса из поля target_shops, сравнивает их с ключами в поле target_shops_coords.

**Выход**:

* Информационное окно с:
  * Общим количеством каталогов
  * Общим количеством координат
  * Количеством адресов с найденными координатами
  * Списком адресов без координат
* CSV файл с адресами, для которых не найдены координаты

{% cut "Пример" %}

![Пример 1](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-6.png =400x400)  ![Пример 2](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-7.png =400x400)  ![Пример 3](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-8.png =400x400)

{% endcut %}

### 4. Собрать barcode из json

**Вход**: 1+ json файл.

**Что делает**: Поочередно открывает каждый выбранный файл json, собирает уникальные штрихкоды длиной более 5 символов из поля offers.barcode.

**Выход**: CSV файл со списком уникальных штрихкодов.

{% cut "Пример" %}

![Пример 1](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-9.png =400x400)  ![Пример 2](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-10.png =400x400)  ![Пример 3](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-11.png =400x400)

{% endcut %}

### 5. Показать кол-во уникальных офферов

**Вход**: 1+ json файл.

**Что делает**: Поочередно открывает каждый выбранный файл json, подсчитывает общее количество офферов и количество уникальных значений в поле offers.description.

**Выход**: Информационное окно с общим количеством офферов и количеством уникальных офферов.

{% cut "Пример" %}

![Пример 1](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-12.png =400x400)  ![Пример 2](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-13.png =400x400)  ![Пример 3](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-14.png =400x400)

{% endcut %}

### 6. Записать тестовый json

**Вход**: 1 json файл.

**Что делает**: Создает сокращенный файл json, сохраняя:

* Все каталоги с одним оффером для каждого
* Соответствующие офферы для каждого каталога
* Поле target_shops_coords без изменений

**Выход**: Сокращенный JSON файл с суффиксом '_test'.

{% cut "Пример" %}

![Пример 1](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-15.png =400x400)  ![Пример 2](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-16.png =400x400)  ![Пример 3](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-17.png =400x400)

{% endcut %}

### 7. Поменять формат картинкам

**Вход**: 1+ изображение (поддерживаемые форматы: PNG, JPG, WEBP, TIF).

**Что делает**: Конвертирует все выбранные изображения в формат PNG.

**Выход**: Папка "Картинки формат" с конвертированными изображениями.

{% cut "Пример" %}

![Пример 1](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-18.png =400x400)  ![Пример 2](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-19.png =400x400)  ![Пример 3](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-20.png =400x400)

{% endcut %}

### 8. Сравнить цены

**Вход**: 1+ json файл.

**Что делает**: Анализирует цены для каждого уникального товара (по полю offers.description):

* Собирает все уникальные цены для каждого товара
* Подсчитывает количество товаров с разными ценами
* Вычисляет разницу между максимальной и минимальной ценой
* Строит гистограмму распределения разницы цен

**Выход**:

* Информационное окно с:
  * Количеством уникальных офферов
  * Количеством офферов с разными ценами
  * Процентом офферов с разными ценами
* Гистограмма разницы цен (сохраняется как "Разница цен.png")

{% cut "Пример" %}

![Пример 1](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-21.png =400x400)  ![Пример 2](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-22.png =400x400)  ![Пример 3](/users/svirin-da/pdf-instrukcija/pitonchik-informacija-2/.files/image-23.png =400x400)

{% endcut %}
