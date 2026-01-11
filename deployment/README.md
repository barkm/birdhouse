# Deployment

[Ansible](https://docs.ansible.com/) is used for deploying code to the relay and Raspberry pis. 

## Installation

The setup assumes that you have the hosts configured in your `~/.ssh/config`. Like

```
Host relay
  HostName <relay-ip>
  User <user>
  ForwardAgent yes

Host birdhouse
  HostName localhost
  Port 2222
  User <user>
  ProxyJump <relay-ip>

Host house
  HostName localhost
  Port 2223
  User <user>
  ProxyJump <relay-ip>

Host zero
  HostName localhost
  Port 2224
  User <user>
  ProxyJump <relay-ip>
```

To test the connection to the hosts run

```bash
uv run ansible all -m ping  -i ansible/inventory.yaml
```


## Deploy

### Relay

#### Relay service
```bash
uv run ansible-playbook -i ansible/inventory.yaml ansible/playbooks/relay/relay.yaml
```

#### Caddy
```bash
DOMAIN=<domain> run ansible-playbook -i ansible/inventory.yaml ansible/playbooks/relay/caddy.yaml
```

### Pi

#### Camera server
```bash
uv run ansible-playbook -i ansible/inventory.yaml ansible/playbooks/pi/camera_server.yaml
```

#### Reverse ssh tunnel
```bash
RELAY_HOST=<relay-host> SSH_PORT=<ssh-port> SERVER_PORT=<server-port> uv run ansible-playbook -i ansible/inventory.yaml ansible/playbooks/pi/reverse_ssh_tunnel.yaml
```

#### Crontab
```bash
NAME=<name> SERVER_PORT=<server-port> uv run ansible-playbook -i ansible/inventory.yaml ansible/playbooks/pi/crontab.yaml
```

#### Caddy

If you want to be able to access devices over the local network you need to install a Caddy as an HTTPS server in front of the camera server
```bash
run ansible-playbook -i ansible/inventory.yaml ansible/playbooks/pi/caddy.yaml
```
