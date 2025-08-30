# Deployment

[Ansible](https://docs.ansible.com/) is used for deploying code to the relay and Raspberry pis. 

## Installation

The setup assumes that you have the hosts `relay` and `birdhouse` configured in your `~/.ssh/config`. Like

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
```

To test the connection to the hosts run

```bash
uv run ansible all -m ping  -i ansible/inventory.yaml
```


## Deploy

### Relay
```bash
uv run ansible-playbook -i ansible/inventory.yaml ansible/playbooks/relay.yaml
```

### Pi

#### Camera server
```bash
uv run ansible-playbook -i ansible/inventory.yaml ansible/playbooks/camera_server.yaml
```

#### Reverse ssh tunnel
```bash
RELAY_HOST=<relay-host> uv run ansible-playbook -i ansible/inventory.yaml ansible/playbooks/reverse_ssh_tunnel.yaml
```