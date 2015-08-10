### BEGIN INIT INFO
# Provides:          scriptname
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Start daemon at boot time
# Description:       Enable service provided by daemon.
### END INIT INFO

#!/bin/sh
#echo "Set the hostname"
ip=$(hostname -I)
#echo "$ip"
sudo hostnamectl set-hostname $ip

#echo "change the /etc/hostname"
sudo >/etc/hostname
sudo echo $ip > /etc/hostname

#echo "change the /etc/hosts"
sed -i "s/127.0.0.1/& $ip /" /etc/hosts

#echo "Set SELinux to Permissive"
sudo setenforce Permissive

#echo "Stop the firewall"
sudo ufw disable

#echo "Run the chef client, this is first run"
sudo chef-client
~
