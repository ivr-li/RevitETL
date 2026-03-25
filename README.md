# RevtiETL — Архитектура

## Проблема

Текущая система построена на ручном управлении: `.bat` файлы, `.exe` скрипты, Планировщик задач Windows. Любое изменение требует перекомпиляции `.exe`, ручного контроля, нет единого интерфейса для мониторинга и запуска.

## Решение

Airflow в Docker — оркестратор (UI, расписание, ретраи, логи). BIM Agent на Windows — набор Python-сервисов для запуска Navisworks, обработки XML и загрузки в SIGNAL. Admin Panel (Streamlit) — GUI для управления конфигурацией. Вся остальная Python-логика выполняется внутри Docker-контейнеров.

**Основа:** [finloop/airflow-postgres-superset-on-docker](https://github.com/finloop/airflow-postgres-superset-on-docker)

## Схема

```
Docker (Linux)                              Windows Host
┌──────────────────────────────┐            ┌─────────────────────────┐
│ Airflow 2.10.5               │   HTTP     │ BIM Agent (Python)      │
│  (CeleryExecutor)            │──────────► │  services/runner.py     │
│  - webserver :8080 (UI)      │            │                         │
│  - scheduler                 │            │ Admin Panel (Streamlit)  │
│  - worker                    │            │  admin/app.py           │
│  - Redis (broker)            │            │                         │
│  - Flower :5555 (мониторинг) │            │ ClashRunner (.NET C#)   │
│                              │            │                         │
│ PostgreSQL                   │            │ Доступ к:               │
│  - airflow-postgres          │            │  → Navisworks.exe       │
│  - client-postgres :5051     │            │  → \\fs\bim\ (UNC)      │
│  - warehouse-postgres :5052  │            └─────────────────────────┘
│                              │
│ Superset :5054 (дашборды)    │
│ pgAdmin :5050 (управление БД)│
│                              │
│ volumes:                     │
│  - ./airflow/dags            │
│  - ./airflow/plugins         │
│  - ./config                  │
└──────────────────────────────┘
```

## Разделение ответственности

**В Docker (Airflow)** — всё что не требует Windows:
- Оркестрация (DAGs, расписание, ретраи, UI)
- Кастомные операторы PostgreSQL (DataFrame ↔ PostgreSQL)
- ETL пайплайны (шаблоны в `airflow/dags/templs/`)

**На Windows хосте (BIM Agent)** — только то, что требует Windows:
- Запуск Navisworks `FileToolsTaskRunner.exe` (экспорт RVT → NWD) через `NWDData`
- XML-обработка коллизий (`CleanXMLData` — разбиение, `UpdateXMLData` — обновление по GUID)
- Загрузка NWD в SIGNAL (`SignalUploader`)
- Генерация BAT/TXT конфигов из conf.yml (`foled_generator.py`)
- Доступ к UNC-путям `\\fs\bim\...`

**Admin Panel (Streamlit)** — управление конфигурацией:
- CRUD проектов в `conf.yml`
- Редактирование глобальных настроек (defaults)
- Управление check_mappings (RVT → XML-проверки ModelChecker)

## Структура проекта

```
RevtiETL/
├── docker-compose.yaml               # Airflow + PostgreSQL + Superset + pgAdmin
├── .env                               # Credentials + AIRFLOW_UID + SIGNAL keys
├── config/
│   └── conf.yml                       # Единый конфиг (defaults + projects)
├── airflow/
│   ├── dags/
│   │   ├── dag_baseline.py            # Базовый DAG (шаблон)
│   │   ├── lib/                       # Библиотеки для DAG tasks
│   │   └── templs/                    # Шаблоны ETL DAGs (customers, orders, ml)
│   ├── plugins/
│   │   └── operators/postgres.py      # DataFrame ↔ PostgreSQL операторы
│   └── logs/
├── admin/                             # Streamlit Admin Panel
│   ├── app.py                         # Главное приложение (CRUD проекты + defaults)
│   ├── config.py                      # ConfigManager — чтение/запись conf.yml
│   └── forms.py                       # ProjectForm — формы проектов
├── bim_agent/
│   ├── resources/
│   │   ├── model_checker/             # XML-шаблоны проверок (MC_01..MC_06)
│   │   └── navisworks/                # XML-конфиги (поисковые наборы, проверки)
│   ├── services/
│   │   ├── config.py                  # DIRS, NAVISWORKS_EXE, загрузка conf.yml
│   │   ├── foled_generator.py         # Генерация каталогов, BAT/TXT конфигов
│   │   └── runner.py                  # NWDData, CleanXML, UpdateXML, SignalUploader, Runner
│   └── routers/                       # (пока пустой)
├── navisworks_clash_runner/           # .NET C# — автоматизация Clash Detective
│   ├── NavisworksClashRunner.sln
│   ├── PackageContents.xml            # Манифест плагина Navisworks
│   ├── deploy.bat                     # Деплой плагина в ApplicationPlugins
│   ├── ClashRunner.Shared/            # Модели данных + XmlReportBuilder
│   ├── ClashRunner.Automation/        # Консольное .exe — загрузка NWD/NWF
│   └── ClashRunner.Plugin/            # AddIn — импорт настроек, запуск тестов
├── superset/                          # Конфигурация Superset
├── client-postgres-init/              # Скрипты инициализации БД
├── docs/                              # Архитектура (drawio, jpg)
└── old_ex/                            # Старый код (справочно)
```

Структура каталогов проекта на файловом сервере (генерируется `foled_generator.py`):
```
00.BIM_Export/
└── <folder_name>/
    ├── 01_NWD/
    │   ├── 00_Data/
    │   │   ├── <project_id>.txt       # Список RVT-файлов
    │   │   ├── <project_id>.bat       # BAT для запуска Navisworks
    │   │   └── <project_id>.log       # Лог экспорта
    │   ├── 01.Сборка_Общая.nwd
    │   └── ...
    ├── 02_Collisions/
    │   ├── 00_Data/
    │   │   ├── archive_<date>/        # Архивы предыдущих XML
    │   │   └── Проверка на пересечения.xml
    │   ├── <имя_rvt>.xml              # Разбитые XML по файлам
    │   └── ...
    ├── 03_ModelChecker/
    │   └── 00_Data/
    └── 00_Templates/
        └── model_checker/
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
| airflow-postgres | — | Метаданные Airflow |
| client-postgres | 5051 | БД для данных проектов |
| warehouse-postgres | 5052 | DWH / data lake |
| superset | 5054 | BI-дашборды |
| pgadmin | 5050 | Управление базами данных |

### BIM Agent (Python, Windows)

Набор Python-сервисов для автоматизации BIM-процессов. Основная логика в `bim_agent/services/runner.py`.

**Классы runner.py:**

- **`NWDData`** — запуск BAT-файла экспорта RVT → NWD, ожидание лога завершения (polling каждые 30с, таймаут 7ч)
- **`CleanXMLData`** — очистка и разбиение сводного XML коллизий по RVT-файлам (архивирование старых, фильтрация по `clashobject/smarttag`)
- **`UpdateXMLData`** — обновление целевого XML по GUID из отдельных XML-файлов в родительской папке
- **`SignalUploader`** — загрузка NWD в облако SIGNAL: auth → signed URL → S3 upload → commit → version → docs item. Параллельная загрузка через `ThreadPoolExecutor(max_workers=9)`
- **`Runner`** — оркестратор пайплайна:
  - `run_nwd_export()` — запуск экспорта для списка папок
  - `xml_export()` — update → clean для XML коллизий
  - `run_full_pipeline()` — полный цикл: export → xml → signal

**Генератор конфигов** (`foled_generator.py`):
- Создаёт каталоги проекта (01_NWD, 02_Collisions, 03_ModelChecker + 00_Data)
- Генерирует TXT-конфиг (список RVT-файлов с полными путями)
- Генерирует BAT-файл для запуска `FileToolsTaskRunner.exe`

### Admin Panel (Streamlit)

Веб-интерфейс (`admin/app.py`) для управления `config/conf.yml`:
- **Сайдбар** — глобальные настройки (output_path, export_files, xml_template, check_mappings)
- **Вкладка "Проекты"** — просмотр/редактирование/удаление проектов
- **Вкладка "Добавить проект"** — создание нового (name, folder_name, export paths, signal IDs)
- **Вкладка "Проверки"** — управление check_mappings (RVT → XML-проверки ModelChecker)

`admin/config.py` — `ConfigManager`: загрузка conf.yml с merge defaults, CRUD проектов, поддержка `"USE_DEFAULTS"` для файлов экспорта.

### Единый конфиг (config/conf.yml)

```yaml
defaults:
  navisworks_exe: "C:\\Program Files\\Autodesk\\Navisworks Manage 2022\\FileToolsTaskRunner.exe"
  signal_max_workers: 9
  bim_agent_url: "http://host.docker.internal:8000"
  output_path: "\\\\fs\\bim\\Projects\\00.BIM_Export\\Tests_zone"
  export_files:                        # Стандартный набор RVT-файлов
    - "01.Сборка_Общая.rvt"
    - "02.Сборка_Архитектура.rvt"
    # ...
  xml_template: "Проверка_файлов.xml"
  check_mappings:                      # RVT → XML-проверки ModelChecker
    "02.Сборка_Архитектура.rvt":
      - template: "MC_01_Проверка файла AR для Архитектора.xml"
        output: "Проверка AR для Архитектора.xlsx"
    # ...

projects:
  testp:
    name: "Тестовая зона"
    folder_name: "testp"
    output_path: "\\\\fs\\bim\\..."
    export:
      source_path: "\\\\fs\\bim\\...\\02_NWD"
      files:                           # или "USE_DEFAULTS"
        - "99_AS.rvt"
    signal:
      project_id: "uuid"
      folder_id: "uuid"
      filter: "_"
```

- `defaults.export_files` — стандартный набор файлов (проект может указать `"USE_DEFAULTS"`)
- `defaults.check_mappings` — сопоставление RVT → XML-проверки ModelChecker
- Каждый шаг опционален — если нет секции `signal`, загрузка не выполняется

### Кастомные Airflow-операторы

`airflow/plugins/operators/postgres.py`:
- `DataFrameToPostgresOverrideOperator` — сохранение DataFrame в PostgreSQL (warehouse)
- `PostgresToDataFrameOperator` — загрузка DataFrame из PostgreSQL (client)
- `CheckIfTableExistsOperator` — проверка существования таблицы

### ClashRunner (.NET C#)

Автоматизация Navisworks Clash Detective:
- **ClashRunner.Automation** — консольное .exe, загружает NWD/NWF и вызывает плагин
- **ClashRunner.Plugin** — AddIn для Navisworks, импортирует настройки и запускает clash-тесты
- **ClashRunner.Shared** — модели данных: `ClashResultEntry`, `ClashTestSummary`, `ClashObjectInfo`, `SmartTag`, `CliArgs`, `XmlReportBuilder`

## Связь Docker ↔ Windows Host

- Airflow из Docker обращается к BIM Agent через `host.docker.internal:8000`
- BIM Agent и Airflow читают общий `config/conf.yml` (volume mount `./config:/opt/airflow/config`)
- Файлы (NWD, Excel, XML) доступны через UNC-пути

## Что заменяет новая архитектура

| Было | Стало |
|------|-------|
| Config_*.txt (15 файлов) | Генерируются из conf.yml (`foled_generator.py`) |
| .bat файлы (15 файлов) | Генерируются из conf.yml (`foled_generator.py`) |
| .exe файлы (Signal, Clean, Update) | Python-классы в `runner.py` |
| Планировщик задач Windows | Airflow scheduler + cron |
| Ручные пути в SIGNAL | В conf.yml → signal.project_id/folder_id |
| Ручной контроль | Airflow UI + логи + ретраи |
| Ручное редактирование конфигов | Admin Panel (Streamlit) |

## Фазы реализации

### Фаза 1 — Инфраструктура + экспорт NWD (done)
1. docker-compose.yaml (Airflow 2.10.5 + PostgreSQL + Superset + pgAdmin)
2. `config/conf.yml` — единый конфиг (defaults + projects)
3. `bim_agent/services/config.py` — загрузка конфига, DIRS
4. `bim_agent/services/foled_generator.py` — генерация каталогов и BAT/TXT
5. `bim_agent/services/runner.py` — NWDData (экспорт), Runner (оркестратор)
6. `airflow/dags/dag_baseline.py` — базовый DAG

### Фаза 2 — XML-обработка коллизий (done)
1. `CleanXMLData` — разбиение сводного XML по RVT-файлам
2. `UpdateXMLData` — обновление XML по GUID
3. `Runner.xml_export()` — оркестрация update → clean

### Фаза 3 — SIGNAL upload (done)
1. `SignalUploader` — загрузка NWD в SIGNAL (auth → S3 → version → docs)
2. Параллельная загрузка через ThreadPoolExecutor

### Фаза 4 — Admin Panel (done)
1. `admin/app.py` — Streamlit UI для управления conf.yml
2. `admin/config.py` — ConfigManager с merge defaults
3. `admin/forms.py` — ProjectForm

### Фаза 5 — ClashRunner .NET (done)
1. `ClashRunner.Automation` — консольное .exe для Navisworks
2. `ClashRunner.Plugin` — AddIn плагин
3. `ClashRunner.Shared` — модели данных

### Фаза 6 — Интеграция + все проекты (в процессе)
1. Перенести все ~15 проектов в conf.yml
2. Настроить cron-расписание в DAGs
3. Реализовать FastAPI роутеры в bim_agent/routers/
4. Интеграция BIM Agent с Airflow через HttpOperator
