# Setting up a new Pi

1. Prepare the OS using the [Raspberry Pi imaging tool](https://www.raspberrypi.com/software/). In the process you should configure
    1. Your username
    2. The hostname
    3. WiFi unless you connect via ethernet
    4. SSH key so that you can access the Pi without a monitor
2. Add the Pi the SSH config 
    1. Locally: `~/.ssh/config`
    ```
    Host <hostname>
      HostName <hostname>.local
      ForwardAgent yes
      User <username>
    ```
    2. To the [CI config](../.github/workflows/run_ansible.yaml)
    ```
    Host <hostname>
      HostName localhost
      Port <ssh-port>
      ProxyJump relay
      User ${{ secrets.RELAY_USER }}
      ForwardAgent yes
    ```
3. After booting the PI, SSH into the Pi with `ssh <hostname>`
    1. Generate a new set of SSH keys
    2. Add the public key to the relay server
    3. Add the GitHub public ssh key to `~/.ssh/authorized_keys` to authorize the CI pipeline
4. Add the hostname to the [inventory](./ansible/inventory.yaml)
5. Manually deploy the reverse SSH tunnel to only this host with ` RELAY_HOST=<relay-ip> SSH_PORT=<ssh-port> SERVER_PORT=<server-port> uv run ansible-playbook -i ./ansible/inventory.yaml -l <hostname> ./ansible/playbooks/reverse_ssh_tunnel.yaml`
6. Now you can either install the camera service and the crontab by following the instructions in the [README](./README.md)
