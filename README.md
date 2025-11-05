# Closed Automation Demo

This repository contains all materials and configurations to replicate in your lab the HPE Juniper Networking demo about Closed Loop Automation or `CLA`. 

![CLA Framework](assets/framework.png)

Your should first install the Prerequisite tools and make the initial configuration. We assume you have 2 routers in your lab: R1 and R2 must be reachable by your CLA server throught Netconf and gNMI. You must allow the CLA server to connect to your R1 and R2 routers on ports **TCP/830** and **TCP/9339**.

> Make sure ACL or other Firewall rules allow these 2 flows. 

We also consider you CLA server be reachable via:
- HTTP **TCP/80** or HTTTPS **TCP/443**
- **TCP/8080**

Also if you want to integrate a **Slack** channel, your VM should access to Internet. 

The following picture illustrates the topology:

![Topology](assets/anim.png)

## Installation 

We consider you use a Debian linux distribution with these following tools pre-installed:
- git
- python 3.12 (min)
- pip3 

### Prerequisite: Install Docker & compose plugin

We use this ubuntu version: https://docs.docker.com/engine/install/ubuntu/

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

### Clone this repository

We consider you clone the repo under `/var/repo-demo`:

```shell 
mkdir /var/demo-repo 
cd /var/demo-repo 

git clone https://github.com/door7302/close-loop-demo . 
```

### Download additionnal packages and prepare environment 

You may use the shell script `install.sh` to do all these tasks automatically or do it by yourself by following all steps below.

```shell
cd /var/repo-demo

sudo chmod +x install.sh

./install.sh
```

At the end of this step you should have these folders created:
- `/opt/demo`: the demo folder where the docker-compose is located to deploy the different tools. 
- `/opt/stacktorm`: the working folder for stackstorm.
- `/opt/kafka`: the working folder for kafka.
- `/opt/telegraf`: the working folder for telegraf.
- `/opt/grafana`: the working folder for grafana.
- `/opt/influxdb`: the working folder for influxdb.

