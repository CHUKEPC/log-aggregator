# Сервис агрегации логов (Log Aggregator Service)

[![CI](https://github.com/CHUKEPC/log-aggregator/actions/workflows/ci.yml/badge.svg)](https://github.com/CHUKEPC/log-aggregator/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.12+-005571.svg?logo=elasticsearch&logoColor=white)](https://www.elastic.co/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://mypy-lang.org/)

Высокопроизводительный централизованный сервис сбора, парсинга и анализа логов. Спроектирован как легковесная, удобная для разработчиков альтернатива стеку ELK: включает поддержку разбора различных форматов логов, хранилище на базе Elasticsearch, полнотекстовый поиск, потоковую передачу логов в реальном времени через WebSocket (`tail -f`), правила алертинга на основе шаблонов и автоматическую очистку устаревших записей (TTL).

[English documentation (Английская версия)](README.md)

---

## Возможности

- **Прием логов через несколько транспортов**:
  - **REST API**: одиночный и пакетный (bulk batch) приём структурированных JSON-записей.
  - **Приём сырого текста (Raw Ingest)**: одиночные и пакетные эндпоинты для нераспарсенных строк с автоопределением или явным указанием формата.
  - **TCP сокет-сервер**: высокопроизводительный асинхронный TCP-сервер на базе asyncio (порт 9000) для непрерывной передачи логов напрямую от syslog-демонов, FluentBit, Logstash или netcat.
- **Движок парсинга различных форматов**:
  - **JSON**: парсинг структурированных логов с извлечением стандартных полей и сохранением произвольных метаданных.
  - **Syslog**: поддержка стандартов RFC 5424 и RFC 3164 (BSD) с маппингом facility и уровней важности (severity).
  - **Nginx**: Combined access-логи (с автоматическим сопоставлением HTTP-статусов) и error-логи.
  - **Apache**: форматы Combined и Common Log Format (CLF).
  - **Regex и Custom**: именованные группы захвата регулярных выражений для кастомных форматов логов приложений.
- **Хранение и поиск (Elasticsearch)**:
  - Полнотекстовый поиск по тексту сообщений, имени сервиса и источникам.
  - Гибкая фильтрация: по уровням важности (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`), сервисам, источникам и тегам.
  - Диапазонные запросы по времени (`start_time`, `end_time`) в формате ISO-8601.
  - Встроенный In-Memory бэкенд для быстрого локального запуска и запуска тестов без Elasticsearch.
- **Потоковая передача в реальном времени (WebSocket)**:
  - Real-time tailing логов через `/ws/logs` с серверной фильтрацией для каждого подключенного клиента по сервису, минимальному уровню и ключевым словам.
- **Агрегации и аналитика**:
  - Почасовые гистограммы распределения логов во времени.
  - Подсчет объема логов по уровням важности и сервисам.
  - Рейтинг наиболее частых сообщений об ошибках.
- **Алертинг на основе шаблонов**:
  - Настраиваемые правила алертинга: порог ошибок за скользящее окно, поиск по ключевым словам или regex-паттернам.
  - Асинхронная отправка webhook-уведомлений при срабатывании правила.
  - Аудит истории сработавших алертов.
- **Политика хранения логов (TTL)**:
  - Автоматическое или ручное удаление логов старше $N$ дней (`/api/v1/retention/cleanup`).
- **Безопасность уровня Production**:
  - OAuth2 Password Bearer и аутентификация по JWT-токенам.
  - Сервисная аутентификация по API-ключам через заголовок `X-API-Key`.
  - Ограничение частоты запросов (Rate Limiting) со скользящим окном.

---

## Стек технологий

- **Язык и среда**: Python 3.11+ (протестировано на 3.11, 3.12, 3.13)
- **Веб-фреймворк**: [FastAPI](https://fastapi.tiangolo.com/), [Starlette](https://www.starlette.io/), [Uvicorn](https://www.uvicorn.org/)
- **Поисковый движок**: [Elasticsearch](https://www.elastic.co/) (асинхронный клиент `elasticsearch-py`)
- **Валидация данных и конфигурация**: [Pydantic v2](https://docs.pydantic.dev/), [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **Безопасность**: PyJWT, Bcrypt, HTTPBearer
- **Сетевые протоколы**: WebSockets, Asyncio TCP sockets
- **Качество и тестирование**: Pytest, Pytest-Asyncio, Pytest-Cov, Ruff, Mypy (строгий режим `strict`)
- **Контейнеризация**: Docker, Docker Compose

---

## Архитектура и структура проекта

Проект строго следует принципам чистой архитектуры с разделением ответственности по подпакетам:

```
log-aggregator/
├── src/log_aggregator/
│   ├── __init__.py
│   ├── main.py                 # Инициализация приложения и lifespan (без бизнес-логики)
│   ├── config.py               # Настройки на базе Pydantic BaseSettings
│   ├── exceptions.py           # Иерархия доменных исключений
│   ├── api/                    # Маршрутизаторы HTTP и WebSocket
│   │   ├── __init__.py
│   │   ├── router.py           # Главный API роутер (/api/v1)
│   │   ├── deps.py             # Зависимости, JWT, проверка API ключей, Rate Limiting
│   │   ├── auth.py             # Эндпоинты аутентификации (/auth/login, /auth/token)
│   │   ├── ingest.py           # Прием логов (/ingest, /ingest/batch, /ingest/raw)
│   │   ├── search.py           # Поиск и получение логов (/search, /logs/{id})
│   │   ├── stats.py            # Метрики и гистограммы (/stats)
│   │   ├── alerts.py           # Управление правилами и событиями алертов (/alerts/rules, /alerts/events)
│   │   ├── retention.py        # Очистка устаревших логов (/retention/cleanup)
│   │   └── stream.py           # WebSocket стриминг логов (/ws/logs)
│   ├── models/                 # Доменные сущности и энумы
│   │   ├── __init__.py
│   │   └── log_entry.py        # LogEntry, LogFilter, LogStats, LogLevel, LogFormat
│   ├── schemas/                # Pydantic схемы запросов и ответов
│   │   ├── __init__.py
│   │   ├── auth.py             # Схемы логина и JWT токенов
│   │   ├── log.py              # Схемы приема, поиска и агрегаций
│   │   └── alerts.py           # Схемы конфигурации алертов
│   ├── parsers/                # Движок разбора форматов логов
│   │   ├── __init__.py
│   │   ├── base.py             # Абстрактный интерфейс BaseLogParser
│   │   ├── factory.py          # Автоопределение формата и фабрика парсеров
│   │   ├── json_parser.py      # Парсер JSON-логов
│   │   ├── syslog_parser.py    # Парсер RFC 5424 и RFC 3164 Syslog
│   │   ├── nginx_parser.py     # Парсер Nginx access и error логов
│   │   ├── apache_parser.py    # Парсер Apache Combined и Common Log Format
│   │   └── regex_parser.py     # Парсер регулярных выражений
│   ├── storage/                # Слой доступа к данным
│   │   ├── __init__.py
│   │   ├── base.py             # Интерфейс LogStorage
│   │   ├── elasticsearch.py    # Асинхронный бэкенд Elasticsearch
│   │   └── memory.py           # Потокобезопасный In-Memory бэкенд
│   ├── services/               # Слой бизнес-логики
│   │   ├── __init__.py
│   │   ├── ingester.py         # Пайплайн приема: парсинг -> запись -> алерты -> стриминг
│   │   ├── searcher.py         # Поиск и расчет агрегаций
│   │   ├── alerter.py          # Бизнес-логика правил алертинга
│   │   ├── retention.py        # Очистка логов по TTL
│   │   └── streamer.py         # Менеджер подписчиков WebSocket
│   ├── alerts/                 # Механизм мониторинга и оповещений
│   │   ├── __init__.py
│   │   ├── models.py           # Доменные модели AlertRule и AlertEvent
│   │   ├── evaluator.py        # Оценка правил в скользящем окне
│   │   └── notifier.py         # Диспетчер webhook-уведомлений и история событий
│   └── transport/              # Сетевые приемники
│       ├── __init__.py
│       └── tcp_server.py       # Asyncio TCP сокет-сервер
├── tests/                      # Набор тестов (unit и integration)
├── docker-compose.yml          # Запуск стека (App + Elasticsearch 8 + Kibana)
├── Dockerfile                  # Многоэтапная сборка Docker
├── Makefile                    # Скрипты автоматизации
├── pyproject.toml              # Единый конфигурационный файл
├── .env.example                # Шаблон переменных окружения
├── README.md                   # Документация на английском
└── README_RU.md                # Документация на русском
```

---

## Установка и запуск

### Требования
- Python 3.11+
- Docker и Docker Compose (опционально для полного стека с ES)

### Локальная разработка

1. **Клонируйте репозиторий**:
   ```bash
   git clone https://github.com/CHUKEPC/log-aggregator.git
   cd log-aggregator
   ```

2. **Создайте виртуальное окружение и установите зависимости**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -e ".[dev]"
   ```

3. **Скопируйте настройки окружения**:
   ```bash
   cp .env.example .env
   ```

4. **Запуск в режиме In-Memory (без необходимости в Elasticsearch)**:
   В файле `.env` укажите:
   ```env
   USE_MEMORY_STORAGE=true
   ENVIRONMENT=development
   ```

5. **Запустите сервер**:
   ```bash
   uvicorn log_aggregator.main:app --reload --port 8000
   ```
   Документация Swagger UI будет доступна по адресу: `http://localhost:8000/docs`

---

## Запуск в Docker Compose (Elasticsearch + Kibana)

Запуск полноценного продакшн-стека (сервис агрегатора + Elasticsearch 8.12 + Kibana):

```bash
docker-compose up -d
```

- **API сервис**: `http://localhost:8000`
- **Документация Swagger**: `http://localhost:8000/docs`
- **TCP сокет-приемник**: `localhost:9000`
- **Elasticsearch API**: `http://localhost:9200`
- **Kibana Web UI**: `http://localhost:5601`

Остановка сервисов:
```bash
docker-compose down
```

---

## Примеры использования API

### 1. Аутентификация

#### Получение JWT токена
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "adminpassword"}'
```
Ответ:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in_minutes": 60
}
```

---

### 2. Приём логов

#### Одиночный структурированный лог (REST)
```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Ошибка проведения платежа: недостаточно средств",
    "service": "payment-service",
    "level": "WARNING",
    "source": "api-gateway",
    "metadata": {
      "user_id": 98412,
      "amount": 250.00
    },
    "tags": ["payment", "checkout"]
  }'
```

#### Пакетный приём логов (Bulk Batch)
```bash
curl -X POST "http://localhost:8000/api/v1/ingest/batch" \
  -H "X-API-Key: secret-payment-key" \
  -H "Content-Type: application/json" \
  -d '{
    "logs": [
      {"message": "Кэш обновлен", "service": "redis-cache", "level": "INFO"},
      {"message": "Таймаут подключения к базе данных", "service": "db-proxy", "level": "ERROR"}
    ]
  }'
```

#### Приём сырых нераспарсенных строк (Nginx, Syslog, Apache)
```bash
curl -X POST "http://localhost:8000/api/v1/ingest/raw" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "raw": "192.168.1.1 - admin [10/Oct/2023:13:55:36 +0000] \"GET /api/v1/users HTTP/1.1\" 200 450",
    "format": "NGINX"
  }'
```

#### Отправка логов через TCP сокет (netcat / syslog)
```bash
echo '{"message": "Фоновая задача успешно завершена", "service": "worker", "level": "INFO"}' | nc localhost 9000
```

---

### 3. Поиск и фильтрация логов

#### Полнотекстовый поиск с фильтрами
```bash
curl -G "http://localhost:8000/api/v1/search" \
  --data-urlencode "q=платежа" \
  --data-urlencode "service=payment-service" \
  --data-urlencode "level=WARNING" \
  --data-urlencode "limit=20"
```

---

### 4. Потоковая передача в реальном времени (WebSocket)

Подключитесь к `/ws/logs` с параметрами фильтрации:

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/logs?service=payment-service&min_level=ERROR");

ws.onmessage = (event) => {
  const logEntry = JSON.parse(event.data);
  console.log(`[${logEntry.timestamp}] [${logEntry.level}] ${logEntry.message}`);
};
```

---

### 5. Метрики и статистика

Получение распределения логов по уровням, сервисам, рейтингу ошибок и почасовой гистограмме:

```bash
curl "http://localhost:8000/api/v1/stats"
```

---

### 6. Настройка алертинга

#### Создание правила алертинга
```bash
curl -X POST "http://localhost:8000/api/v1/alerts/rules" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Алерт критических сбоев платежей",
    "condition": "ERROR_COUNT",
    "service": "payment-service",
    "level": "ERROR",
    "threshold": 5,
    "window_minutes": 2,
    "webhook_url": "https://hooks.slack.com/services/...",
    "enabled": true
  }'
```

---

### 7. Политики хранения (Retention)

Удаление логов старше указанного количества дней:
```bash
curl -X POST "http://localhost:8000/api/v1/retention/cleanup?days=14" \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Тестирование и проверка качества

```bash
# Запуск тестов с отчетом о покрытии (цель: 80%+)
pytest

# Проверка линтером ruff
ruff check src/ tests/
ruff format --check src/ tests/

# Строгая проверка типов mypy
mypy src/
```

Или через `Makefile`:
```bash
make test
make lint
make type-check
make all
```

---

## Лицензия

Проект распространяется под лицензией MIT. Подробности см. в файле [LICENSE](LICENSE).
