# Решение Проблемы с GPG Ключом SignalWire

## Проблема

Контейнер застревает на STEP 3/8 при попытке загрузить GPG ключ от SignalWire:

```
[STEP 3/8] Adding SignalWire FreeSWITCH repository...
Downloading GPG key from SignalWire...
Attempt 1 of 3...
Failed to download GPG key (attempt 1/3)
Attempt 2 of 3...
Failed to download GPG key (attempt 2/3)
Attempt 3 of 3...
Failed to download GPG key (attempt 3/3)
ERROR: Could not download SignalWire GPG key after 3 attempts
```

## Причины

1. **Firewall** блокирует доступ к `files.freeswitch.org`
2. **Сетевые проблемы** на сервере Coolify
3. **SignalWire репозиторий временно недоступен**
4. **DNS не резолвит** `files.freeswitch.org`

---

## ✅ РЕШЕНИЕ 1: Используйте Pre-built Version (РЕКОМЕНДУЕТСЯ)

### ⚠️ ОБНОВЛЕНИЕ: SignalWire Docker Hub Недоступен

**Обнаружено:** Официальный образ `signalwire/freeswitch` недоступен на Docker Hub (требует авторизацию или не существует).

**Решение:** Используем альтернативный образ `ghcr.io/patrickbaus/freeswitch-docker:latest` из GitHub Container Registry.

### Что это?

Вместо установки FreeSWITCH из репозитория, используем **готовый Docker образ** из GitHub Container Registry.

### Преимущества:

- ✅ **Не нужен GPG ключ** - FreeSWITCH уже установлен в образе
- ✅ **Быстрый запуск** - не нужно устанавливать пакеты (2-3 минуты)
- ✅ **Меньше точек отказа** - всего 4 шага вместо 8
- ✅ **Работает даже при блокировке** files.freeswitch.org
- ✅ **Бесплатный доступ** - GitHub Container Registry не требует авторизацию

### Как использовать:

#### В Coolify UI:

1. **Откройте ваш FreeSWITCH сервис**
2. **Измените Docker Compose file на:** `docker-compose.coolify-prebuilt.yml`
3. **Убедитесь что ENV переменные установлены** (те же самые)
4. **Нажмите "Deploy"**

#### Пример ENV переменных (те же самые):

```bash
FS_DOMAIN=apps.linkify.cloud
EXTERNAL_SIP_IP=46.224.205.100
EXTERNAL_RTP_IP=46.224.205.100
USERS=alice:SecretPass:1001
GATEWAYS=provider:fpbx.de:5060:777z9uovpu:4UMtPyXw8Qss:true:udp
DEFAULT_GATEWAY=provider
DEFAULT_EXTENSION=1001
```

### Что вы увидите в логах:

```
==========================================
FreeSWITCH Coolify - Pre-built Image
Start time: Tue Jan 27 12:00:00 UTC 2026
==========================================

[STEP 1/4] Validating environment variables...
✓ Environment validated
  EXTERNAL_SIP_IP: 46.224.205.100
  EXTERNAL_RTP_IP: 46.224.205.100

[STEP 2/4] Installing dependencies...
✓ Dependencies installed

[STEP 3/4] Preparing configuration...
✓ Config directories prepared

[STEP 4/4] Running provision script...
✓ Provision completed

==========================================
Starting FreeSWITCH...
==========================================
```

Всего **4 шага** вместо 8, и никаких проблем с GPG ключом!

---

## ✅ РЕШЕНИЕ 2: Используйте Обновленную Debug Версию

### Что изменилось?

Обновлены `docker-compose.coolify-debug.yml` и `docker-compose.coolify-debian.yml` с:

- **3 резервных URL** для GPG ключа:
  1. `https://files.freeswitch.org/repo/deb/debian-release/fsstretch-archive-keyring.asc`
  2. `https://freeswitch.signalwire.com/repo/deb/debian-release/fsstretch-archive-keyring.asc`
  3. `https://files.freeswitch.org/repo/deb/freeswitch-1.10/fsstretch-archive-keyring.asc`

