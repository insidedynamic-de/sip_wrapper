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

| Pos | Name | Beschreibung | Getestet | Outbound | Inbound |
|-----|------|--------------|:--------:|:--------:|:-------:|
| 1 | **Placetel** SIP Trunk | Business SIP Trunk | ✓ | ✓ | ✓ |
| 2 | **Placetel** Nebenstelle | Cloud PBX Nebenstelle | ✓ | ✓ | ✓ |
| 3 | **Easybell** SIP Trunk | Business SIP Trunk | ✓ | ✓ | ✓ |
| 4 | **Easybell** Nebenstelle | Cloud Nebenstelle | ✓ | ✓ | ✓ |
| 5 | **Sipgate** SIP Trunk | Business SIP Trunk | ✓ | ✓ | ✓ |
| 6 | **Zadarma** SIP Trunk | Internationaler SIP Trunk | ✓ | ✓ | ✓ |
| 7 | **Zadarma** Nebenstelle | Cloud Nebenstelle | ✓ | ✓ | ✓ |
| 8 | **Fritzbox** | Vodafone Cable Business | ✓ | ✓ | ✓ |
| 9 | **3CX** | Cloud / On-Premise PBX | ✓ | ✓ | ✓ |
| 10 | **Agfeo** Cloud | Cloud Telefonanlage | ✗ | - | - |
| 11 | **Agfeo** On-Premise | On-Premise Telefonanlage | ✗ | - | - |
| 12 | **FreePBX** | Open Source PBX | ✗ | - | - |
| 13 | **Starface** | Business PBX | ✗ | - | - |
| 14 | **Asterisk** | Open Source PBX | ✗ | - | - |
| 15 | **Tengo** CentraFlex | Cloud PBX | ✗ | - | - |
| 16 | **Plusnet** SIP Trunk | Business SIP Trunk | ✗ | - | - |
| 17 | **Telekom** DeutschlandLAN | Business SIP Trunk | ✗ | - | - |
| 18 | **Telekom** Company Flex | Cloud PBX | ✗ | - | - |
| 19 | **Telekom** Cloud PBX | Cloud Telefonanlage | ✗ | - | - |
| 20 | **Gamma** (ehem. HFO) | Business SIP Trunk | ✗ | - | - |
| 21 | **Crown** Centrex | Cloud PBX | ✗ | - | - |
| 22 | **NFON** | Cloud PBX | ✗ | - | - |
| 23 | **Fonial** Nebenstelle | Cloud Nebenstelle | ✗ | - | - |
| 24 | **Fonial** SIP Trunk | Business SIP Trunk | ✗ | - | - |

**Ihr System fehlt?** Kontaktieren Sie uns - wir integrieren es.

---

## KI-Plattformen

| Pos | Name | Beschreibung | Getestet | Outbound | Inbound |
|-----|------|--------------|:--------:|:--------:|:-------:|
| 1 | **VAPI** | KI-Telefonie Plattform | ✓ | ✓ | ✓ |
| 2 | **Retell** | KI-Telefonie Plattform | ✓ | ✓ | ✓ |
| 3 | **Bland AI** | KI-Telefonie Plattform | ✓ | ✓ | ✓ |

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
