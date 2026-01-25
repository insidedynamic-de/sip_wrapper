# FreeSWITCH SIP Wrapper (Minimal SIP Relay)

A minimal, production-ready FreeSWITCH SIP relay for forwarding all inbound and outbound calls between a single SIP user and a single SIP provider. No business logic, no web services, no persistent storage.

## Features
- One SIP user (default: 1001)
- All inbound and outbound calls are transparently bridged to a SIP provider
- No number rewriting, no caller ID manipulation
- Configuration-only: all settings via environment variables
- Docker-only, no persistent storage
- No web services, no APIs, no databases
- Suitable for Docker, Coolify, and GitHub Actions deployments

## Environment Variables
See `.env.example` for all required and optional variables:
- `SIP_USER` (default: 1001)
- `SIP_PASSWORD`
- `SIP_DOMAIN`
- `PROVIDER_HOST`
- `PROVIDER_PORT`
- `PROVIDER_USERNAME` (optional)
- `PROVIDER_PASSWORD` (optional)
- `PROVIDER_TRANSPORT` (udp/tcp)
- `EXTERNAL_IP` (optional)

## Usage

### 1. Build the Docker image
```sh
docker build -t sip_wrapper .
```

### 2. Prepare your environment
Copy `.env.example` to `.env` and fill in your credentials and provider info.

### 3. Run with Docker
```sh
docker run --env-file .env --rm sip_wrapper
```

### 4. (Optional) Docker Compose
Create a `docker-compose.yml`:
```yaml
version: '3.8'
services:
  freeswitch:
    build: .
    env_file: .env
    restart: unless-stopped
    ports:
      - "5060:5060/udp"
      - "5060:5060/tcp"
      - "5080:5080/udp"
      - "5080:5080/tcp"
      - "16384-16484:16384-16484/udp"
```
Then run:
```sh
docker compose up
```

## How it works
- All configuration is generated at container startup by `entrypoint.sh` from environment variables.
- No data is persisted between runs.
- Logs are sent to stdout.
- The container fails fast on misconfiguration or if the SIP user/provider is unreachable.

## Dialplan Logic
- **Inbound calls**: Any call received is immediately bridged to the SIP provider (no filtering, no voicemail, no IVR).
- **Outbound calls**: Only calls from the configured SIP user are accepted and immediately bridged to the provider.
- **Phone numbers**: Passed exactly as received (e.g., +49176..., 0176..., 0049176...). No normalization or rewriting.
- **Caller ID**: Passed transparently.
- **Fail fast**: If the user is not registered or the provider is unreachable, the container exits with an error.

## Directory Structure
- `Dockerfile` - Container build
- `entrypoint.sh` - Startup script, generates configs
- `freeswitch/` - Mount point for generated configs
  - `sip_profiles/` - Generated SIP profiles
  - `dialplan/` - Generated dialplan
- `templates/` - XML templates for config generation
- `.env.example` - Example environment file

## Security
- No credentials or sensitive data are stored in the image or repo.
- All secrets are passed via environment variables at runtime.

## Support
This project is intentionally minimal. For issues, open a GitHub issue or PR.
