# Closed Loop Automation Demo
# HPE Juniper Networking CLA Demo

This repository contains all materials and configurations needed to replicate the HPE Juniper Networking demo on Closed Loop Automation (`CLA`) in your lab.  

![CLA Framework](assets/framework.png)

You can also watch a recorded session of the demo: [YouTube video](https://www.youtube.com/watch?v=oVkMBBKSG0g)

First, install the prerequisite tools and complete the initial configuration. We assume you have two routers in your lab: **R1** and **R2**, which must be reachable by your CLA server via **Netconf** and **gNMI**. Ensure that the CLA server can connect to your R1 and R2 routers on ports **TCP/830** and **TCP/9339**.

> Make sure any ACLs or other firewall rules allow these two flows.

We also assume your CLA server is reachable via:  
- HTTP (**TCP/80**) or HTTPS (**TCP/443**)  
- **TCP/8080**  

If you want to integrate a **Slack** channel, your VM must have Internet access.  

The following diagram illustrates the topology:

![Topology](assets/anim.png)

## Installation 

We assume you are using a Debian linux distribution with these following tools pre-installed:
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

> Don't forget the `.` at the end. 

### Download additional packages and prepare environment 

You can use the shell script `install.sh` to perform all these tasks automatically, or you can do them manually by following the steps below.

```shell
cd /var/repo-demo

sudo chmod +x install.sh

./install.sh
```

At the end of this step, you should have the following folders created:

- `/opt/demo`: the demo folder containing the `docker-compose` setup for deploying the different tools.  
- `/opt/stackstorm`: the working folder for StackStorm.  
- `/opt/kafka`: the working folder for Kafka.  
- `/opt/telegraf`: the working folder for Telegraf.  
- `/opt/grafana`: the working folder for Grafana.  
- `/opt/influxdb`: the working folder for InfluxDB.  

If you used the `install.sh` script, you can skip directly to this [step](#initial-configuration).

#### Install Mongo DB py package 

```shell
sudo pip install pymongo
```

#### Install StackStorm 

```shell
sudo mkdir -p /opt/stackstorm 

cd /opt/stackstorm 

sudo git clone https://github.com/stackstorm/st2-docker .

sudo mkdir -p /opt/stackstorm/logs
sudo touch /opt/stackstorm/logs/demo_logic.log
chmod +666 /opt/stackstorm/logs/demo_logic.log
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

#### Prepare folders

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

As mentioned, we assume you have two routers: **R1** and **R2**. These simple hostnames are used in all configuration files to simplify the initial setup. You must create two static entries in your `/etc/hosts` file. **R1** should point to the management IP address of the router you designate as R1, and **R2** should point to the management IP address of the router you designate as R2 in your lab.

```shell 
cat /etc/hosts

x.x.x.x R1
y.y.y.Y R2 
```

### Using SSL for Grafana and Stackstorm

By default, we use HTTP for both Grafana and StackStorm. If you prefer to use HTTPS instead, you should first modify the `/opt/demo/.env` file. The default HTTP configuration is:

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

Next, you need to edit the `grafana.ini` configuration file to enable SSL. To do this, modify the following file and update the variables as shown below. **Keep the certificate and key filenames and paths unchanged.**

```shell 
cat /opt/grafana/grafana.ini

[server]
# Protocol (http, https, h2, socket)
protocol = https

# https certs & key file
cert_file = "/tmp/st2.crt"
cert_key ="/tmp/st2.key"
```

Next, you should place your certificates (your CLA server certificate and the CA certificate) into the following folders. **Keep the filenames unchanged.** We assume your certificate and key are named `st2.crt` and `st2.key`, respectively.

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
If you want to integrate **Slack** into the demo, you first need to follow these steps. In short, you must install the Slack client on a laptop, create a **noc-support** channel, and generate a token to allow the CLA server to post messages to this **noc-support** channel.

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps) and click `Create New App`, then select the `From scratch` option.

2. Give a name to your app associated with your Slack account—for example, `cla`:

![Create Slack App](assets/slack1.png)

3. On the next screen, go to the `OAuth & Permissions` menu, scroll down to `Scopes`, and add the following scopes:

![Scopes Slack App](assets/slack2.png)

4. Then go to the `Install App` menu and click the `Install <app name>` button:

![Install Slack App](assets/slack3.png)

5. At the end of the installation process, you should see two tokens:

![Slack App Token](assets/slack4.png)

Copy the second token, the **Bot User OAuth Token**.

Finally, update the `logic.py` Python script with this token. Open the following file and paste the token you just copied:

```shell 
vi /opt/stackstorm/packs.dev/demo/scripts/logic.py

# Scroll down until you find out the SLACK_TOKEN Variable and paste your Token

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

All the containers will be downloaded, built, and started by running the following command.  
This requires that your CLA server has Internet access.

```shell
# Go to demo folder 

cd /opt/demo 

sudo docker compose up -d 
 ⠙ Network demo_public                   Created  12.1s 
 ⠏ Network demo_private                  Created  11.9s 
 ✔ Container influxdb                    Started   2.9s 
 ✔ Container demo-redis-1                Started   1.9s 
 ✔ Container demo-rabbitmq-1             Started   2.1s 
 ✔ Container kafka                       Started   2.4s 
 ✔ Container demo-st2makesecrets-1       Started   2.0s 
 ✔ Container demo-mongo-1                Started   1.9s 
 ✔ Container grafana                     Started   7.6s 
 ✔ Container jts_telegraf                Started   6.0s 
 ✔ Container demo-st2api-1               Started   3.0s 
 ✔ Container demo-st2stream-1            Started   9.6s 
 ✔ Container demo-st2workflowengine-1    Started   7.5s 
 ✔ Container demo-st2scheduler-1         Started   7.1s 
 ✔ Container demo-st2timersengine-1      Started   9.5s 
 ✔ Container demo-st2notifier-1          Started   6.5s 
 ✔ Container demo-st2rulesengine-1       Started   8.6s 
 ✔ Container demo-st2auth-1              Started   7.7s 
 ✔ Container demo-st2sensorcontainer-1   Started  10.3s 
 ✔ Container demo-st2actionrunner-1      Started  10.7s 
 ✔ Container demo-st2garbagecollector-1  Started   6.5s 
 ✔ Container demo-st2chatops-1           Started  10.7s 
 ✔ Container demo-st2web-1               Started  11.5s 
 ✔ Container demo-st2client-1            Started  10.8s
```

> This could take a few minutes the first time. 

### Additionnal configuration 

First create the **cmerror** Kafka topic:

```shell
export PATH=$PATH:/opt/kafka/bin

kafka-topics.sh --create --bootstrap-server 10.83.153.137:9092 --replication-factor 1 --partitions 1 --topic cmerror

kafka-topics.sh --list --bootstrap-server 10.83.153.137:9092
```

Next, you must install the StackStorm **demo** Pack. First, connect to the **st2client** container and run the following **st2** commands:

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

root@7ed5112569d8:/opt/stackstorm# exit
```

Finally, you must access the StackStorm GUI to configure the sensor. Open the web page: `http(s)://your-cla-server-ip`.

> Default credentials are `st2admin/Ch@ngeMe`

Then, click on the "PACKS" menu at the top of the page and search for the `demo` pack. Finally, copy and paste the following JSON configuration into the input field. You only need to replace `YOUR-CLA-SERVER-IP` with the local Ethernet IP of your CLA server:

```json
{
  "message_sensor": {
    "bootstrap_servers": "YOUR-CLA-SERVER-IP:9092",
    "topics": [
      {
        "name": "cmerror",
        "group_id": "st2_cmerror",
        "trigger": "demo.cmerror_trigger"
      }
    ]
  }
}
```

![st2 pack config](assets/st2gui1.png)

Once saved, you should see this message:

![st2 saved](assets/st2gui2.png)

The final step is to reload the package from the `st2client` container. Follow the steps below:

```shell
cd /opt/demo

docker compose exec st2client bash 

root@7ed5112569d8:/opt/stackstorm# st2 login st2admin 

/!\ Password is: Ch@ngeMe 

root@7ed5112569d8:/opt/stackstorm# st2ctl reload --register-all

root@7ed5112569d8:/opt/stackstorm# exit
```

### Verifications

Depending on whether you configured SSL or not:

- You should be able to access the Grafana GUI via: `http(s)://your-cla-server-ip:8080`  
- You should be able to access the StackStorm GUI via: `http(s)://your-cla-server-ip`  

Verify on each router that the gNMI session is properly established:

```junos
R1> show system connections | match 9339 
tcp4       0      0  10.83.154.64.9339                             10.83.153.137.53522                           ESTABLISHED
tcp46      0      0  *.9339                                        *.*                                           LISTEN

R2> show system connection | match 9339 
tcp6       0      0 :::9339                 :::*                    LISTEN      14000/nginx: master
tcp6       0      0 10.83.154.6:9339        10.83.153.137:38722     ESTABLISHED 20427/nginx: worker
```

## Play the demo

Make sure the gNMI session is up and running on both routers.  
Open the Grafana dashboard, the Slack **noc-support** channel (if configured), and a console on your CLA server, then monitor the following log file:

```shell
tail -f /opt/stackstorm/logs/demo_logic.log
```

1. Provision the inventory. 

You may edit the `/opt/demo/sample_inventory.json` file if needed. Just make sure not to modify the router names **R1** and **R2**.

```shell
cd /opt/demo

python3 provision_mongo.py 
Inserted 2 routers
Inserted 1 POPs
✅ Database initialized successfully.
```
2. Select a router (MX or PTX) and trigger a hardware error

On either R1 or R2, open a console and run the following command to generate a "Major" error ID:

![Demo](assets/topo.png)

Choose one FPC on which you want to trigger the error, then issue the following commands depending on the router and linecard model. You should see a long list of alarms.

- For all MX240, MX480, MX960, MX2K, MX10003 MPC, and MX10K LC480, except for **MPC10e** and **MPC11e**:

**X** is the FPC/MPC Slot
```junos 
R1> start shell pfe network fpcX

SMPC0(R1 vty)# show cmerror module      

Module-id  Name   Error-id     PFE  Level  Threshold  Count  Occurred  Cleared  Last-occurred(ms ago)  Name
-----------------------------------------------------------------------------------------------------------
<-- truncated output -->
   17  XR2CHIP(3)
                  0x250002      1   Minor      1        0       0         0        0                   XR2CHIP_ASIC_JGCI_MINOR_CRC_ERROR
                  0x250001      1   Major      1        0       0         0        0                   XR2CHIP_ASIC_JGCI_MAJOR_CRC_ERROR
   18  EA[0:0]
                  0x240001      0   Major      1        0       0         0        0                   EACHIP_CMERROR_HMCIF_TX_INT_REG_WO_DEALLOC_IDX_UNDERFLOW

<-- truncated output -->
```

Pick one `Major` alarm related to an ASIC (XL, LU, EA, etc.). You must note the following:

- **Module-id**: For example, if the alarm is related to `EA[0:0]`, the ID is `18`  
- **Error-id**: `0x240001`  
- **PFE**: `0`  
- **Name**: `EACHIP_CMERROR_HMCIF_TX_INT_REG_WO_DEALLOC_IDX_UNDERFLOW`

Then, issue the command to trigger the alarm:

**X** is the FPC/MPC Slot
```junos 
R1> start shell pfe network fpcX

# Syntax is: test cmerror trigger-error <error-id> <pfe> <name> <module-id> 

SMPC0(R1 vty)# test cmerror trigger-error 0x240001 0 EACHIP_CMERROR_HMCIF_TX_INT_REG_WO_DEALLOC_IDX_UNDERFLOW 18
```

- For MPC10e, MPC11e or all other MX10K MPCs or MX304 chassis and all PTX10K EVO chassis:

**X** is the FPC/MPC Slot
```junos 
R2> start shell pfe network fpcX

lab@R2:pfe> show cmerror module fpc X   

Module-id  Name   Error-id     PFE  Level  Threshold  Count  Occured  Cleared  Last-occurred(ms ago)  Name
---------------------------------------------------------------------------------------------------------------
    1  fab-pfe@0
<-- truncated output -->
                  0x410002      5   Major      1        0       0        0        0                   Fabric_Plane_health_failure
                  0x410007      5   Major      1        0       0        0        0                   PFE_Asic_PIO_Fault
                  0x410008      5   Major      1        0       0        0        0                   PFE_Asic_Fabric_Self_Reachability_Fault
    4  btchip
<-- truncated output --> 
                  0x450011      0   Fatal      1        0       0        0        0                   hostif_dma_3_sram_p_intr_d_dma_sram_bnk
                  0x450012      0   Major      1        0       0        0        0                   toe_0_intr2_unaligned_memory_error_thread_3
```

Pick one `Major` alarm related to an ASIC (BT, BX, ZT, YT, etc.). You must note the following:

- **Module-id**: For example, if the alarm is related to `btchip`, the ID is `4`  
- **Error-id**: `0x450012`  
- **PFE**: `0`  
- **Name**: `toe_0_intr2_unaligned_memory_error_thread_3`

Then, issue the command to trigger the alarm:

**X** is the FPC/MPC Slot
```junos 
R1> start shell pfe network fpcX

# Syntax is: test cmerror trigger-error <error-id> <pfe> <name> <module-id> 

lab@R2:pfe> test cmerror trigger-error 0x450012 0 toe_0_intr2_unaligned_memory_error_thread_3 4
```

This last command should trigger a "cmerror" Major alarm, which in turn will trigger the following "logic":

![logic to mitigate cmerror](assets/algo.png)