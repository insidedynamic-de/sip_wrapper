# FreeSWITCH SIP Wrapper (Minimal SIP Relay)

A minimal, production-ready FreeSWITCH SIP relay for forwarding all inbound and outbound calls between a single SIP user and a single SIP provider. No business logic, no web services, no persistent storage.

## Features
- One SIP user (example: exampleuser)
- All inbound and outbound calls are transparently bridged to a SIP provider
- No number rewriting, no caller ID manipulation
- Configuration-only: all settings via environment variables
- Docker-only, no persistent storage
- No web services, no APIs, no databases
- Suitable for Docker, Coolify, and GitHub Actions deployments

## Quick Start (Coolify or Docker Compose)

1. **Copy the docker-compose.yml file** to your project or Coolify app.
2. **Edit the environment variables** in the `docker-compose.yml` file to match your SIP credentials and provider details:

```yaml
environment:
  SIP_USER: exampleuser
  SIP_PASSWORD: examplepass
  SIP_DOMAIN: example.sip.domain
  PROVIDER_HOST: example.provider.host
  PROVIDER_PORT: 5060
  PROVIDER_USERNAME: provideruser
  PROVIDER_PASSWORD: providerpass
  PROVIDER_TRANSPORT: udp
  EXTERNAL_IP: example.external.ip
  GITHUB_URL: https://github.com/insidedynamic-de/sip_wrapper
```

3. **Set the correct ports** for SIP and RTP in the `docker-compose.yml` file:
```yaml
ports:
  - "5060:5060/udp"
  - "5080:5080/udp"
  - "16384-32768:16384-32768/udp"
```

4. **Deploy with Coolify** (or locally):
   - In Coolify, create a new Docker Compose app and upload your `docker-compose.yml`.
   - Make sure to set or override environment variables in the Coolify UI if needed.
   - Deploy the app.

5. **Check logs and registration**
   - Use `fs_cli -x "sofia status"` and `fs_cli -x "show registrations"` to verify SIP registration and call routing.

## Environment Variables
- `SIP_USER` — SIP user/extension (e.g., 1001)
- `SIP_PASSWORD` — SIP user password
- `SIP_DOMAIN` — SIP domain or host for user registration
- `PROVIDER_HOST` — SIP provider host
- `PROVIDER_PORT` — SIP provider port (default: 5060)
- `PROVIDER_USERNAME` — Provider username (if required)
- `PROVIDER_PASSWORD` — Provider password (if required)
- `PROVIDER_TRANSPORT` — udp or tcp (default: udp)
- `EXTERNAL_IP` — External IP or hostname for RTP/SIP (e.g., your Coolify app hostname)
- `GITHUB_URL` — (optional) Link to this repository

## Notes
- All configuration is generated at container startup from environment variables.
- No persistent storage is required.
- Logs are sent to stdout.
- The container fails fast on misconfiguration or if the SIP user/provider is unreachable.

## Example docker-compose.yml
```yaml
version: '3.9'
services:
  freeswitch:
    build: .
    container_name: freeswitch
    environment:
      SIP_USER: exampleuser
      SIP_PASSWORD: examplepass
      SIP_DOMAIN: example.sip.domain
      PROVIDER_HOST: example.provider.host
      PROVIDER_PORT: 5060
      PROVIDER_USERNAME: provideruser
      PROVIDER_PASSWORD: providerpass
      PROVIDER_TRANSPORT: udp
      EXTERNAL_IP: example.external.ip
      GITHUB_URL: https://github.com/insidedynamic-de/sip_wrapper
    ports:
      - "5060:5060/udp"
      - "5080:5080/udp"
      - "16384-32768:16384-32768/udp"
    restart: unless-stopped
```

## Security
- No credentials or sensitive data are stored in the image or repo.
- All secrets are passed via environment variables at runtime.

## Support
This project is intentionally minimal. For issues, open a GitHub issue or PR.
