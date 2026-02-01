# Auto IP Detection Feature

## Новая возможность: Автоматическое определение IP адреса

Оба файла (`docker-compose.coolify-debug.yml` и `docker-compose.coolify-debian.yml`) теперь **автоматически определяют** публичный IP адрес сервера, если вы:

1. Не указали `EXTERNAL_SIP_IP` и `EXTERNAL_RTP_IP`
2. Или оставили placeholder значение: `your-server-ip`

---

## Как это работает

### Если IP указан правильно:
```bash
EXTERNAL_SIP_IP=203.0.113.10
EXTERNAL_RTP_IP=203.0.113.10
```
✅ **Используется ваш IP** - автодетект не запускается

### Если IP = placeholder:
```bash
EXTERNAL_SIP_IP=your-server-ip
EXTERNAL_RTP_IP=your-server-ip
```
⚙️ **Автоматически определяет** публичный IP сервера

### Методы определения IP (в порядке попыток):

1. **Method 1**: `curl ifconfig.me`
2. **Method 2**: `curl ipinfo.io/ip` (если первый не сработал)
3. **Method 3**: `curl icanhazip.com` (если оба не сработали)

Timeout для каждого метода: **5 секунд**

---

## Что вы увидите в логах

### Успешное автоопределение:

```
[STEP 1/8] Validating environment variables...
WARNING: EXTERNAL_SIP_IP/EXTERNAL_RTP_IP are set to placeholder values!
Attempting to auto-detect server public IP address...
✓ Auto-detected public IP: 203.0.113.10
Using auto-detected IP for EXTERNAL_SIP_IP and EXTERNAL_RTP_IP
✓ Environment validation passed
Final configuration:
  EXTERNAL_SIP_IP: 203.0.113.10
  EXTERNAL_RTP_IP: 203.0.113.10
```

### Если автодетект не удался:

```
WARNING: EXTERNAL_SIP_IP/EXTERNAL_RTP_IP are set to placeholder values!
Attempting to auto-detect server public IP address...
ERROR: Could not auto-detect public IP address!
Please set EXTERNAL_SIP_IP and EXTERNAL_RTP_IP manually in Coolify UI.
Find your IP with: curl ifconfig.me
```

Container остановится с ошибкой, и вам нужно будет указать IP вручную.

---

## Примеры использования

### Вариант 1: Полностью автоматический (рекомендуется для тестов)

**ENV переменные в Coolify:**
```bash
FS_DOMAIN=apps.linkify.cloud
EXTERNAL_SIP_IP=your-server-ip  # Будет автоопределен
EXTERNAL_RTP_IP=your-server-ip  # Будет автоопределен
USERS=alice:SecretPass:1001
GATEWAYS=provider:fpbx.de:5060:user:pass:true:udp
DEFAULT_GATEWAY=provider
DEFAULT_EXTENSION=1001
```

FreeSWITCH автоматически определит IP сервера при запуске.

### Вариант 2: Указать IP вручную (рекомендуется для production)

**ENV переменные в Coolify:**
```bash
FS_DOMAIN=apps.linkify.cloud
EXTERNAL_SIP_IP=203.0.113.10  # Ваш реальный IP
EXTERNAL_RTP_IP=203.0.113.10  # Ваш реальный IP
USERS=alice:SecretPass:1001
GATEWAYS=provider:fpbx.de:5060:user:pass:true:udp
DEFAULT_GATEWAY=provider
DEFAULT_EXTENSION=1001
```

Автодетект не запустится, будет использован указанный IP.

---

## Когда использовать автодетект

### ✅ Хорошо для:
- **Тестирования** - быстрый запуск без настройки
- **Development** - не нужно искать IP каждый раз
- **Динамические IP** - если IP сервера может меняться

### ⚠️ Не рекомендуется для:
- **Production** - лучше указать IP явно
- **Серверы за NAT** - автодетект может вернуть внутренний IP
- **Proxy/Load Balancer** - может определить IP неправильно

