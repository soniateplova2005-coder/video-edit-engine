# video-edit-engine

Автоматизация технической части монтажа Reels: авто-кадрирование под 9:16
(трекинг лица), авто-субтитры (Whisper, покадровая подсветка слова), базовая
цветокоррекция и склейка с переходами.

Нарезка/выбор дублей — это редакторское решение, а не механический шаг,
поэтому она не автоматизирована полностью: `src/engine/beatsync.py` даёт сырые
тайминги битов и смен сцен, которые используются вручную под конкретное видео.

## Установка

```bash
pip install -r requirements.txt
# + ffmpeg должен быть в PATH
```

## Использование

```bash
python cli.py input.mp4 output.mp4
```

Флаги: `--no-vertical`, `--no-captions`, `--no-grade`, `--whisper-model small`.

## Структура

- `src/engine/reframe.py` — трекинг лица (MediaPipe) и авто-кроп в 9:16
- `src/engine/captions.py` — транскрипция (Whisper) и анимированные субтитры (ASS)
- `src/engine/beatsync.py` — детекция битов (librosa) и смен сцен (PySceneDetect)
- `src/engine/colorgrade.py` — цветокоррекция и xfade-переходы между клипами
- `src/engine/pipeline.py` — сборка шагов в один проход
- `cli.py` — точка входа
