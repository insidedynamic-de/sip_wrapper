# FreeSWITCH на Coolify - Быстрый старт

## За 2 минуты

### Шаг 1: Создайте сервис в Coolify

1. Откройте Coolify → Projects → Ваш проект
2. Нажмите **"Add New Service"**
3. Выберите **"Docker Compose"**

### Шаг 2: Подключите Git

**Вариант A - Ваш репозиторий:**
- Repository URL: `https://github.com/your-org/freeswitch-production.git`
- Branch: `main`
- Docker Compose Location: `docker-compose.coolify.yml`

**Вариант B - Вставить напрямую:**
Скопируйте содержимое [docker-compose.coolify.yml](docker-compose.coolify.yml) в Coolify UI.

### Шаг 3: Настройте ENV переменные

В разделе **Environment Variables** в Coolify UI добавьте:

```bash
# ОБЯЗАТЕЛЬНО
FS_DOMAIN=sip.yourdomain.com
EXTERNAL_SIP_IP=203.0.113.10
EXTERNAL_RTP_IP=203.0.113.10
USERS=alice:SecretPass123:1001,bob:SecretPass456:1002
GATEWAYS=provider:sip.provider.com:5060:username:password:true:udp
DEFAULT_GATEWAY=provider
DEFAULT_EXTENSION=1001
```

**💡 Узнать IP вашего Coolify сервера:**
```bash
curl ifconfig.me
```

### Шаг 4: Deploy

Нажмите **"Deploy"** и дождитесь завершения (1-2 минуты).

### Шаг 5: Проверка

В Coolify откройте **Terminal** вашего сервиса:

```bash
fs_cli -x "sofia status"
```

Должно показать:
```
Profile internal: UP (port 5060)
Profile external: UP (port 5080)
```

## Готово! 🎉

Теперь можно:
1. Зарегистрировать SIP клиент на `EXTERNAL_SIP_IP:5060`
2. Звонить через gateway
3. Принимать входящие звонки

---

## Настройка SIP клиента

**Пример с Linphone/Zoiper:**

```
Сервер: 203.0.113.10 (ваш EXTERNAL_SIP_IP)
Порт: 5060
Username: alice
Password: SecretPass123
Domain: sip.yourdomain.com (или оставьте пустым)
Transport: UDP
```

---

## Troubleshooting

### Build failed: "no such file or directory"

Если вы видите ошибку:
```
failed to solve: failed to read dockerfile: open Dockerfile.production: no such file or directory
```

**Решение:**
Убедитесь, что файлы закоммичены в Git:
```bash
git add Dockerfile.coolify provision.sh docker-entrypoint.sh docker-compose.coolify.yml
git commit -m "Add Coolify deployment files"
git push origin main
```

Затем в Coolify нажмите "Redeploy".

### Gateway не регистрируется

В Coolify Terminal:
```bash
fs_cli -x "sofia status gateway provider"
```

Если показывает "NOREG" или "FAIL":
1. Проверьте credentials в `GATEWAYS`
2. Проверьте firewall разрешает UDP порты
3. Включите debug: добавьте в ENV: `SIP_DEBUG=9`

### Пользователи не могут регистрироваться

1. Проверьте `EXTERNAL_SIP_IP` установлен на **публичный IP** сервера
2. Проверьте firewall открыт для UDP 5060
3. В Coolify Terminal:
   ```bash
   fs_cli -x "sofia status profile internal"
   ```

### Нет звука

1. Проверьте `EXTERNAL_RTP_IP` = публичный IP
2. Откройте UDP порты **16384-32768** в firewall
3. Убедитесь, что в docker-compose.coolify.yml используется `network_mode: host`

---

## Примеры конфигураций

### Простой офис (3 пользователя, 1 провайдер)

```bash
FS_DOMAIN=office.mycompany.com
EXTERNAL_SIP_IP=203.0.113.50
EXTERNAL_RTP_IP=203.0.113.50
USERS=alice:Pass123:1001,bob:Pass456:1002,carol:Pass789:1003
GATEWAYS=voip:sip.provider.com:5060:account123:secret:true:udp
DEFAULT_GATEWAY=voip
DEFAULT_EXTENSION=1001
```

### Multi-provider (разные направления)

```bash
FS_DOMAIN=pbx.company.com
EXTERNAL_SIP_IP=203.0.113.100
EXTERNAL_RTP_IP=203.0.113.100
USERS=user1:Pass1:1001,user2:Pass2:1002
GATEWAYS=provider_de:sip.de.com:5060:user_de:pass_de:true:udp,provider_us:sip.us.com:5060:user_us:pass_us:true:udp
OUTBOUND_ROUTES=^\+49.*:provider_de,^\+1.*:provider_us
INBOUND_ROUTES=+4930111111:1001,+4930222222:1002
```

### SIP Trunk без авторизации

```bash
FS_DOMAIN=trunk.example.com
EXTERNAL_SIP_IP=203.0.113.200
EXTERNAL_RTP_IP=203.0.113.200
ACL_USERS=trunk:198.51.100.50:9000
GATEWAYS=provider:sip.provider.net:5060:::false:udp
DEFAULT_GATEWAY=provider
DEFAULT_EXTENSION=9000
```

---

## Полезные команды в Coolify Terminal

```bash
# Статус FreeSWITCH
fs_cli -x "status"

# Статус профилей
fs_cli -x "sofia status"

# Статус гатвеев
fs_cli -x "sofia status gateway"

# Зарегистрированные пользователи
fs_cli -x "show registrations"

# Активные звонки
fs_cli -x "show channels"

# Включить SIP trace для отладки
fs_cli -x "sofia global siptrace on"

# Перезагрузить конфигурацию
fs_cli -x "reloadxml"
```

---

## Дополнительная документация

- **[COOLIFY.md](COOLIFY.md)** - Полное руководство по Coolify
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Детальное руководство по deployment
- **[README.production.md](README.production.md)** - Полная документация
- **[.env.example](.env.example)** - Все ENV переменные с примерами

---

## Checklist для production

- [ ] `EXTERNAL_SIP_IP` и `EXTERNAL_RTP_IP` = публичный IP сервера
- [ ] Используются сильные пароли в `USERS`
- [ ] Firewall открыт: 5060, 5080, 16384-32768 UDP
- [ ] Gateway credentials правильные
- [ ] Протестированы inbound calls
- [ ] Протестированы outbound calls
- [ ] Протестирован звук
- [ ] Настроены health checks в Coolify
- [ ] Настроен backup volume

---

**Готово к использованию!** 🚀 FreeSWITCH запущен на Coolify за 2 минуты!
