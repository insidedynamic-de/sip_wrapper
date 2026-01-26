# FreeSWITCH Production - Coolify Ready

> Production-ready FreeSWITCH with ENV-based configuration. Deploy to Coolify in 2 minutes.

[![GitHub](https://img.shields.io/badge/GitHub-insidedynamic--de%2Fsip__wrapper-blue?logo=github)](https://github.com/insidedynamic-de/sip_wrapper)

---

## 🚀 Deploy to Coolify (2 минуты)

### 1. Create Service

Coolify → **Add New Service** → **Docker Compose**

### 2. Connect Git

- **Repository:** `https://github.com/insidedynamic-de/sip_wrapper.git`
- **Branch:** `main`
- **Docker Compose file:** `docker-compose.coolify.yml`

### 3. Set ENV Variables (в Coolify UI)

```bash
# REQUIRED
FS_DOMAIN=sip.yourdomain.com
EXTERNAL_SIP_IP=your-server-ip
EXTERNAL_RTP_IP=your-server-ip

# USERS (format: username:password:extension)
USERS=alice:SecretPass123:1001,bob:SecretPass456:1002

# GATEWAYS (format: name:host:port:user:pass:register:transport)
GATEWAYS=provider:sip.provider.com:5060:username:password:true:udp

# ROUTING
DEFAULT_GATEWAY=provider
DEFAULT_EXTENSION=1001
```

**💡 Как узнать IP сервера:**
```bash
curl ifconfig.me
```

### 4. Deploy

Нажмите **Deploy** → Готово! ✅

### 5. Verify

В Coolify Terminal:
```bash
fs_cli -x "sofia status"
```

---

## 📖 Документация

| Файл | Описание |
|------|----------|
| **[COOLIFY_QUICKSTART.md](COOLIFY_QUICKSTART.md)** | Быстрый старт для Coolify |
| **[COOLIFY.md](COOLIFY.md)** | Полное руководство по Coolify |
| **[.env.example](.env.example)** | Все ENV переменные с примерами |
| **[QUICKSTART.md](QUICKSTART.md)** | Быстрый старт Docker/Linux |
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | Детальное руководство |

---

## ⚙️ Конфигурация

### Минимальная конфигурация

```bash
FS_DOMAIN=sip.example.com
EXTERNAL_SIP_IP=203.0.113.10
EXTERNAL_RTP_IP=203.0.113.10
USERS=alice:pass:1001
GATEWAYS=provider:sip.provider.com:5060:user:pass:true:udp
DEFAULT_GATEWAY=provider
DEFAULT_EXTENSION=1001
```

### Расширенная конфигурация

**Multiple users:**
```bash
USERS=alice:pass1:1001,bob:pass2:1002,carol:pass3:1003
```

**ACL users (без пароля, по IP):**
```bash
ACL_USERS=trunk:192.168.1.100:9000
```

**Multiple gateways:**
```bash
GATEWAYS=provider1:sip.p1.com:5060:u1:p1:true:udp,provider2:sip.p2.com:5060:u2:p2:true:udp
```

**Pattern-based routing:**
```bash
OUTBOUND_ROUTES=^00.*:provider1,^0.*:provider2
INBOUND_ROUTES=+49301234567:1001,+49301234568:1002,*:1000
```

Полный список: [.env.example](.env.example)

---

## 🎯 Примеры

### Простой офис

3 пользователя, 1 провайдер:

```bash
FS_DOMAIN=office.local
EXTERNAL_SIP_IP=203.0.113.50
EXTERNAL_RTP_IP=203.0.113.50
USERS=alice:Pass123:1001,bob:Pass456:1002,carol:Pass789:1003
GATEWAYS=provider:sip.provider.com:5060:account:secret:true:udp
DEFAULT_GATEWAY=provider
DEFAULT_EXTENSION=1001
```

### Multi-provider

Разные провайдеры для разных направлений:

```bash
FS_DOMAIN=pbx.company.com
EXTERNAL_SIP_IP=203.0.113.100
EXTERNAL_RTP_IP=203.0.113.100
USERS=user1:Pass1:1001,user2:Pass2:1002
GATEWAYS=provider_de:sip.de.com:5060:user_de:pass_de:true:udp,provider_us:sip.us.com:5060:user_us:pass_us:true:udp
OUTBOUND_ROUTES=^\+49.*:provider_de,^\+1.*:provider_us
INBOUND_ROUTES=+4930111111:1001,+4930222222:1002
```

### SIP Trunk (без auth)

IP-based trunk:

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

## ✅ Проверка

### В Coolify Terminal

```bash
# Статус FreeSWITCH
fs_cli -x "status"

# Статус профилей (должны быть UP)
fs_cli -x "sofia status"

# Статус гатвеев (должны быть REGED)
fs_cli -x "sofia status gateway"

# Зарегистрированные пользователи
fs_cli -x "show registrations"

# Активные звонки
fs_cli -x "show channels"
```

### Настройка SIP клиента

```
Сервер: your EXTERNAL_SIP_IP
Порт: 5060
Username: alice (из USERS)
Password: SecretPass123
Domain: FS_DOMAIN (или пустое)
Transport: UDP
```

---

## 🔧 Troubleshooting

### Gateway не регистрируется

```bash
fs_cli -x "sofia status gateway provider"
```

**Решения:**
1. Проверьте credentials в `GATEWAYS`
2. Проверьте firewall открыт для UDP 5060, 5080
3. Включите debug: `SIP_DEBUG=9` в ENV

### Пользователи не могут регистрироваться

1. `EXTERNAL_SIP_IP` должен быть **публичный IP** сервера
2. Firewall открыт для UDP 5060
3. Проверьте пароли в `USERS`

### Нет звука

1. `EXTERNAL_RTP_IP` = публичный IP
2. Firewall открыт для UDP **16384-32768**
3. `network_mode: host` используется (уже настроено)

**Полное руководство:** [COOLIFY.md](COOLIFY.md#troubleshooting)

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────┐
│       FreeSWITCH Server             │
│                                     │
│  Internal Profile (5060)            │
│  └─ Users (auth required)           │
│                                     │
│  External Profile (5080)            │
│  └─ Gateways (no auth)              │
│                                     │
│  Outbound: User → Gateway → Provider│
│  Inbound:  Provider → Gateway → User│
└─────────────────────────────────────┘
```

---

## 📋 Файлы проекта

### Для Coolify:
- `docker-compose.coolify.yml` - Главный файл для Coolify
- `Dockerfile.coolify` - Dockerfile (альтернатива)
- `.env.example` - Примеры ENV переменных

### Для production:
- `docker-compose.production.yml` - Production Docker Compose
- `Dockerfile.production` - Production Dockerfile
- `install.sh` - Установка на Linux
- `provision.sh` - Генерация конфигурации
- `docker-entrypoint.sh` - Docker entrypoint

### Документация:
- `README.md` - Этот файл
- `COOLIFY_QUICKSTART.md` - Быстрый старт Coolify
- `COOLIFY.md` - Полное руководство Coolify
- `QUICKSTART.md` - Быстрый старт Docker/Linux
- `DEPLOYMENT.md` - Детальное руководство
- `README.production.md` - Полная техническая документация
- `SUMMARY.md` - Итоговая сводка

---

## ✨ Особенности

- ✅ Официальная установка FreeSWITCH из SignalWire
- ✅ Без demo/example конфигураций
- ✅ 100% автоматизация через ENV
- ✅ Multiple users (password + IP-based)
- ✅ Multiple gateways/providers
- ✅ Гибкая маршрутизация inbound/outbound
- ✅ NAT traversal
- ✅ **Coolify-ready за 2 минуты**
- ✅ Production-ready
- ✅ Docker, Kubernetes, Bare Metal

---

## 📝 Production Checklist

- [ ] `EXTERNAL_SIP_IP` = публичный IP сервера
- [ ] `EXTERNAL_RTP_IP` = публичный IP сервера
- [ ] Сильные пароли в `USERS`
- [ ] Firewall открыт: 5060, 5080, 16384-32768 UDP
- [ ] Gateway credentials правильные
- [ ] Протестированы inbound calls
- [ ] Протестированы outbound calls
- [ ] Протестирован звук
- [ ] Health check работает
- [ ] Backup volume настроен

---

## 🤝 Support

- **Issues:** [GitHub Issues](https://github.com/insidedynamic-de/sip_wrapper/issues)
- **Docs:** [COOLIFY.md](COOLIFY.md) | [DEPLOYMENT.md](DEPLOYMENT.md)
- **FreeSWITCH:** https://freeswitch.org

---

## 📄 License

Provided as-is for production use.

---

**Made for DevOps/VoIP Engineers** 🚀 | Deploy to Coolify in 2 minutes!