- **По 2 попытки на каждый URL** (всего 6 попыток вместо 3)
- **Лучшая диагностика** - показывает какой URL пробуется

### Как использовать:

1. **Закоммитьте изменения:**
   ```bash
   git add .
   git commit -m "Fix GPG key download with multiple fallback URLs"
   git push origin main
   ```

2. **В Coolify:** Redeploy с `docker-compose.coolify-debug.yml`

3. **Проверьте логи** - должно сработать на одном из резервных URL

---

## ✅ РЕШЕНИЕ 3: Проверьте Сетевую Связность

Если оба решения не работают, проблема в сети сервера.

### Диагностика на Coolify сервере:

```bash
# Проверьте доступ к SignalWire
curl -I https://files.freeswitch.org

# Ожидаемый ответ: HTTP/2 200
# Если не работает - проблема с firewall или DNS

# Проверьте альтернативный хост
curl -I https://freeswitch.signalwire.com

# Проверьте DNS
nslookup files.freeswitch.org

# Проверьте что wget работает
wget --timeout=10 --tries=1 -qO- https://files.freeswitch.org/repo/deb/debian-release/fsstretch-archive-keyring.asc
```

### Если все проверки проваливаются:

**Проблема:** Firewall блокирует HTTPS исходящие запросы к SignalWire

**Решение:**

1. Используйте **РЕШЕНИЕ 1** (Pre-built Version) - это обходит проблему
2. Или откройте firewall для:
   - `files.freeswitch.org` (порт 443)
   - `freeswitch.signalwire.com` (порт 443)

---

## ✅ РЕШЕНИЕ 3: Build from Source (Полная Независимость)

### Что это?

Компилируем FreeSWITCH из исходников с GitHub - полная независимость от SignalWire.

### Преимущества:

- ✅ **Полная независимость** - не нужен SignalWire репозиторий
- ✅ **Не нужен GPG ключ** - используем прямо GitHub
- ✅ **Свежая версия** - берем из официального репозитория
- ✅ **Возможность кастомизации** сборки

### Недостатки:

- ❌ **Долгая сборка** - ~15-20 минут при первом запуске
- ❌ **Требует ресурсов** - CPU и RAM для компиляции

### Как использовать:

**Файл:** `docker-compose.coolify-source.yml`

**В Coolify UI:**
1. Docker Compose file: `docker-compose.coolify-source.yml`
2. ENV переменные (те же самые)
3. Deploy и **дождитесь** ~20 минут (первая сборка)

**После первой сборки** контейнер запускается быстро (образ закеширован).

---

## Сравнение Версий

| Версия | Шагов | GPG ключ нужен? | Скорость | Надежность | Зависимости |
|--------|-------|----------------|----------|------------|-------------|
| **Pre-built (GHCR)** | 4 | ❌ Нет | ⚡ 2-3 мин | ✅✅✅ Высокая | GitHub CR |
| **Build from Source** | 6 | ❌ Нет | 🐢 15-20 мин | ✅✅✅ Высокая | GitHub |
| Debug (новая) | 8 | ✅ Да (3 URL) | 🐌 5-7 мин | ✅✅ Хорошая | SignalWire |
| Debian (новая) | 8 | ✅ Да (3 URL) | 🐌 5-7 мин | ✅✅ Хорошая | SignalWire |

---

## Рекомендация

### Для Вашей Ситуации:

Поскольку **SignalWire репозиторий требует аутентификацию** (возвращает 401), рекомендую:

### 🥇 Вариант 1: Pre-built Image (ЛУЧШИЙ ВЫБОР)

**Используйте:** `docker-compose.coolify-prebuilt.yml`

