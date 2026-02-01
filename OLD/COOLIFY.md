# FreeSWITCH Deployment on Coolify

Пошаговое руководство по развертыванию FreeSWITCH на Coolify.

## Содержание

1. [Быстрый старт](#быстрый-старт)
2. [Метод 1: Docker Compose](#метод-1-docker-compose-рекомендуется)
3. [Метод 2: Dockerfile](#метод-2-dockerfile)
4. [Настройка ENV-переменных](#настройка-env-переменных)
5. [Проверка работы](#проверка-работы)
6. [Troubleshooting](#troubleshooting)

---

## Быстрый старт

### Минимальная конфигурация

Для запуска FreeSWITCH в Coolify нужно настроить только эти переменные:

```bash
FS_DOMAIN=sip.example.com
EXTERNAL_SIP_IP=your-server-ip
EXTERNAL_RTP_IP=your-server-ip
USERS=alice:SecretPass123:1001,bob:SecretPass456:1002
GATEWAYS=provider:sip.provider.com:5060:username:password:true:udp
DEFAULT_GATEWAY=provider
DEFAULT_EXTENSION=1001
```

---

## Метод 1: Docker Compose (рекомендуется)

### Шаг 1: Создание сервиса в Coolify

1. **Откройте Coolify** → Projects → Ваш проект
2. **Нажмите** "Add New Service"
3. **Выберите** "Docker Compose"

### Шаг 2: Подключение Git репозитория

1. **Source Type:** Git Repository
2. **Repository URL:** `https://github.com/your-org/freeswitch-production.git`
3. **Branch:** `main`
4. **Docker Compose Location:** `docker-compose.coolify.yml`

Или вставьте содержимое [docker-compose.coolify.yml](docker-compose.coolify.yml) напрямую.

### Шаг 3: Настройка переменных окружения

В разделе **Environment Variables** добавьте:

#### Обязательные переменные:

```bash
FS_DOMAIN=sip.yourdomain.com
EXTERNAL_SIP_IP=203.0.113.10
EXTERNAL_RTP_IP=203.0.113.10
USERS=alice:SecretPass123:1001,bob:SecretPass456:1002
GATEWAYS=provider:sip.provider.com:5060:username:password:true:udp
```

**Важно:**
- `EXTERNAL_SIP_IP` и `EXTERNAL_RTP_IP` должны быть **публичным IP** вашего сервера
- Или используйте домен: `your-app.coolify.app` (но лучше IP)
- Если у вашего Coolify несколько серверов, используйте IP того сервера, где будет FreeSWITCH

#### Маршрутизация (выберите один вариант):

**Вариант A - Простая маршрутизация:**
```bash
DEFAULT_GATEWAY=provider
DEFAULT_EXTENSION=1001
```

**Вариант B - Сложная маршрутизация:**
```bash
OUTBOUND_ROUTES=^00.*:provider1,^0.*:provider2
INBOUND_ROUTES=+49301234567:1001,+49301234568:1002,*:1000
```

#### Дополнительные (опционально):

```bash
ACL_USERS=trunk:192.168.1.100:9000
INTERNAL_SIP_PORT=5060
EXTERNAL_SIP_PORT=5080
RTP_START_PORT=16384
RTP_END_PORT=32768
CODEC_PREFS=PCMU,PCMA,G729
SIP_DEBUG=0
SIP_TRACE=no
```

### Шаг 4: Настройка портов

**ВАЖНО:** FreeSWITCH требует определенные порты.

В настройках Coolify:

1. **Перейдите:** Service Settings → Network
2. **Network Mode:** `host` (рекомендуется)

Или если используете bridge networking:

**Публичные порты:**
```
5060:5060/udp   # SIP Internal
5080:5080/udp   # SIP External
16384-32768:udp # RTP Media Range
```

**Рекомендация:** Используйте `network_mode: host` (уже настроено в docker-compose.coolify.yml)

### Шаг 5: Deploy

1. **Нажмите** "Deploy"
2. **Дождитесь** завершения сборки и запуска
3. **Проверьте** логи

---

## Метод 2: Dockerfile

Если хотите использовать простой Dockerfile вместо Docker Compose:

### Шаг 1: Создание сервиса

1. **Coolify** → Add New Service
2. **Type:** Dockerfile
3. **Git Repository:** ваш репозиторий
4. **Dockerfile:** `Dockerfile.coolify`

### Шаг 2: Build Pack

```
Dockerfile: Dockerfile.coolify
Build Command: (оставьте пустым, Coolify сам соберет)
```

### Шаг 3: Настройка ENV

Те же переменные, что и для Docker Compose (см. выше).

### Шаг 4: Порты

```
5060/udp
5080/udp
16384-32768/udp
```

Или используйте `host` networking в advanced settings.

### Шаг 5: Deploy

Нажмите Deploy и дождитесь готовности.

---

## Настройка ENV-переменных

### Полный список переменных

#### 1. Core Settings (обязательно)

| Переменная | Описание | Пример |
|-----------|----------|--------|
| `FS_DOMAIN` | SIP domain | `sip.example.com` |
| `EXTERNAL_SIP_IP` | Публичный IP для SIP | `203.0.113.10` |
| `EXTERNAL_RTP_IP` | Публичный IP для RTP | `203.0.113.10` |

**Как узнать ваш IP:**
```bash
curl ifconfig.me
```

#### 2. Users (обязательно хотя бы один)

**Формат:** `username:password:extension`

```bash
USERS=alice:SecretPass123:1001,bob:SecretPass456:1002,carol:Pass789:1003
```

**ACL Users (опционально, без пароля):**

**Формат:** `username:ip_address:extension`

```bash
ACL_USERS=trunk1:192.168.1.100:2001,trunk2:10.0.0.50:2002
```

#### 3. Gateways (обязательно хотя бы один)

**Формат:** `name:host:port:username:password:register:transport`

```bash
GATEWAYS=provider:sip.provider.com:5060:myusername:mypassword:true:udp
```

**Несколько гатвеев:**
```bash
GATEWAYS=provider1:sip.p1.com:5060:user1:pass1:true:udp,provider2:sip.p2.com:5060:user2:pass2:true:udp
```

**Gateway без регистрации:**
```bash
GATEWAYS=trunk:sip.trunk.com:5060:::false:udp
```

#### 4. Outbound Routing (выберите один)

**Вариант A - Default Gateway (проще):**
```bash
DEFAULT_GATEWAY=provider
```

**Вариант B - Pattern-based routing:**
```bash
OUTBOUND_ROUTES=^00.*:provider1,^0[1-9].*:provider2:+49:0
```

Формат: `pattern:gateway:prepend:strip`

#### 5. Inbound Routing (выберите один)

**Вариант A - Default Extension (проще):**
```bash
DEFAULT_EXTENSION=1001
```

**Вариант B - DID routing:**
```bash
INBOUND_ROUTES=+49301234567:1001,+49301234568:1002,*:1000
```

Формат: `DID:extension`

#### 6. Optional Settings

```bash
INTERNAL_SIP_PORT=5060
EXTERNAL_SIP_PORT=5080
RTP_START_PORT=16384
RTP_END_PORT=32768
CODEC_PREFS=PCMU,PCMA,G729,opus
OUTBOUND_CODEC_PREFS=PCMU,PCMA,G729
SIP_DEBUG=0
SIP_TRACE=no
```

---

## Примеры конфигураций для Coolify

### Пример 1: Простой офисный PBX

```bash
# Базовая конфигурация
FS_DOMAIN=office.mycompany.com
EXTERNAL_SIP_IP=203.0.113.50
EXTERNAL_RTP_IP=203.0.113.50

# 3 сотрудника
USERS=alice:AlicePass123:1001,bob:BobPass456:1002,carol:CarolPass789:1003

# 1 провайдер
GATEWAYS=voip_provider:sip.provider.com:5060:account123:secret123:true:udp

# Простая маршрутизация
DEFAULT_GATEWAY=voip_provider
DEFAULT_EXTENSION=1001
```

### Пример 2: Multi-provider

```bash
FS_DOMAIN=pbx.company.com
EXTERNAL_SIP_IP=203.0.113.100
EXTERNAL_RTP_IP=203.0.113.100

USERS=user1:Pass1:1001,user2:Pass2:1002

# 2 провайдера
GATEWAYS=provider_de:sip.de-provider.com:5060:user_de:pass_de:true:udp,provider_us:sip.us-provider.com:5060:user_us:pass_us:true:udp

# Маршрутизация по направлениям
OUTBOUND_ROUTES=^\\+49.*:provider_de,^\\+1.*:provider_us,^.*:provider_de

# Разные DID на разных пользователей
INBOUND_ROUTES=+4930111111:1001,+4930222222:1002
```

### Пример 3: SIP Trunk (без auth)

```bash
FS_DOMAIN=trunk.example.com
EXTERNAL_SIP_IP=203.0.113.200
EXTERNAL_RTP_IP=203.0.113.200

# Нет пользователей с паролем
USERS=

# IP-based trunk
ACL_USERS=provider_trunk:198.51.100.50:9000

# Gateway без регистрации
GATEWAYS=provider:sip.provider.net:5060:::false:udp

DEFAULT_GATEWAY=provider
DEFAULT_EXTENSION=9000
```

---

## Проверка работы

### 1. Проверка логов в Coolify

Откройте **Logs** вашего сервиса и найдите:

```
[TIMESTAMP] ENTRYPOINT: Running provisioning...
[TIMESTAMP] Validating configuration...
[TIMESTAMP] Configuration validated
[TIMESTAMP] Generating vars.xml...
...
[TIMESTAMP] Provisioning completed successfully!
[TIMESTAMP] Starting FreeSWITCH...
```

### 2. Подключение к CLI

В Coolify, откройте **Terminal** вашего контейнера:

```bash
fs_cli
```

Или из терминала:
```bash
# Если знаете имя контейнера
docker exec -it freeswitch-container-id fs_cli
```

### 3. Проверка профилей

```bash
fs_cli -x "sofia status"
```

Должно показать:
```
Profile internal: UP (port 5060)
Profile external: UP (port 5080)
```

### 4. Проверка гатвеев

```bash
fs_cli -x "sofia status gateway"
```

Должно показать:
```
provider   REGED
```

### 5. Проверка пользователей

Когда пользователь зарегистрируется:

```bash
fs_cli -x "show registrations"
```

### 6. Тест регистрации SIP клиента

Настройте любой SIP клиент (например, Linphone, Zoiper):

```
Сервер: EXTERNAL_SIP_IP вашего Coolify сервера
Порт: 5060
Username: alice (из USERS)
Password: SecretPass123
Domain: FS_DOMAIN (или оставьте пустым)
```

---

## Troubleshooting

### Проблема: Gateway не регистрируется

**Проверка:**
```bash
fs_cli -x "sofia status gateway gateway_name"
```

**Решения:**
1. Проверьте правильность `GATEWAYS` (username, password)
2. Проверьте firewall на сервере Coolify
3. Проверьте, разрешает ли провайдер ваш IP
4. Включите debug:
   ```bash
   SIP_DEBUG=9
   SIP_TRACE=yes
   ```

### Проблема: Пользователи не могут регистрироваться

**Проверка:**
```bash
fs_cli -x "sofia status profile internal"
```

**Решения:**
1. Убедитесь, что `EXTERNAL_SIP_IP` установлен правильно
2. Проверьте порт 5060 UDP открыт в firewall
3. Проверьте правильность `USERS` (username:password:ext)
4. Проверьте security group в Coolify (если есть)

### Проблема: Нет звука (RTP)

**Решения:**
1. Проверьте `EXTERNAL_RTP_IP` установлен на публичный IP
2. Откройте порты `16384-32768` UDP в firewall
3. Проверьте NAT settings:
   ```bash
   cat /etc/freeswitch/vars.xml | grep external
   ```
4. Убедитесь, что `network_mode: host` используется

### Проблема: Не применяется конфигурация

**Решения:**
1. Перезапустите контейнер в Coolify (redeploy)
2. Проверьте логи на ошибки provisioning
3. Вручную перезагрузите конфигурацию:
   ```bash
   fs_cli -x "reloadxml"
   fs_cli -x "sofia profile internal restart reloadxml"
   fs_cli -x "sofia profile external restart reloadxml"
   ```

### Проблема: Контейнер не стартует

**Проверка логов:**
1. Coolify → Service → Logs
2. Найдите строку с ERROR
3. Обычно это:
   - Неправильный формат ENV переменных
   - Отсутствуют обязательные переменные (`FS_DOMAIN`, `EXTERNAL_SIP_IP`, etc.)
   - Проблема с портами

**Решение:**
- Проверьте все обязательные ENV установлены
- Проверьте формат USERS, GATEWAYS, ROUTES (запятые, двоеточия)

### Получение отладочной информации

```bash
# Войти в контейнер
docker exec -it container-id bash

# Проверить сгенерированные файлы
ls -la /etc/freeswitch/
cat /etc/freeswitch/vars.xml
cat /etc/freeswitch/sip_profiles/internal.xml
cat /etc/freeswitch/directory/default.xml

# Включить полный debug
fs_cli -x "console loglevel debug"
fs_cli -x "sofia global siptrace on"
```

---

## Coolify Advanced Settings

### Network Settings

**Рекомендуется:** `host` network mode

В docker-compose.coolify.yml уже настроено:
```yaml
network_mode: host
```

Если Coolify не поддерживает, используйте port mapping:
```yaml
ports:
  - "5060:5060/udp"
  - "5080:5080/udp"
  - "16384-32768:16384-32768/udp"
```

### Resource Limits

Добавьте в Coolify UI или docker-compose:

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      cpus: '1'
      memory: 512M
```

### Health Checks

Уже настроен в [docker-compose.coolify.yml](docker-compose.coolify.yml:62):

```yaml
healthcheck:
  test: ["CMD", "fs_cli", "-x", "status"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

### Persistent Storage

Backup volume уже настроен:

```yaml
volumes:
  - freeswitch_backups:/var/backups/freeswitch
```

Coolify автоматически создаст volume.

---

## Мониторинг в Coolify

### Проверка статуса

1. **Coolify Dashboard** → Your Service
2. **Status:** должен быть "Running" (зеленый)
3. **Health Check:** должен быть "Healthy"

### Логи

Coolify → Logs → выберите временной диапазон

Полезные строки для поиска:
```
"Provisioning completed successfully"
"FreeSWITCH is running"
"sofia status"
"REGED" (для gateways)
```

### Метрики (если настроены)

Coolify может показывать:
- CPU usage
- Memory usage
- Network I/O

Для FreeSWITCH нормально:
- CPU: 1-10% idle, до 50% при активных звонках
- Memory: 200-500 MB
- Network: зависит от количества звонков

---

## Production Checklist для Coolify

- [ ] `EXTERNAL_SIP_IP` и `EXTERNAL_RTP_IP` установлены на правильный публичный IP
- [ ] Используются сильные пароли в `USERS`
- [ ] Firewall открыт: 5060, 5080, 16384-32768 UDP
- [ ] Gateway credentials правильные
- [ ] Протестированы inbound calls
- [ ] Протестированы outbound calls
- [ ] Протестировано качество звука
- [ ] Настроен monitoring в Coolify
- [ ] Настроены alerts (если доступно)
- [ ] Backup volume создан и работает
- [ ] Health check работает

---

## Дополнительные ресурсы

- [QUICKSTART.md](QUICKSTART.md) - Быстрый старт
- [README.production.md](README.production.md) - Полная документация
- [DEPLOYMENT.md](DEPLOYMENT.md) - Детальное руководство
- [.env.example](.env.example) - Примеры переменных

---

## Поддержка

При проблемах:
1. Проверьте [Troubleshooting](#troubleshooting) выше
2. Проверьте логи в Coolify
3. Используйте fs_cli для диагностики
4. Откройте issue на GitHub с логами

---

**Успешного развертывания на Coolify!** 🚀
