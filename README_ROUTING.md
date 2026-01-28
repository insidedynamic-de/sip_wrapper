# FreeSWITCH Advanced Routing Configuration

Полное руководство по настройке маршрутизации и Caller ID в FreeSWITCH.

---

## Содержание

1. [Базовая конфигурация](#базовая-конфигурация)
2. [Per-User Caller ID](#per-user-caller-id)
3. [Outbound Routing](#outbound-routing)
4. [Inbound Routing](#inbound-routing)
5. [Примеры конфигураций](#примеры-конфигураций)

---

## Базовая конфигурация

### Обязательные параметры

```bash
FS_DOMAIN=apps.linkify.cloud
EXTERNAL_SIP_IP=46.224.205.100
EXTERNAL_RTP_IP=46.224.205.100
```

---

## Per-User Caller ID

### 1. Authenticated Users (USERS)

**Формат:** `username:password:extension:caller_id`

**Caller ID опциональный** - если не указан, используется `OUTBOUND_CALLER_ID` или extension.

```bash
# Пример: один пользователь с Caller ID
USERS=alice:SecretPass:1001:+4932221803986

# Пример: несколько пользователей с разными Caller ID
USERS=alice:SecretPass:1001:+4932221803986,bob:Pass456:1002:+4932221803987

# Пример: без Caller ID (будет использован OUTBOUND_CALLER_ID или extension)
USERS=alice:SecretPass:1001,bob:Pass456:1002
```

**Что это даёт:**
- Когда `alice` делает исходящий звонок, получатель видит номер `+4932221803986`
- Когда `bob` делает исходящий звонок, получатель видит номер `+4932221803987`

---

### 2. ACL Users (IP-based, без пароля)

**Формат:** `username:ip_address:extension:caller_id`

**Caller ID опциональный** - если не указан, используется `OUTBOUND_CALLER_ID` или extension.

```bash
# Пример: VAPI с разными Caller ID
ACL_USERS=vapi1:34.213.129.25:9000:+4932221803986,vapi2:44.238.177.138:9000:+4932221803987,vapi3:44.229.228.186:9000:+4932221803988

# Пример: без Caller ID
ACL_USERS=vapi1:34.213.129.25:9000
```

**Что это даёт:**
- Когда `vapi1` (IP 34.213.129.25) делает исходящий звонок, получатель видит `+4932221803986`
- Когда `vapi2` (IP 44.238.177.138) делает исходящий звонок, получатель видит `+4932221803987`
- VAPI не нужен пароль - авторизация по IP

---

### 3. Global Outbound Caller ID (fallback)

```bash
# Если у пользователя не указан свой Caller ID, используется этот
OUTBOUND_CALLER_ID=+4932221803986
```

**Приоритет Caller ID:**
1. **User/ACL User Caller ID** (самый высокий)
2. **OUTBOUND_CALLER_ID** (fallback)
3. **Extension** (если ничего не указано)

---

## Outbound Routing

### 1. Simple Outbound (DEFAULT_GATEWAY)

Все исходящие звонки идут через один gateway:

```bash
DEFAULT_GATEWAY=provider
```

**Call flow:**
```
User/VAPI → FreeSWITCH → provider gateway → Destination
```

---

### 2. Pattern-based Outbound Routing (OUTBOUND_ROUTES)

Маршрутизация по **номеру назначения** (не по пользователю):

**Формат:** `pattern:gateway:prepend:strip`

```bash
# Пример: немецкие номера через provider_de, американские через provider_us
OUTBOUND_ROUTES=^\+49.*:provider_de,^\+1.*:provider_us

# Пример: international через provider1, national через provider2
OUTBOUND_ROUTES=^00.*:provider1,^0[1-9].*:provider2
```

**Важно:** Это маршрутизация по **номеру назначения**, а не по **источнику звонка**.

---

### 3. User-based Outbound Routing ✅ РЕАЛИЗОВАНО

Маршрутизация по **источнику звонка** (кто звонит):

**Формат:** `username:gateway,username2:gateway2`

```bash
# Пример: alice через provider1, bob через provider2
OUTBOUND_USER_ROUTES=alice:provider1,bob:provider2

# Пример: alice и VAPI через разные gateways
OUTBOUND_USER_ROUTES=alice:provider1,vapi1:provider2,vapi2:provider2,vapi3:provider2
```

**Что это даёт:**
- `alice` звонит → через provider1
- `bob` звонит → через provider2
- `vapi1`, `vapi2`, `vapi3` звонят → через provider2
- Если пользователь не в списке → используется DEFAULT_GATEWAY

**Приоритет:**
1. **OUTBOUND_USER_ROUTES** (самый высокий) - проверяется первым
2. **OUTBOUND_ROUTES** (средний) - проверяется если user routing не сработал
3. **DEFAULT_GATEWAY** (fallback) - если ничего не подошло

---

## Inbound Routing

### 1. Simple Inbound (DEFAULT_EXTENSION)

Все входящие звонки идут на один extension:

```bash
DEFAULT_EXTENSION=1001
```

**Call flow:**
```
Provider → FreeSWITCH → extension 1001 (alice)
```

---

### 2. Inbound to Gateway

Все входящие звонки перенаправляются на gateway (например VAPI):

```bash
DEFAULT_EXTENSION=gateway@vapi
```

**Call flow:**
```
Provider → FreeSWITCH → VAPI gateway (AI обрабатывает)
```

---

### 3. DID-based Inbound Routing (INBOUND_ROUTES)

Маршрутизация по **DID** (номер, на который позвонили):

**Формат:** `DID:extension` или `DID:gateway@gateway_name`

```bash
# Пример: разные DID на разные extensions
INBOUND_ROUTES=+4932221803986:1001,+4932221803987:1002,*:1001

# Пример: один DID на VAPI, остальные на alice
INBOUND_ROUTES=+4932221803986:gateway@vapi,*:1001

# Пример: селективная маршрутизация
INBOUND_ROUTES=+4932221803986:gateway@vapi,+4932221803987:1001,+4932221803988:1002,*:1001
```

**Что означает:**
- Звонок на `+4932221803986` → VAPI (AI)
- Звонок на `+4932221803987` → alice (extension 1001)
- Звонок на `+4932221803988` → bob (extension 1002)
- Все остальные (`*`) → alice

---

### 4. Gateway-based Inbound Routing (будущая фича)

**Пока не реализовано.** Планируется:

```bash
# Формат: gateway:extension
INBOUND_GATEWAY_ROUTES=provider1:1001,provider2:gateway@vapi
```

**Что это даст:**
- Звонки от provider1 → alice (extension 1001)
- Звонки от provider2 → VAPI gateway

---

## Примеры конфигураций

### Пример 1: Простой офис

**Сценарий:** Два пользователя, один provider, входящие на alice.

```bash
FS_DOMAIN=apps.linkify.cloud
EXTERNAL_SIP_IP=46.224.205.100
EXTERNAL_RTP_IP=46.224.205.100

# Users с Caller ID
USERS=alice:SecretPass:1001:+4932221803986,bob:Pass456:1002:+4932221803987

# Gateway
GATEWAYS=provider:fpbx.de:5060:777z9uovpu:4UMtPyXw8Qss:true:udp

# Routing
DEFAULT_GATEWAY=provider
DEFAULT_EXTENSION=1001

# Fallback Caller ID
OUTBOUND_CALLER_ID=+4932221803986
```

**Call flow:**
- **Outbound:** alice/bob → provider → destination (Caller ID: свой номер)
- **Inbound:** provider → alice (extension 1001)

---

### Пример 2: Provider + VAPI (AI)

**Сценарий:** Alice + VAPI, входящие на VAPI (AI обрабатывает).

```bash
FS_DOMAIN=apps.linkify.cloud
EXTERNAL_SIP_IP=46.224.205.100
EXTERNAL_RTP_IP=46.224.205.100

# Users
USERS=alice:SecretPass:1001:+4932221803986

# ACL Users (VAPI, без пароля, по IP)
ACL_USERS=vapi1:34.213.129.25:9000:+4932221803986,vapi2:44.238.177.138:9000:+4932221803987,vapi3:44.229.228.186:9000:+4932221803988

# Gateways: provider + VAPI
GATEWAYS=provider:fpbx.de:5060:777z9uovpu:4UMtPyXw8Qss:true:udp,vapi:sip.vapi.ai:5060:::false:udp

# Routing
DEFAULT_GATEWAY=provider          # Все outbound через provider
DEFAULT_EXTENSION=gateway@vapi    # Все inbound на VAPI (AI)

# Fallback Caller ID
OUTBOUND_CALLER_ID=+4932221803986
```

**Call flow:**
- **Outbound:** alice/VAPI → provider → destination
- **Inbound:** provider → VAPI (AI обрабатывает звонки)

---

### Пример 3: Селективная маршрутизация

**Сценарий:** Разные DID на разные destinations.

```bash
FS_DOMAIN=apps.linkify.cloud
EXTERNAL_SIP_IP=46.224.205.100
EXTERNAL_RTP_IP=46.224.205.100

# Users
USERS=alice:SecretPass:1001:+4932221803986,bob:Pass456:1002:+4932221803987

# ACL Users (VAPI)
ACL_USERS=vapi1:34.213.129.25:9000:+4932221803988

# Gateways
GATEWAYS=provider:fpbx.de:5060:777z9uovpu:4UMtPyXw8Qss:true:udp,vapi:sip.vapi.ai:5060:::false:udp

# Routing
DEFAULT_GATEWAY=provider

# Inbound routing по DID
INBOUND_ROUTES=+4932221803986:gateway@vapi,+4932221803987:1001,+4932221803988:1002,*:1001

# Fallback Caller ID
OUTBOUND_CALLER_ID=+4932221803986
```

**Call flow:**
- **Outbound:** alice/bob/VAPI → provider → destination
- **Inbound:**
  - `+4932221803986` → VAPI (AI)
  - `+4932221803987` → alice (extension 1001)
  - `+4932221803988` → bob (extension 1002)
  - Все остальные → alice

---

### Пример 4: Multiple Providers

**Сценарий:** Несколько providers, маршрутизация по направлению.

```bash
FS_DOMAIN=apps.linkify.cloud
EXTERNAL_SIP_IP=46.224.205.100
EXTERNAL_RTP_IP=46.224.205.100

# Users
USERS=alice:SecretPass:1001:+4932221803986

# Gateways
GATEWAYS=provider_de:fpbx.de:5060:user1:pass1:true:udp,provider_us:sip.us.com:5060:user2:pass2:true:udp

# Outbound routing по номеру
OUTBOUND_ROUTES=^\+49.*:provider_de,^\+1.*:provider_us

# Fallback
DEFAULT_GATEWAY=provider_de

# Inbound
DEFAULT_EXTENSION=1001
```

**Call flow:**
- **Outbound:**
  - Номера `+49...` → через provider_de
  - Номера `+1...` → через provider_us
  - Все остальные → через provider_de (fallback)
- **Inbound:** provider_de/provider_us → alice

---

### Пример 5: User-based Routing (alice + bob через разные providers)

**Сценарий:** Alice звонит через provider1, bob звонит через provider2.

```bash
FS_DOMAIN=apps.linkify.cloud
EXTERNAL_SIP_IP=46.224.205.100
EXTERNAL_RTP_IP=46.224.205.100

# Users с Caller ID
USERS=alice:SecretPass:1001:+4932221803986,bob:Pass456:1002:+4932221803987

# Gateways
GATEWAYS=provider1:fpbx.de:5060:user1:pass1:true:udp,provider2:other-provider.com:5060:user2:pass2:true:udp

# User-based outbound routing
OUTBOUND_USER_ROUTES=alice:provider1,bob:provider2

# Fallback (если кто-то не в списке)
DEFAULT_GATEWAY=provider1

# Inbound
DEFAULT_EXTENSION=1001

# Fallback Caller ID
OUTBOUND_CALLER_ID=+4932221803986
```

**Call flow:**
- **Outbound:**
  - `alice` звонит → через provider1 (Caller ID: +4932221803986)
  - `bob` звонит → через provider2 (Caller ID: +4932221803987)
  - Другие пользователи → через provider1 (fallback)
- **Inbound:** provider1/provider2 → alice (extension 1001)

---

### Пример 6: VAPI через отдельный provider

**Сценарий:** Alice через provider1, все VAPI через provider2.

```bash
FS_DOMAIN=apps.linkify.cloud
EXTERNAL_SIP_IP=46.224.205.100
EXTERNAL_RTP_IP=46.224.205.100

# Users
USERS=alice:SecretPass:1001:+4932221803986

# ACL Users (VAPI)
ACL_USERS=vapi1:34.213.129.25:9000:+4932221803987,vapi2:44.238.177.138:9000:+4932221803988,vapi3:44.229.228.186:9000:+4932221803989

# Gateways
GATEWAYS=provider1:fpbx.de:5060:user1:pass1:true:udp,provider2:vapi-provider.com:5060:user2:pass2:true:udp

# User-based outbound routing
OUTBOUND_USER_ROUTES=alice:provider1,vapi1:provider2,vapi2:provider2,vapi3:provider2

# Fallback
DEFAULT_GATEWAY=provider1

# Inbound
DEFAULT_EXTENSION=1001

# Fallback Caller ID
OUTBOUND_CALLER_ID=+4932221803986
```

**Call flow:**
- **Outbound:**
  - `alice` → provider1 (Caller ID: +4932221803986)
  - `vapi1` → provider2 (Caller ID: +4932221803987)
  - `vapi2` → provider2 (Caller ID: +4932221803988)
  - `vapi3` → provider2 (Caller ID: +4932221803989)
- **Inbound:** provider1/provider2 → alice

---

## Примечания о Provider

### Caller ID Support

**Некоторые providers:**

- ✅ **Разрешают любой Caller ID** - FreeSWITCH установит ваш Caller ID
- ⚠️ **Разрешают только зарегистрированные номера** - FreeSWITCH попробует установить, но provider может заменить на зарегистрированный
- ❌ **Не поддерживают Caller ID** - provider всегда установит свой номер

**Рекомендация:** Проверьте документацию вашего provider или протестируйте звонки.

---

## Deployment

### 1. Обновите ENV в Coolify

Добавьте новые параметры в Coolify UI → Environment Variables.

### 2. Restart FreeSWITCH

```bash
# В Coolify UI: Restart service
```

Новый `provision.sh` будет загружен с `--no-cache` и применит новую конфигурацию.

### 3. Проверка

```bash
# Проверьте users
fs_cli -x "list_users"

# Проверьте gateways
fs_cli -x "sofia status gateway"

# Проверьте переменные пользователя
fs_cli -x "user_data alice var outbound_caller_id_number"
```

---

## Troubleshooting

### Caller ID не установлен

**Проблема:** Получатель видит не тот номер.

**Решение:**
1. Проверьте, что Caller ID указан в ENV
2. Проверьте переменные пользователя: `fs_cli -x "user_data alice var outbound_caller_id_number"`
3. Проверьте поддержку provider (см. [Примечания о Provider](#примечания-о-provider))

### Входящие звонки не работают

**Проблема:** Входящие звонки не доходят до extension/gateway.

**Решение:**
1. Проверьте логи: `fs_cli -x "console loglevel 7"`
2. Проверьте `DEFAULT_EXTENSION` или `INBOUND_ROUTES`
3. Проверьте dialplan: `fs_cli -x "xml_locate dialplan"`

### Исходящие звонки не работают

**Проблема:** Исходящие звонки не идут через нужный gateway.

**Решение:**
1. Проверьте `DEFAULT_GATEWAY` или `OUTBOUND_ROUTES`
2. Проверьте статус gateway: `fs_cli -x "sofia status gateway"`
3. Проверьте dialplan: `fs_cli -x "xml_locate dialplan"`

---

## Реализованные фичи ✅

1. **Per-User Caller ID** - каждый пользователь может иметь свой Caller ID
2. **User-based Outbound Routing** - маршрутизация по источнику звонка (кто звонит)
3. **DID-based Inbound Routing** - маршрутизация входящих по номеру
4. **Pattern-based Outbound Routing** - маршрутизация по паттернам номера
5. **ACL Users** - пользователи без пароля (по IP)

## Планируемые фичи

1. **Gateway-based Inbound Routing** - автоматическая маршрутизация по source gateway
   ```bash
   INBOUND_GATEWAY_ROUTES=provider1:1001,provider2:gateway@vapi
   ```

2. **Time-based Routing** - маршрутизация по времени суток
   ```bash
   ROUTING_SCHEDULE=working_hours:08:00-18:00:alice,after_hours:*:gateway@vapi
   ```

3. **Load Balancing** - распределение нагрузки между несколькими gateways
   ```bash
   OUTBOUND_LOAD_BALANCE=provider1:provider2:provider3
   ```

---

## Поддержка

- **GitHub Issues:** https://github.com/insidedynamic-de/sip_wrapper/issues
- **Документация:** См. другие README файлы в репозитории

---

**Версия:** 1.1.0
**Дата:** 2026-01-28
