# Relay

Relays http requests to registered devices

## Run

```bash
uv run fastapi run main.py --port $PORT
```

## HTTPS

Use e.g. [Caddy](https://caddyserver.com/) to manage certificates and forward HTTPS requests to the relay. 

### Setup

1. [Install](https://caddyserver.com/) Caddy
2. Install configuration file: `mv Caddyfile /etc/caddy/`
3. Add the environment variables
    - `DOMAIN`: domain name for the host machine
    - `PORT`: local port of the relay server 

    to the file `/etc/caddy/.env` and run `sudo systemctl edit caddy` and add the line
    ```
    [Service]
    EnvironmentFile=/etc/caddy/.env
    ```
    to add the variables to the service environment
4. Enable Caddy on boot: `sydo systemctl enable caddy`
5. Start Caddy: `sudo systemctl start caddy`
