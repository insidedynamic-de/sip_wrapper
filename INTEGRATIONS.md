# SIP Wrapper - Integrationen

> Verbinden Sie Ihre KI-Telefonie mit der deutschen Telefonie-Infrastruktur

---

## Das Problem

Sie haben eine KI-Telefonie-Lösung (VAPI, Retell, Bland AI) und möchten deutsche Rufnummern nutzen?

**Die Realität:**

- Direkte Verbindung zu deutschen Providern funktioniert nicht
- Stunden an Debugging ohne Ergebnis
- Inkompatible Protokolle und Authentifizierung
- Support-Tickets ohne Lösung
- Projekt verzögert sich um Wochen

**Das Resultat:** Ihre KI kann nicht telefonieren.

---

## Die Lösung

**SIP Wrapper** verbindet Ihre KI-Plattform mit jedem deutschen Provider oder Telefonanlage.

```
    Ihre KI                    SIP Wrapper                  Telefonie
  ┌──────────┐               ┌─────────────┐              ┌──────────┐
  │  VAPI    │               │             │              │ Provider │
  │  Retell  │  ──────────►  │   Bridge    │  ──────────► │ Anlagen  │
  │  Bland   │               │             │              │ Trunks   │
  └──────────┘               └─────────────┘              └──────────┘
       │                            │                           │
  KI spricht                  Übersetzt                   Deutsche
  SIP                         Protokolle                  Rufnummer
```

**In 2 Minuten deployed. Funktioniert sofort.**

---

## Integrationen

| Name | Beschreibung | Getestet | Outbound | Inbound |
|------|--------------|:--------:|:--------:|:-------:|
| **Placetel** SIP Trunk | Business SIP Trunk | ✓ | ✓ | ✓ |
| **Placetel** Nebenstelle | Cloud PBX Nebenstelle | ✓ | ✓ | ✓ |
| **Easybell** SIP Trunk | Business SIP Trunk | ✓ | ✓ | ✓ |
| **Easybell** Nebenstelle | Cloud Nebenstelle | ✓ | ✓ | ✓ |
| **Sipgate** SIP Trunk | Business SIP Trunk | ✓ | ✓ | ✓ |
| **Zadarma** SIP Trunk | Internationaler SIP Trunk | ✓ | ✓ | ✓ |
| **Zadarma** Nebenstelle | Cloud Nebenstelle | ✓ | ✓ | ✓ |
| **Fritzbox** | Vodafone Cable Business | ✓ | ✓ | ✓ |
| **3CX** | Cloud / On-Premise PBX | ✓ | ✓ | ~ |
| **Agfeo** Cloud | Cloud Telefonanlage | ✗ | - | - |
| **Agfeo** On-Premise | On-Premise Telefonanlage | ✗ | - | - |
| **FreePBX** | Open Source PBX | ✗ | - | - |
| **Starface** | Business PBX | ✗ | - | - |
| **Asterisk** | Open Source PBX | ✗ | - | - |
| **Tengo** CentraFlex | Cloud PBX | ✗ | - | - |
| **Plusnet** SIP Trunk | Business SIP Trunk | ✗ | - | - |
| **Telekom** DeutschlandLAN | Business SIP Trunk | ✗ | - | - |
| **Telekom** Company Flex | Cloud PBX | ✗ | - | - |
| **Telekom** Cloud PBX | Cloud Telefonanlage | ✗ | - | - |
| **Gamma** (ehem. HFO) | Business SIP Trunk | ✗ | - | - |
| **Crown** Centrex | Cloud PBX | ✗ | - | - |
| **NFON** | Cloud PBX | ✗ | - | - |
| **Fonial** Nebenstelle | Cloud Nebenstelle | ✗ | - | - |
| **Fonial** SIP Trunk | Business SIP Trunk | ✗ | - | - |

**Legende:** ✓ = Produktiv | ~ = Im Test | ✗ = In Entwicklung | - = Noch nicht getestet

**Ihr System fehlt?** Kontaktieren Sie uns - wir integrieren es.

---

## KI-Plattformen

| Name | Beschreibung | Getestet | Outbound | Inbound |
|------|--------------|:--------:|:--------:|:-------:|
| **VAPI** | KI-Telefonie Plattform | ✓ | ✓ | ✓ |
| **Retell** | KI-Telefonie Plattform | ✓ | ✓ | ✓ |
| **Bland AI** | KI-Telefonie Plattform | ✓ | ✓ | ✓ |

---

## Warum SIP Wrapper?

### Sofort einsatzbereit

- Deploy in 2 Minuten
- Keine komplexe Konfiguration
- Funktioniert out-of-the-box

### Ressourcenschonend

- ~50 MB RAM
- Läuft auf kleinsten Servern
- Keine Datenbank nötig

### Flexibel

- Mehrere Provider gleichzeitig
- Mehrere KI-Plattformen
- Routing nach Benutzer, Rufnummer, Ziel

### Zuverlässig

- Automatische Wiederverbindung
- NAT-Traversal integriert
- Produktionserprobt

---

## Anwendungsbeispiele

### KI-Callcenter

Ihre VAPI-Agenten nehmen Anrufe auf deutschen Rufnummern entgegen:

```
Eingehender Anruf → Deutsche Rufnummer → SIP Wrapper → VAPI Agent
```

### Outbound-Kampagnen

Ihre KI ruft Kunden mit deutscher Caller-ID an:

```
KI startet Anruf → SIP Wrapper → Deutscher Provider → Kunde sieht +49...
```

### Hybrid-Lösung

Manche Anrufe an KI, manche an echte Mitarbeiter:

```
Anruf auf +49 30 123456 → SIP Wrapper → VAPI (KI)
Anruf auf +49 30 123457 → SIP Wrapper → Mitarbeiter-Telefon
```

---

## Nächste Schritte

1. **Repository klonen:** `github.com/insidedynamic-de/sip_wrapper`
2. **In Coolify deployen:** 2 Minuten
3. **Provider konfigurieren:** ENV-Variablen setzen
4. **Telefonieren:** Fertig

---

## Kontakt

- **GitHub:** [github.com/insidedynamic-de/sip_wrapper](https://github.com/insidedynamic-de/sip_wrapper)
- **Issues:** [GitHub Issues](https://github.com/insidedynamic-de/sip_wrapper/issues)

---

**Verbindet Telefonie-Welten** | Made in Germany
