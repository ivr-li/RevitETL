# RevtiETL — Архитектура

## Проблема

Текущая система построена на ручном управлении: `.bat` файлы, `.exe` скрипты, Планировщик задач Windows. Любое изменение требует перекомпиляции `.exe`, ручного контроля, нет единого интерфейса для мониторинга и запуска.

## Решение

Airflow в Docker — оркестратор (UI, расписание, ретраи, логи). BIM Agent на Windows — прослойка для запуска Navisworks/Revit. Вся остальная Python-логика выполняется внутри Docker-контейнеров.

**Основа:** [finloop/airflow-postgres-superset-on-docker](https://github.com/finloop/airflow-postgres-superset-on-docker)

## Схема

```
Docker (Linux)                              Windows Host
┌──────────────────────────────┐            ┌─────────────────────────┐
│ Airflow (CeleryExecutor)     │   HTTP     │ BIM Agent (FastAPI)     │
│  - webserver :8080 (UI)      │──────────► |  :8000                  │
│  - scheduler                 │            │                         │
│  - worker                    │            │ /api/export             │
│  - Redis (broker)            │            │ /api/checker            │
│  - Flower :5555 (мониторинг) │            │ /api/status/{task_id}   │
│                              │            │                         │
│ PostgreSQL                   │            │ Доступ к:               │
│  - client-postgres :5051     │            │  → Navisworks.exe       │
│  - warehouse-postgres :5052  │            │  → Revit                │
│                              │            │  → \\fs\bim\ (UNC)      │
│ Superset :5054 (дашборды)    │            └─────────────────────────┘
│ pgAdmin :5050 (управление БД)│
│                              │
│ Python tasks (внутри):       │
│  - signal_upload             │
│  - excel_processing          │
│  - clash_detection           │
│                              │
│ volumes:                     │
│  - ./airflow/dags            │
│  - ./config                  │
└──────────────────────────────┘
```

```
        ┌─────────────┐
        │  Streamlit  │
        │  UI portal  │
        └──────┬──────┘
               │ REST
               │
        ┌──────▼──────┐
        │   Airflow   │
        │   API / UI  │
        └──────┬──────┘
               │
 ┌─────────────▼─────────────┐
 │        Airflow DAGs       │
 │ export → upload → check   │
 └─────────────┬─────────────┘
               │
        host.docker.internal
               │
        ┌──────▼──────┐
        │  BIM Agent  │
        │  FastAPI    │
        └─────────────┘
```

## Разделение ответственности

**В Docker (Airflow)** — всё что не требует Windows:
- Оркестрация (DAGs, расписание, ретраи, UI)
- SIGNAL upload (Python, requests)
- Excel обработка (Python, pandas/openpyxl)
- XML clash detection (Python, xml.etree)
- PostgreSQL — метаданные Airflow + data lake

**На Windows хосте (BIM Agent)** — только то, что требует Windows:
- Запуск Navisworks `FileToolsTaskRunner.exe` (экспорт RVT → NWD)
- Запуск Revit ModelChecker
- Доступ к UNC-путям `\\fs\bim\...`

## Структура проекта

```
RevtiETL/
├── docker-compose.yaml               # Airflow + PostgreSQL + Superset + pgAdmin
├── .env                               # Credentials + AIRFLOW_UID
├── config/
│   └── projects.yaml                  # Единый конфиг всех проектов
├── airflow/
│   └── dags/
│       ├── dag_factory.py             # Генерация DAG из projects.yaml
│       └── lib/
│           ├── signal_upload.py       # Загрузка NWD в SIGNAL
│           ├── model_checker.py       # Обработка Excel отчётов
│           └── clash_detection.py     # XML split/merge/export
├── bim_agent/
│   ├── main.py                        # FastAPI приложение
│   ├── routers/
│   │   ├── export.py                  # /api/export — запуск Navisworks
│   │   └── checker.py                 # /api/checker — запуск Revit ModelChecker
│   ├── services/
│   │   └── navisworks.py              # Генерация конфигов + subprocess
│   └── requirements.txt
├── superset/                          # Конфигурация Superset
├── client-postgres-init/              # Скрипты инициализации БД
└── old_ex/                            # Старый код (справочно)
```

## Компоненты

### Docker-сервисы (docker-compose.yaml)

| Сервис | Порт | Назначение |
|--------|------|------------|
| airflow-webserver | 8080 | UI для управления DAGs |
| airflow-scheduler | — | Планировщик задач |
| airflow-worker | — | Исполнитель задач (CeleryExecutor) |
| redis | — | Брокер сообщений для Celery |
| flower | 5555 | Мониторинг Celery workers |
| client-postgres | 5051 | БД для данных проектов |
| warehouse-postgres | 5052 | DWH / data lake |
| superset | 5054 | BI-дашборды |
| pgadmin | 5050 | Управление базами данных |

### BIM Agent (FastAPI, Windows)

Минимальный сервис — прослойка между Airflow и Windows-программами. Запускается на хосте, слушает порт 8000.

**Эндпоинты:**

`POST /api/export` — запуск экспорта RVT → NWD
```json
{"project": "KGN_GP06", "files": ["02.Сборка_Архитектура.rvt"]}
→ {"task_id": "abc-123", "status": "running"}
```

`POST /api/checker` — запуск Revit ModelChecker
```json
{"project": "KGN_GP06"}
→ {"task_id": "def-456", "status": "running"}
```

`GET /api/status/{task_id}` — статус задачи
```json
→ {"status": "completed", "logs": "...", "artifacts": ["path/to/file.nwd"]}
```

**Внутренняя логика:**
1. Читает `config/projects.yaml` для получения путей
2. Генерирует временный `.txt` конфиг (список `.rvt` файлов)
3. Запускает `subprocess`: `FileToolsTaskRunner.exe /i config.txt /od output/ /log log.txt`
4. Отслеживает процесс, возвращает статус через `/api/status`

### DAG Factory (dag_factory.py)

Читает `config/projects.yaml` и для каждого проекта автоматически создаёт DAG в Airflow:

```
[call_bim_export] → [upload_signal] → [notify]
                  → [call_bim_checker] → [process_excel]
```

| Task | Тип оператора | Где выполняется |
|------|---------------|-----------------|
| call_bim_export | HttpOperator → BIM Agent | Windows (через агент) |
| upload_signal | PythonOperator | Docker (внутри контейнера) |
| call_bim_checker | HttpOperator → BIM Agent | Windows (через агент) |
| process_excel | PythonOperator | Docker (внутри контейнера) |
| notify | PythonOperator | Docker (внутри контейнера) |

**Ручной запуск** через Airflow UI → "Trigger DAG with config":
```json
{"files": ["02.Сборка_Архитектура.rvt"], "steps": ["export"]}
```

### Единый конфиг (config/projects.yaml)

```yaml
defaults:
  navisworks_exe: "C:\\Program Files\\Autodesk\\Navisworks Manage 2022\\FileToolsTaskRunner.exe"
  signal_max_workers: 9
  bim_agent_url: "http://host.docker.internal:8000"

projects:
  KGN_GP06:
    name: "Курган ГП06"
    export:
      source_path: "\\\\fs\\bim\\...\\02_NWD"
      output_path: "\\\\fs\\bim\\...\\KGN_GP06"
      files:
        - "01.Сборка_Общая.rvt"
        - "02.Сборка_Архитектура.rvt"
        - "03.1 Сборка_Конструктив.rvt"
    signal:
      project_id: "78048844-..."
      folder_id: "0a2c3623-..."
      filter: "Сборка"
    checker:
      xml_template: "Проверка_файлов.xml"
      data_path: "\\\\fs\\bim\\...\\KGN_GP06"
    schedule:
      export_cron: "0 18 * * 2,5"    # Вт, Пт 18:00
      signal_cron: "0 8 * * 3"       # Ср 08:00
```

Каждый шаг опционален — если в YAML нет секции `signal`, соответствующий task не создаётся.

### Модули airflow/dags/lib/

Выполняются внутри Docker-контейнера.

**signal_upload.py** — загрузка NWD в облако SIGNAL:
- `upload_project(project_config, files=None)` → auth + upload + forge convert
- Credentials из `.env`
- Параллельная загрузка (ThreadPoolExecutor)

**model_checker.py** — обработка Excel отчётов ModelChecker:
- `process_excel(project_config)` → сборка DataFrame.xlsx по дисциплинам (AR, AS, SC, WSS, HVAC)

**clash_detection.py** — обработка XML пересечений:
- `split_xml(source_xml, output_dir)` → разбиение сводного XML по RVT файлам
- `merge_updates(source_xml, updates_dir)` → слияние обновлений по GUID
- `export_marked(xml_path)` → экспорт помеченных конфликтов в Excel

## Связь Docker ↔ Windows Host

- Airflow из Docker обращается к BIM Agent через `host.docker.internal:8000`
- BIM Agent и Airflow читают общий `config/projects.yaml`
- Файлы (NWD, Excel, XML) доступны через shared volume или через BIM Agent

## Что заменяет новая архитектура

| Было | Стало |
|------|-------|
| Config_*.txt (15 файлов) | Генерируются из projects.yaml |
| .bat файлы (15 файлов) | BIM Agent subprocess |
| .exe файлы (Signal, Clean, Update, ListOfMark, Excel) | Python-модули в dags/lib/ |
| Планировщик задач Windows | Airflow scheduler + cron |
| "00. Пути в SIGNAL.txt" | В projects.yaml |
| Ручной контроль | Airflow UI + логи + ретраи |

## Фазы реализации

### Фаза 1 — Инфраструктура + экспорт NWD
1. Адаптировать docker-compose.yaml (volume для config/, переменная BIM_AGENT_URL)
2. Создать BIM Agent (FastAPI) с эндпоинтом `/api/export`
3. Создать `config/projects.yaml` для 1-2 проектов
4. Создать `dag_factory.py` — DAG с HttpOperator к BIM Agent
5. Проверить: `docker-compose up` → Airflow UI → Trigger DAG → NWD файлы

### Фаза 2 — SIGNAL upload
1. Рефакторинг старого main.py → `dags/lib/signal_upload.py`
2. Добавить task `upload_signal` в DAG
3. Полная цепочка: export → upload

### Фаза 3 — ModelChecker + Clash detection
1. Добавить `/api/checker` в BIM Agent
2. `dags/lib/model_checker.py` и `dags/lib/clash_detection.py`
3. Добавить tasks в DAG

### Фаза 4 — Все проекты + расписание
1. Перенести все ~15 проектов в `projects.yaml`
2. Настроить cron-расписание
3. (Позже) Notion-интеграция для автоматического расписания
