# SIP Wrapper - Multi-Provider Telefonie Bridge

> Verbindet KI-Telefonie mit deutschen Providern und Telefonanlagen

---

## Das Problem

Moderne KI-Telefonie-Plattformen (VAPI, Retell, Bland AI) haben Schwierigkeiten, sich direkt mit deutschen SIP-Providern und Telefonanlagen zu verbinden:

- Authentifizierungsprobleme
- Inkompatible Codecs
- NAT/Firewall-Probleme
- Fehlende deutsche Rufnummern

**Resultat:** Stunden an Debugging, instabile Verbindungen, keine Anrufe.

---

## Die Lösung

**SIP Wrapper** ist eine Multi-Tenant SIP Bridge, die verschiedene Telefonie-Welten verbindet.

```
┌─────────────────┐                           ┌─────────────────┐
│   KI-Telefonie  │                           │  Deutsche       │
│                 │                           │  Provider       │
│  - VAPI         │      ┌─────────────┐      │                 │
│  - Retell       │ ───► │ SIP Wrapper │ ───► │  - Placetel     │
│  - Bland AI     │      └─────────────┘      │  - Sipgate      │
│  - Custom       │                           │  - 3CX          │
└─────────────────┘                           │  - Fritzbox     │
                                              └─────────────────┘
```

---

## Vorteile

**Einfache Konfiguration**
- Komplette Konfiguration über Umgebungsvariablen
- Keine XML-Dateien editieren
- Deploy in 2 Minuten

**Ressourcenschonend**
- Minimaler Speicherverbrauch (~50MB RAM)
- Läuft auf kleinen VPS-Servern
- Keine Datenbank erforderlich

**Multi-Tenant**
- Beliebig viele Benutzer
- Beliebig viele Provider gleichzeitig
- Flexibles Routing pro Benutzer

**Produktionsreif**
- Stabile Verbindungen
- Automatische Wiederverbindung
- NAT-Traversal integriert

---

## Getestete Integrationen

### SIP Provider

| Provider | Typ | Status |
|----------|-----|--------|
| **Placetel** | SIP Trunk | Getestet |
| **Placetel** | Nebenstelle | Getestet |
| **Sipgate** | SIP Trunk | Getestet |

### Telefonanlagen

| Anlage | Anbindung | Status |
|--------|-----------|--------|
| **Fritzbox** | Vodafone Cable Business | Getestet |
| **3CX** | SBC Gateway | Getestet |

### KI-Plattformen

| Plattform | Typ | Status |
|-----------|-----|--------|
| **VAPI** | IP-basiert (ACL) | Getestet |
| **Retell** | IP-basiert (ACL) | Kompatibel |
| **Bland AI** | IP-basiert (ACL) | Kompatibel |

---

## Schnellstart

### 1. Deploy (Coolify)

```bash
Repository: https://github.com/insidedynamic-de/sip_wrapper.git
Docker Compose: docker-compose.coolify-prebuilt.yml
```

### 2. Konfiguration

```bash
# Server
FS_DOMAIN=sip.yourdomain.com
EXTERNAL_SIP_IP=your-server-ip
EXTERNAL_RTP_IP=your-server-ip

# Benutzer
USERS=alice:password:1001,bob:password:1002

# Provider
GATEWAYS=placetel:sip.placetel.de:5060:user:pass:true:udp

# Routing
DEFAULT_GATEWAY=placetel
DEFAULT_EXTENSION=1001
```

### 3. Fertig

Anrufe funktionieren sofort nach dem Deploy.

---

## Dokumentation

| Datei | Beschreibung |
|-------|--------------|
| [COOLIFY_QUICKSTART.md](COOLIFY_QUICKSTART.md) | Schnellstart für Coolify |
| [README_ROUTING.md](README_ROUTING.md) | Routing-Konfiguration |
| [.env.template](.env.template) | Alle Konfigurationsoptionen |

---

## Anwendungsfälle

### KI-Callcenter mit deutscher Rufnummer

VAPI-Agent nimmt Anrufe auf deutscher Rufnummer entgegen:

```bash
ACL_USERS=vapi:34.213.129.25:9000:+4930123456
GATEWAYS=placetel:sip.placetel.de:5060:user:pass:true:udp
INBOUND_ROUTES=+4930123456:gateway@vapi
```

### Multi-Provider Routing

Verschiedene Benutzer nutzen verschiedene Provider:

```bash
USERS=alice:pass:1001,bob:pass:1002
GATEWAYS=provider1:...,provider2:...
OUTBOUND_USER_ROUTES=alice:provider1,bob:provider2
```

### Fritzbox als Gateway

Fritzbox-Nebenstelle für Outbound-Calls:

```bash
GATEWAYS=fritzbox:fritz.box:5060:user:pass:true:udp
DEFAULT_GATEWAY=fritzbox
```

---

## Support

- **GitHub Issues:** [github.com/insidedynamic-de/sip_wrapper/issues](https://github.com/insidedynamic-de/sip_wrapper/issues)
- **Dokumentation:** Siehe Dateien im Repository

---

**Verbindet Telefonie-Welten** | Made in Germany
