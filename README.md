# sip_wrapper

`sip_wrapper` is a minimal, containerized FreeSWITCH setup designed to act as a transparent SIP relay.

All incoming and outgoing calls are forwarded directly to a single SIP provider without any number normalization or routing logic.

The project is fully environment-driven and intended for automated deployment using Docker, Coolify, or GitHub Actions.

---

## Features

- FreeSWITCH running in Docker
- Single SIP user (default: 1001)
- All inbound calls → SIP provider
- All outbound calls → SIP provider
- Phone numbers are passed **exactly as received**
  - +49176...
  - 01761...
  - 0049176...
- No dialplan logic, no prefix rewriting
- Configuration generated at container startup from environment variables
- Secrets-safe (no credentials committed to Git)

---

## Use cases

- SIP trunk wrapper
- Voice API (VAPI, bots, AI agents)
- Call forwarding / relay
- Testing SIP providers
- Simple PBX-less SIP bridge

---

## Configuration

All configuration is done via environment variables.

Example:

```env
FS_USER=1001
FS_PASS=pass1001

PROVIDER_NAME=placetel
PROVIDER_HOST=fpbx.de
PROVIDER_USER=your_sip_username
PROVIDER_PASS=your_sip_password

EXTERNAL_IP=your.server.ip
SIP_PORT=5080
RTP_START=16384
RTP_END=32768