---

## Troubleshooting

### Проблема: Автодетект определил неправильный IP

**Причина:** Сервер за NAT или используется proxy

**Решение:** Укажите IP вручную:
```bash
# Найдите публичный IP вашего сервера
curl ifconfig.me

# Установите в Coolify UI
EXTERNAL_SIP_IP=ваш_реальный_публичный_ip
EXTERNAL_RTP_IP=ваш_реальный_публичный_ip
```

### Проблема: "Could not auto-detect public IP address"

**Причины:**
1. Сервер не имеет доступа к интернету
2. Все три сервиса (ifconfig.me, ipinfo.io, icanhazip.com) недоступны
3. Firewall блокирует исходящие HTTPS запросы

**Решение:**
1. Проверьте интернет на сервере: `curl -I https://ifconfig.me`
2. Укажите IP вручную в ENV переменных

### Проблема: Контейнер перезапускается после успешного автодетекта

Автодетект работает правильно, но проблема на следующих шагах. Смотрите логи:
- Если застревает на **STEP 3**: Проблема с загрузкой GPG ключа
- Если застревает на **STEP 4**: Проблема установки FreeSWITCH
- Если застревает на **STEP 7**: Проблема в provision.sh (проверьте формат USERS/GATEWAYS)

---

## Технические детали

### Реализация в docker-compose.coolify-debug.yml:

```bash
# Check for placeholder values and auto-detect IP if needed
if [ "$EXTERNAL_SIP_IP" = "your-server-ip" ] || [ "$EXTERNAL_RTP_IP" = "your-server-ip" ]; then
  echo "WARNING: EXTERNAL_SIP_IP/EXTERNAL_RTP_IP are set to placeholder values!"
  echo "Attempting to auto-detect server public IP address..."

  # Try multiple methods to get public IP
  DETECTED_IP=""

  # Method 1: ifconfig.me
  DETECTED_IP=$$(curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "")

  # Method 2: ipinfo.io if first failed
  if [ -z "$$DETECTED_IP" ]; then
    DETECTED_IP=$$(curl -s --max-time 5 ipinfo.io/ip 2>/dev/null || echo "")
  fi

  # Method 3: icanhazip.com if both failed
  if [ -z "$$DETECTED_IP" ]; then
    DETECTED_IP=$$(curl -s --max-time 5 icanhazip.com 2>/dev/null || echo "")
  fi

  if [ -n "$$DETECTED_IP" ]; then
    echo "✓ Auto-detected public IP: $$DETECTED_IP"
    export EXTERNAL_SIP_IP="$$DETECTED_IP"
    export EXTERNAL_RTP_IP="$$DETECTED_IP"
    echo "Using auto-detected IP for EXTERNAL_SIP_IP and EXTERNAL_RTP_IP"
  else
    echo "ERROR: Could not auto-detect public IP address!"
    exit 1
  fi
fi
```

### Особенности:
- **3 резервных метода** определения IP
- **Timeout 5 секунд** на каждый метод
- **Fallback на ошибку** если все методы не сработали
- **Export переменных** для использования в provision.sh

---

## Совместимость

Эта функция работает в:
- ✅ `docker-compose.coolify-debug.yml` - с подробным логированием
- ✅ `docker-compose.coolify-debian.yml` - production версия
- ❌ `docker-compose.coolify.yml` - требует Dockerfile (не поддерживается)

---

## Резюме

**Теперь можно:**
1. Оставить `EXTERNAL_SIP_IP=your-server-ip` в Coolify
2. Container автоматически определит публичный IP при запуске
3. FreeSWITCH будет работать с правильным IP

**Или:**
1. Указать реальный IP вручную: `EXTERNAL_SIP_IP=203.0.113.10`
2. Автодетект не запустится
3. Будет использован указанный IP

**Рекомендация для production:** Всегда указывайте IP вручную для надежности и предсказуемости.
