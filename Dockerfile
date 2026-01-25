FROM debian:stable-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      curl ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Download docker-compose.yml from GitHub
ARG COMPOSE_URL=https://raw.githubusercontent.com/insidedynamic-de/sip_wrapper/docker-compose.yml
RUN curl -fsSL "$COMPOSE_URL" -o docker-compose.yml

CMD ["cat", "docker-compose.yml"]
