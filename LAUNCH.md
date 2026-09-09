# Product Hunt — материалы запуска

## Карточка продукта

**Name:** `burn`

**Tagline** (60 знаков максимум — считай символы, PH режет молча):
```
See what Claude actually did for you today
```
41 символ. Запасные:
```
Your Claude Code day, in tokens, dollars and code     (52)
How much did Claude do for you today?                 (37)
Turn your Claude Code day into a number               (38)
```

**Topics:** Developer Tools · Artificial Intelligence · Productivity · Open Source · Command Line Interfaces

**Links:** GitHub-репозиторий как основная ссылка. Сайта нет и не нужно — аудитория PH в среду утром это разработчики, им хватит README.

**Pricing:** Free · Open Source

---

## Description (260 знаков)

```
A local CLI that reads your Claude Code transcripts and tells you what the day
was worth: tokens, API-equivalent cost, how much prompt caching saved you, and
the commits and lines that came out of it — measured against the Linux kernel,
Doom and the first commit of git.
```

---

## First comment — самое важное поле

На Product Hunt первый комментарий мейкера читают чаще, чем описание. Он должен отвечать
на «зачем это мне», а не пересказывать фичи.

```
Hi Product Hunt 👋

I build platforms with Claude Code every day. Last Sunday I shipped 13 services and
around 101,000 lines of Go in four days, and I had no idea what that actually cost —
Claude Code shows a session number, never a day, and never connects tokens to what
got built.

So I wrote burn. It reads the transcripts already on your disk and answers three
questions at once:

  what the model did      877,508,082 tokens · 5,598 calls · 32% of output was thinking
  what it would cost      $630.91 at API rates
  what came out of it     30 commits · 11,070 lines across 4 repositories

Two things surprised me the first time I ran it.

The first: 98% of that token volume was cache reads, billed at a tenth of the input
rate. Caching saved $3,877 that day. If your cache-read share is low, that is a real
finding — something in your prompt prefix is changing between requests and silently
invalidating it.

The second: if you are on a subscription, you did not pay that $630. burn says so on
every run and shows what the day was worth against Pro, Max 5× and Max 20×. That day
was 3.2 months of Max 20× — delivered in one day.

And because a number alone is not motivating, burn compares your output to code you
already have a feel for. That day was 28% of the Doom engine, with 27,930 lines to go
before passing it. The first Linux kernel was 10,239 lines — a normal day with an agent
now exceeds what Torvalds released in 1991.

The legends list lives in legends.json. Send a pull request with the one you want to
race — that is the roadmap.

No network calls. No account. Reads ~/.claude and your git history, nothing else.
engine.py is 120 lines; read it before you run it.

  git clone <repo> && cd burn && python3 burn.py

Curious what your numbers look like — post them.
```

---

## Стратегия запуска

### Когда

**Вторник или среда, 00:01 PST** (13:01 по Астане). Сутки на PH считаются с полуночи по
тихоокеанскому времени — запуск в 9 утра означает потерю трети суток. Понедельник и пятница
слабее, выходные мёртвые.

### Первый час решает

Алгоритм PH выводит наверх то, что набрало скорость рано. Что нужно подготовить **до** запуска:

- 10–15 человек, которые знают дату и час. Не «поддержите когда-нибудь», а «в среду в 13:01
  по Астане». Отдельно каждому, не в общий чат.
- **Просить комментарий, а не апвоут.** Комментарии весят больше и не выглядят накруткой.
- Свой первый комментарий опубликовать сразу после запуска, не через час.
- Скриншот вывода на реальных данных — не мокап. Люди отличают.

### Чего не делать

- Не просить голоса публично постом «заапвоутьте меня» — PH это наказывает.
- Не запускать в один день с крупным AI-релизом. Проверить главную PH накануне.
- Не использовать голоса новых аккаунтов — фильтруется.

### Ассеты

| Что | Требование | Статус |
|---|---|---|
| Иконка | 240×240 | ❌ нужна |
| Галерея | 1270×760, первый кадр решает | ❌ нужен скриншот вывода |
| Демо | GIF работы с анимацией счёта | ❌ записать `burn` без `--no-anim` |

Для GIF: запустить `burn` в чистом терминале, тёмная тема, шрифт покрупнее.
Анимация счёта вверх — это то, ради чего смотрят.

---

## Если не залетит — план на повтор

Cursor подавался четыре раза. Это норма, а не исключение. Правила PH разрешают релонч,
если продукт существенно изменился.

**Что менять между попытками — по убыванию влияния:**

1. **Tagline.** Первое, что видят, и единственное, что видит большинство. Тестировать
   формулировки.
2. **Первый кадр галереи.** Второе по влиянию.
3. **Первый комментарий.** Начинать с самой сильной цифры, а не с «привет, я сделал».
4. **Новая фича как повод.** Именно поэтому список легенд вынесен в JSON: каждый релонч —
   «добавили N новых проектов для сравнения», и это честный повод, а не переупаковка.

**Между попытками:** собирать реальные цифры пользователей. «1 200 разработчиков узнали,
что их подписка отдаёт в среднем $340 в день» — это заголовок сильнее любого tagline.

---

## Чего в продукте не хватает до запуска

- [ ] **Репозиторий должен быть публичным.** Сейчас у аккаунта 0 публичных репозиториев —
      ссылка с PH никуда не приведёт.
- [ ] Иконка, скриншот, GIF
- [ ] Проверить на чужой машине: у другого человека может не быть `~/.claude/projects`
      или транскрипты могут иметь другую форму. Нужен дружелюбный отказ, а не traceback.
- [ ] `--since` для диапазона дат: «неделя» и «месяц» — очевидный следующий вопрос
- [ ] Установка одной строкой: `pipx install` или `uvx`, чтобы не клонировать репозиторий
