FROM debian:stable-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install FreeSWITCH and dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      freeswitch freeswitch-mod-sofia freeswitch-mod-dialplan-xml freeswitch-lang-en freeswitch-sounds-en-us-callie \
      xmlstarlet curl ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Add entrypoint and config directories
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
COPY templates/ /templates/

VOLUME ["/freeswitch"]

EXPOSE 5060/udp 5060/tcp 5080/udp 5080/tcp 16384-16484/udp

ENTRYPOINT ["/entrypoint.sh"]
