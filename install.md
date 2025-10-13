# Close Loop Automation Demo

## Download this repo 

We consider you clone the repo under /var/repo-demo: 

```shell 
mkdir /var/demo-repo 
cd /var/demo-repo 

git clone https://github.com/door7302/close-loop-demo . 
```

## Prerequisite: Install Docker & compose plugin

https://docs.docker.com/engine/install/ubuntu/

```shell
sudo umask 022

sudo apt-get update
sudo apt-get install ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update

sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

## Install Mongo DB py package 

```shell
pip install pymongo
```

## Download packages and prepare environment 

You may use the shell script `install.sh` to do all these tasks automatically or do it by yourself by following all steps below: 

### Install StackStorm 

```shell
mkdir -p /opt/stackstorm 

cd /opt/stackstorm 

git clone https://github.com/stackstorm/st2-docker .
```

### Install Kafka Tools 

```shell 
mkdir -p /opt/kafka

cd /tmp 

sudo curl -O https://downloads.apache.org/kafka/3.8.0/kafka_2.13-3.8.0.tgz

tar -xzf kafka_2.13-3.8.0.tgz

mv kafka_2.13-3.8.0/* /opt/kafka/

rm -rf /tmp/kafka_2.13-3.8.0
```

## Prepare folders

Create all folders 

```shell 
mkdir -p /opt/telegraf
mkdir -p /opt/telegraf/metadata
mkdir -p /opt/telegraf/cert
mkdir -p /opt/influxdb
mkdir -p /opt/influxdb/data
mkdir -p /opt/grafana
mkdir -p /opt/grafana/cert
mkdir -p /opt/grafana/provisioning
mkdir -p /opt/grafana/provisioning/datasources
mkdir -p /opt/grafana/provisioning/dashboards
mkdir -p /opt/grafana/data
mkdir -p /opt/grafana/plugins
mkdir -p /opt/demo 
```

Copy paste from the demo repo the following directories:

```shell 
cp -r /var/demo-repo/grafana/* /opt/grafana/
cp -r /var/demo-repo/influxdb/* /opt/influxdb/
cp -r /var/demo-repo/telegraf/* /opt/telegraf/
```

Copy the docker-compose file under /opt/demo:

```shell
cp /var/demo-repo/docker-compose.yml /opt/demo 
cp /var/demo-repo/.env /opt/demo 
```

Copy the StackStorm demo 

```shell
cp -r /var/demo-repo/demo /opt/stackstorm/packs.dev/
```
