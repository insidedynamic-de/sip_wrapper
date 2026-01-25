FROM dheaps/freeswitch:latest

# Try both Alpine and Debian package managers for git
RUN apk add --no-cache git || (apt-get update && apt-get install -y git)

WORKDIR /app

# Download entrypoint.sh and templates/ from GitHub
RUN curl -fsSL https://raw.githubusercontent.com/insidedynamic-de/sip_wrapper/main/entrypoint.sh -o /entrypoint.sh && \
    chmod +x /entrypoint.sh && \
    git clone --depth=1 https://github.com/insidedynamic-de/sip_wrapper.git /tmp/sip_wrapper && \
    cp -r /tmp/sip_wrapper/templates /templates

CMD ["/entrypoint.sh"]
