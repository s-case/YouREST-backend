######################################
##        Initialize GIT            ##
######################################

mkdir /home/ubuntu/YouREST
cd /home/ubuntu/YouREST
git init --bare
sudo chown -R ubuntu:ubuntu /home/ubuntu/YouREST
cd /home/ubuntu/YouREST/hooks

######################################
##    Create post-receive hook      ##
######################################

cat > post-receive << EOF1
#!/bin/bash

######################################
##    Configure the PostgreSQL"     ##
######################################
echo
echo "****************** CONFIGURING THE VM  *********************"
echo "Configuing the PostgreSQL - password"
# Generate 1 password of length 8 randomly
PASSWD=\$(pwgen 8 1)
bash_content=\$(sudo cat /home/ubuntu/.bashrc)
echo -en "export PASSWD=\$PASSWD\n$content" >/home/ubuntu/.bashrc
source ~/.bashrc
echo \$PASSWD 
#sudo -u postgres psql --command '\\password \$PASSWD'
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD '\$PASSWD';"
echo
echo "Configuing the PostgreSQL - port"
sudo sed -i "s/port = 5432/port = 3127/" /etc/postgresql/9.4/main/postgresql.conf
echo
echo "restarting PostgresSQL and starting jetty"
sudo /etc/init.d/postgresql restart

######################################
##    Compile the code              ##
######################################
echo
echo "Building the war file... please wait"
sudo mkdir /home/ubuntu/YouREST-local-repo
cd /home/ubuntu/YouREST-local-repo
sudo git clone /home/ubuntu/YouREST
WEB_APP=\$(cd /home/ubuntu/YouREST-local-repo/YouREST && ls -d *)
sudo chown -R ubuntu:ubuntu /home/ubuntu/YouREST-local-repo
echo \$WEB_APP
cd /home/ubuntu/YouREST-local-repo/YouREST/\$WEB_APP
current=\$(pwd)
echo \$current
mvn package

######################################
##    Move the war file to jetty    ##
######################################
echo
echo "Moving the war file to jetty webapps"
WAR_FILE=\$(cd /home/ubuntu/YouREST-local-repo/YouREST/\$WEB_APP/target && (ls -d * | grep .war))
echo \$WAR_FILE
sudo mv /home/ubuntu/YouREST-local-repo/YouREST/\$WEB_APP/target/\$WAR_FILE /opt/jetty/webapps

######################################
##        Start jetty               ##
######################################
cd /opt/jetty
sudo java -jar start.jar

EOF1

chmod +x /home/ubuntu/YouREST/hooks/post-receive
