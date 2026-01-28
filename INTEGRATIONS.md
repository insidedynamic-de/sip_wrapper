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

## Bereits verbunden

Diese Systeme wurden erfolgreich getestet und funktionieren:

| System | Status |
|--------|--------|
| **Placetel** SIP Trunk | Produktiv |
| **Placetel** Nebenstelle | Produktiv |
| **Easybell** SIP Trunk | Produktiv |
| **Easybell** Nebenstelle | Produktiv |
| **Sipgate** SIP Trunk | Produktiv |
| **Zadarma** SIP Trunk | Produktiv |
| **Zadarma** Nebenstelle | Produktiv |
| **Fritzbox** (Vodafone Cable Business) | Produktiv |
| **3CX** Cloud / On-Premise | Produktiv |

---

## KI-Plattformen

Folgende KI-Telefonie-Plattformen werden unterstützt:

| Plattform | Anbindung | Status |
|-----------|-----------|--------|
| **VAPI** | IP-basiert (ACL) | Produktiv |
| **Retell** | IP-basiert (ACL) | Produktiv |
| **Bland AI** | IP-basiert (ACL) | Produktiv |

---

## In Entwicklung

An diesen Integrationen arbeiten wir aktuell:

| System | Status |
|--------|--------|
| **Agfeo** Cloud | In Arbeit |
| **Agfeo** On-Premise | In Arbeit |
| **FreePBX** | In Arbeit |
| **Starface** | In Arbeit |
| **Asterisk** | In Arbeit |
| **Tengo** CentraFlex | In Arbeit |
| **Plusnet** SIP Trunk | In Arbeit |
| **Telekom** DeutschlandLAN SIP-Trunk | In Arbeit |
| **Telekom** Company Flex | In Arbeit |
| **Telekom** Cloud PBX | In Arbeit |
| **Gamma Communication** (ehem. HFO Telekom) | In Arbeit |
| **Crown** Centrex | In Arbeit |
| **NFON** Cloud PBX | In Arbeit |
| **Fonial** Nebenstelle | In Arbeit |
| **Fonial** SIP Trunk | In Arbeit |

**Ihr System fehlt?** Kontaktieren Sie uns - wir integrieren es.

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
