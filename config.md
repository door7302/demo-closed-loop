Create Kafka Topic:

export PATH=$PATH:/opt/kafka/bin
kafka-topics.sh --create --bootstrap-server 10.83.153.137:9092 --replication-factor 1 --partitions 1 --topic cmerror
kafka-topics.sh --list --bootstrap-server 10.83.153.137:9092

Ch@ngeMe

# 1. Register pack
st2 pack register /opt/stackstorm/packs.dev/demo && \
st2 run packs.setup_virtualenv packs=demo
# 2. Recreate virtualenv and install requirements
st2ctl reload --register-recreate-virtualenvs && \
# 3. Restart sensor container to pick up new sensors
docker restart demo-repo-st2sensorcontainer-1

{"message_sensor":{"bootstrap_servers":"10.83.153.137:9092","topics":[{"name":"cmerror","group_id":"st2_cmerror","trigger":"demo.cmerror_trigger"}]}}
GUI > PACK > DEMO 

Copy in : 

{"bootstrap_servers": "10.83.153.137:9092", "group_id": "st2_cmerror", "topic": "cmerror"}

{
  "message_sensor": {
    "bootstrap_servers": "10.83.153.137:9092",
    "topics": [
      {
        "name": "cmerror",
        "group_id": "st2_cmerror",
        "trigger": "demo.cmerror_trigger"
      }
    ]
  }
}

Install demo package:  

docker compose exec st2client bash 

root@7ed5112569d8:/opt/stackstorm# st2 pack install file:///opt/stackstorm/packs.dev/demo

        [ succeeded ] init_task
        [ succeeded ] download_pack
        [ succeeded ] make_a_prerun
        [ succeeded ] get_pack_dependencies
        [ succeeded ] check_dependency_and_conflict_list
        [ succeeded ] install_pack_requirements
        [ succeeded ] get_pack_warnings
        [ succeeded ] register_pack

+-------------+------------------------------------+
| Property    | Value                              |
+-------------+------------------------------------+
| ref         | demo                               |
| name        | demo                               |
| description | Demo pack for Kafka cmerror sensor |
| version     | 1.0.0                              |
| author      | Your Name                          |
+-------------+------------------------------------+

docker logs -f demo-repo-st2sensorcontainer-1

docker compose logs -f st2api

docker compose exec st2client bash 


st2 pack register /opt/stackstorm/packs/demo