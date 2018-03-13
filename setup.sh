#!/bin/bash

if [[ ! $EUID -eq 0 ]]; then
    echo "must be run as root."
    exit 1
fi

if [[ -z $1 ]]; then
    echo "usage: $0 USER."
    exit 1
fi

user=$1
pass=$1
install_dir=/opt/vbg

apt-get install -y gcc make libx11-dev libxtst-dev python3-xlib wmctrl git xauth
useradd --shell /bin/sh -m ${user}
#touch /home/${user}/.Xauthority
chown ${user}:${user} /home/${user}/.Xauthority
echo "${user}:${pass}" | chpasswd

cat << EOF >> /etc/ssh/sshd_config
Match User ${user}
        X11Forwarding yes
        PermitEmptyPasswords yes
        PasswordAuthentication yes
        AllowTcpForwarding no
        PermitTTY no
        ForceCommand cd ${install_dir} && ./vbg.py -m cmd >>/tmp/${user}.log 2>>/tmp/${user}.log; exit 1
EOF
service sshd restart

git clone https://github.com/xfee/vbg ${install_dir}
chmod o+r -R ${install_dir}
cd ${install_dir} && make