You can switch directly to this [step](#initial-configuration) if you used the `install.sh` script. 

#### Install Mongo DB py package 

```shell
sudo pip install pymongo
```

#### Install StackStorm 

```shell
sudo mkdir -p /opt/stackstorm 

cd /opt/stackstorm 

sudo git clone https://github.com/stackstorm/st2-docker .
```

#### Install Kafka Tools 

```shell 
sudo mkdir -p /opt/kafka

cd /tmp 

sudo curl -O https://downloads.apache.org/kafka/3.8.0/kafka_2.13-3.8.0.tgz

sudo tar -xzf kafka_2.13-3.8.0.tgz

sudo mv kafka_2.13-3.8.0/* /opt/kafka/

sudo rm -rf /tmp/kafka_2.13-3.8.0
```

### Prepare folders

Create all folders 

```shell 
sudo mkdir -p /opt/telegraf
sudo mkdir -p /opt/telegraf/metadata
sudo mkdir -p /opt/telegraf/cert
sudo mkdir -p /opt/influxdb
sudo mkdir -p /opt/influxdb/data
sudo mkdir -p /opt/grafana
sudo mkdir -p /opt/grafana/cert
sudo mkdir -p /opt/grafana/provisioning
sudo mkdir -p /opt/grafana/provisioning/datasources
sudo mkdir -p /opt/grafana/provisioning/dashboards
sudo mkdir -p /opt/grafana/data
sudo mkdir -p /opt/grafana/plugins
sudo mkdir -p /opt/demo 
```

Copy paste from the demo repo the following directories:

```shell 
sudo cp -r /var/demo-repo/grafana/* /opt/grafana/
sudo cp -r /var/demo-repo/influxdb/* /opt/influxdb/
sudo cp -r /var/demo-repo/telegraf/* /opt/telegraf/
```

Copy the docker-compose file under /opt/demo:

```shell
sudo cp /var/demo-repo/docker-compose.yml /opt/demo 
sudo cp /var/demo-repo/.env /opt/demo 
```

Copy the provision_mongo script and its json file:

```shell
sudo cp /var/demo-repo/provision_mongo.py /opt/demo 
sudo cp /var/demo-repo/sample_inventory.json /opt/demo 
```

Copy the StackStorm demo 

```shell
sudo cp -r /var/demo-repo/demo /opt/stackstorm/packs.dev/
```

## Initial Configuration

### Provision /etc/hosts

As mentionned we consider you have 2 routers **R1** and **R2**. These 2 simple hostname are used in all the config files to simplify the initial configuration. You must create 2 static entries into your `/etc/hosts`. R1 should point to the management IP address of the router you consider to be **R1**. Similary, R2 should point to the management IP address of the router you consider to be **R2** in your lab. 

```shell 
cat /etc/hosts

x.x.x.x R1
y.y.y.Y R2 
```

### Using SSL for Grafana and Stackstorm

By default we use simple HTTP for both Grafana and Stacktorm. In case you'd prefer to use HTTPS instead, you should first modify the `/opt/demo/.env` file. The default HTTP config is:

```shell 
GRAFANA_PORT=8080
ST2_EXPOSE_HTTP=0.0.0.0:80
ST2_EXPOSE_HTTPS=0.0.0.0:443
ST2WEB_HTTPS=0
```

To switch to HTTPS just set the flag **ST2WEB_HTTPS** to 1 as below:

```shell
GRAFANA_PORT=8080
ST2_EXPOSE_HTTP=0.0.0.0:80
ST2_EXPOSE_HTTPS=0.0.0.0:443
ST2WEB_HTTPS=1
```

Then you need to edit `grafana.ini` config file to enable SSL as well. For that, edit the following file and change the variable like that. **Keep the names and paths of certificate and key unchanged.**

```shell 
cat /opt/grafana/grafana.ini

[server]
# Protocol (http, https, h2, socket)
protocol = https

# https certs & key file
cert_file = "/tmp/st2.crt"
cert_key ="/tmp/st2.key"
```

Then you should put your certificate (of your CLA server and the CA certificate) into these following folders. **Keep the names unchanged.** We assume your certificate and key have respectively the name st2.crt and st2.key. 

```shell 
cp st2.key /opt/grafana/cert
cp st2.crt /opt/grafana/cert

mkdir -p /etc/ssl/st2
cp st2.key /etc/ssl/st2
cp st2.crt /etc/ssl/st2
```
In case you need to also install the CA certificate, follow these steps as well:

```shell
cp ca.crt /usr/local/share/ca-certificates/ca.crt

# update CA then
update-ca-certificates
```

### Slack Integration 

In case you want to integrate a **Slack** in the demo, you need first to follow the following steps. In short, you must install Slack client on a laptop, create a **noc-support** channel and create a Token to allow the CLA server to publish messages under this **noc-support** channel. 

First you should connect to https://api.slack.com/apps and click to `Create New App` then select `from scratch` option.

Give a name to your app associated to your slack account - in my example I've chosen `cla`:

![create slack's app](assets/slack1.png)

On the next screen, go to `OAuth & Permissions` menu and scroll down until you see `Scope` and then add the following scopes:

![scopes slack's app](assets/slack2.png)

Then go to the `Install App` menu and click on the `Install xxx` button

![install slack's app](assets/slack3.png)

At the end of the install process you should see 2 tokens:

![slack's app token](assets/slack4.png)

Copy the second token `Bot user OAuth Token`. 

You should then update the `logic.py` python script with this Token. Open the following file and paste the previous Token:

```shell 
vi /opt/stackstorm/packs.dev/demo/scripts/logic.py

# Scroll down until you find out the SLACK_SECRET Variable and paste your Token

# SLACK TOKEN
SLACK_TOKEN="xoxb-9xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxp"

# Save the file
```

Finally, thanks to the slack client, create a channel named `noc-support`

### Router Configuration 

On your 2 routers, apply this configuration. Don't change the `lab` password. 

```junos
edit exclusive

# Create lab/lab123 user/pwd
set system login user lab class super-user
set system login user lab123 authentication plaintext-password xxxxx < lab123

# Clear Text gRPC/gNMI service
set system services extension-service request-response grpc clear-text port 9339
set system services extension-service request-response grpc max-connections 8
set system services extension-service request-response grpc skip-authentication

# Netconf service
set system services netconf ssh

commit and-quit
```

## Launch the environment  

All the containers will be download, built, and started by issuing the following command:

```shell
# Go to demo folder 

cd /opt/demo 

sudo docker compose up -d 
```

### Additionnal configuration 

First create the **cmerror** Kafka topic:

```shell
export PATH=$PATH:/opt/kafka/bin

kafka-topics.sh --create --bootstrap-server 10.83.153.137:9092 --replication-factor 1 --partitions 1 --topic cmerror

kafka-topics.sh --list --bootstrap-server 10.83.153.137:9092
```

Then you must install the Stackstorm **demo** Pack. You should first connect to the **st2client** container and issue some **st2** commands: 

```shell
cd /opt/demo

docker compose exec st2client bash 

root@7ed5112569d8:/opt/stackstorm# st2 login st2admin 

/!\ Password is: Ch@ngeMe 

root@7ed5112569d8:/opt/stackstorm# st2 pack install file:///opt/stackstorm/packs.dev/demo

        [ succeeded ] init_task
        [ succeeded ] download_pack
        [ succeeded ] make_a_prerun
        [ succeeded ] get_pack_dependencies
        [ succeeded ] check_dependency_and_conflict_list
        [ succeeded ] install_pack_requirements
        [ succeeded ] get_pack_warnings
        [ succeeded ] register_pack

+-------------+-------------------------------------------+
| Property    | Value                                     |
+-------------+-------------------------------------------+
| ref         | demo                                      |
| name        | demo                                      |
| description | Demo pack for Closed Loop Automation Demo |
| version     | 1.0.0                                     |
| author      | David Roy                                 |
+-------------+-------------------------------------------+

root@7ed5112569d8:/opt/stackstorm# st2ctl reload --register-all

root@7ed5112569d8:/opt/stackstorm# exit
```

### Verifications

Depending on you configure SSL or not. 

You should be able to access to Grafana GUI via: http(s)://<your-cla-server>:8080 
You should be able to access to Stackstorm GUI via: http(s)://<your-cla-server>

> StackStorm is not used for the demo, default credentials are st2admin/Ch@ngeMe

Verify on each router the gNMI session is well established: 

```junos
R1> show system connection | match 9339 
```

## Play the demo

Make sure gNMI session is up and running on both routers. Open Grafana Dashboard, Slack **noc-support** channel, if configured and a console of your CLA server and monitor the following log file:

```shell
tail -f /opt/stackstorm/logs/demo_logic.log
```

1. Provision the inventory. 

You may edit the `/opt/demo/sample_inventory.json` if needed. Just don't modify router name R1 and R2. 

```shell
cd /opt/demo

python3 provision_mongo.py 
```

2. Select a router MX or PTX and trigger an HW error
 
Either on R1 or R2, open a console and issue the following command to pick up a "Major" error id. 

![Demo](assets/topo.png)

Choose one FPC on which you want to trigger an error. 

For all MX240, MX480, MX960, MX2K, MX10003 MPC and MX10K LC480 except the **MPC10e and MPC11e**: 

**X** is the FPC/MPC Slot
```junos 
start shell pfe network fpcX

```

For MPC10e, MPC11e or all other MX10K MPCs or MX304 chassis and all PTX10K EVO chassis:

**X** is the FPC/MPC Slot
```junos 
start shell pfe network fpcX.0

```

This last command should trigger a "cmerror" Major alarm and thus trigger the following "logic":

![logic to mitigate cmerror](assets/algo.png)