**Почему:**
- ⚡ Быстрый запуск (2-3 минуты)
- ✅ Не нужен GPG ключ
- ✅ Не нужен доступ к SignalWire
- ✅ Готовый образ с GitHub Container Registry

**Недостатки:**
- Зависит от доступности GitHub Container Registry

### 🥈 Вариант 2: Build from Source (ПОЛНАЯ НЕЗАВИСИМОСТЬ)

**Используйте:** `docker-compose.coolify-source.yml`

**Почему:**
- ✅ Полная независимость от SignalWire
- ✅ Свежая версия с GitHub
- ✅ Возможность кастомизации

**Недостатки:**
- 🐢 Долгая первая сборка (~20 минут)
- Требует CPU/RAM для компиляции

### 🥉 Вариант 3: Debug/Debian с резервными URL (НЕ РЕКОМЕНДУЕТСЯ)

**Причина:** SignalWire репозиторий **требует аутентификацию**, все резервные URL будут возвращать 401 Unauthorized.

**Используйте только если:**
- У вас есть токен доступа к SignalWire
- Вы готовы настроить аутентификацию в docker-compose

---

## Коммит Изменений

Перед деплоем в Coolify, закоммитьте все файлы:

```bash
git add docker-compose.coolify-debug.yml
git add docker-compose.coolify-debian.yml
git add docker-compose.coolify-prebuilt.yml
git add GPG_KEY_FIX.md
git commit -m "Add GPG key fallback URLs and pre-built image version"
git push origin main
```

---

## Что Делать Дальше

### ✅ Шаг 1: Закоммитьте Изменения

```bash
cd /путь/к/sip_wrapper
git add .
git commit -m "Add alternative deployment options without SignalWire auth"
git push origin main
```

### ✅ Шаг 2: Выберите Версию

#### Вариант A: Pre-built Version (РЕКОМЕНДУЕТСЯ) ⚡

```bash
1. Coolify UI → Ваш FreeSWITCH сервис
2. Docker Compose file: docker-compose.coolify-prebuilt.yml
3. ENV переменные - оставьте те же самые
4. Deploy
5. Проверьте логи - должно пройти все 4 шага за 2-3 минуты
```

**Ожидаемый лог:**
```
FreeSWITCH Coolify - Pre-built Image
[STEP 1/4] Validating environment variables... ✓
[STEP 2/4] Installing dependencies... ✓
[STEP 3/4] Preparing configuration... ✓
[STEP 4/4] Running provision script... ✓
Starting FreeSWITCH...
```

#### Вариант B: Build from Source (Если вариант A не работает) 🛠️

```bash
1. Coolify UI → Ваш FreeSWITCH сервис
2. Docker Compose file: docker-compose.coolify-source.yml
3. ENV переменные - оставьте те же самые
4. Deploy
5. ДОЖДИТЕСЬ ~15-20 минут (первая сборка)
6. Проверьте логи - после компиляции FreeSWITCH запустится
```

**Ожидаемый лог:**
```
FreeSWITCH Coolify - Build from Source
This will take ~15-20 minutes to compile
[STEP 1/6] Validating environment variables... ✓
[STEP 2/6] Installing build dependencies... ✓
[STEP 3/6] Downloading FreeSWITCH source code... ✓
[STEP 4/6] Building FreeSWITCH from source... (долго)
[STEP 5/6] Cleaning up build files... ✓
[STEP 6/6] Preparing configuration... ✓
Starting FreeSWITCH...
```

---

## Итог

**Самый быстрый путь к решению:**
1. Используйте `docker-compose.coolify-prebuilt.yml`
2. Деплой займет ~2-3 минуты (вместо 5-7)
3. Никаких проблем с GPG ключами
4. FreeSWITCH запустится и будет работать

**Если нужна установка из исходников:**
1. Закоммитьте обновленные файлы
2. Используйте `docker-compose.coolify-debug.yml` (теперь с 3 резервными URL)
3. Если все 3 URL не работают - firewall issue, используйте Pre-built Version
