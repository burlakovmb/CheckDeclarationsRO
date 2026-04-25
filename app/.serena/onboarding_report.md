# Отчёт онбординга — Declarations Checking

Дата: 2026-04-23

## Краткая сводка
- Проект: Declarations Checking (DUK-Integrator wrapper)
- Язык: Python (FastAPI)
- Веб-фреймворк: FastAPI
- Входная точка приложения: `app/app.py` (FastAPI на `/validate`)
- Вспомогательные модули: `app/runner.py`, `app/parser.py`
- Docker: `app/Dockerfile`

## Зависимости
- Python packages: перечислены в `app/requirements.txt` (`fastapi`, `uvicorn`)
- Системные требования: Java 8 JRE (контейнер использует `eclipse-temurin:8-jre-jammy`)
- Внешний артефакт: DUK Integrator (`duk/dist/DUKIntegrator.jar`), ожидается в `app/duk`

## Как запустить локально (Docker, рекомендуемый)
1. Сборка контейнера:

```bash
cd app
docker build -t check-declarations .
```

2. Запуск (порт 8000):

```bash
docker run -d -p 8000:8000 check-declarations
```

3. Пример запроса:

```bash
curl -X POST http://localhost:8000/validate -H "Content-Type: application/json" -d '{"declaration_type":"TYPE","xml":"<Declaration>...</Declaration>"}'
```

## Как запустить без Docker (dev)
1. Установить Java 8 и поместить `DUKIntegrator.jar` в папку `app/duk/dist` либо указать `DUK_PATH`.
2. Установить зависимости:

```bash
python -m pip install -r app/requirements.txt
```

3. Запустить uvicorn:

```bash
cd app
uvicorn app:app --host 0.0.0.0 --port 8000
```

4. Отправлять запросы на `http://localhost:8000/validate`.

## Рекомендации и замечания
- В репозитории пока нет тестов (unit/integration). Рекомендую добавить минимальные unit-тесты для `parser.py` и интеграционный тест для `runner.py` с моком/фейковой реализацией DUK.
- Добавить шаги CI (GitHub Actions) для проверки линтинга, запуска тестов и сборки Docker-образа.
- Зафиксировать версию Python и использовать `requirements.txt` с зафиксированными версиями (например, `fastapi==...`).
- Добавить документацию OpenAPI (FastAPI уже генерирует `/docs`).

## Артефакты онбординга
- Этот файл: `app/.serena/onboarding_report.md` — краткий отчёт и инструкции.

---

Если хотите, могу:
- Добавить минимальные unit-тесты и CI workflow;
- Автоматически пометить онбординг как выполненный (создать файл-флаг);
- Собрать Docker-образ локально и запустить контейнер для проверки.
