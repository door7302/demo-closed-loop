Create Kafka Topic:

export PATH=$PATH:/opt/kafka/bin
kafka-topics.sh --create --bootstrap-server 10.83.153.137:9092 --replication-factor 1 --partitions 1 --topic cmerror
kafka-topics.sh --list --bootstrap-server 10.83.153.137:9092

Ch@ngeMe

# 1. Register pack

st2 run packs.load packs=git register=configs

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

st2 run packs.load packs=git register=configs

st2ctl reload --register-all
4  YT[1]
                  0x3f0001      1   Major      1        0       0        0        0                   YTCHIP_CMERROR_FLEXMEM_ECC_PROTECT_FSET_REG_DETECTED_SLICE

 test cmerror trigger-error 0x3f0001 1 YTCHIP_CMERROR_FLEXMEM_ECC_PROTECT_FSET_REG_DETECTED_SLICE 4

   123  host_loopback
                  0x020001      0   Major      1        0       0        0        0                   host_loopback_wedge_detected



Module-id  Name   Error-id     PFE  Level  Threshold  Count  Occured  Cleared  Last-occurred(ms ago)  Name
---------------------------------------------------------------------------------------------------------------
    1  GE Switch
                  0x180000      0   Major      1        0       0        0        0                   CMERROR_GESW_MODULE[0]


                   124  pic@0
                  0x310001      0   Fatal      1        0       0        0        0                   PIC_FPGA-PCIe_Fail

                  0x310007      1   Major      1        0       0        0        0                   PIC_Retimer_Failure



2025-10-15 15:00:37,526 INFO [-] Received message on cmerror: {"fields":{"cmerror_clear":0,"cmerror_count":1,"cmerror_desc":"FLEXMEM_ECC_PROTECT: Detected: Parity error for FlexMem slices","cmerror_id":"/fpc/0/platformd/0/cm/0/ytchip/1/YTCHIP_CMERROR_FLEXMEM_ECC_PROTECT_FSET_REG_DETECTED_SLICE","cmerror_slot":0,"cmerror_update":1760539753692},"name":"JUNOS_CMERROR","tags":{"/junos/chassis/cmerror/counters/name":"/fpc/0/platformd/0/cm/0/ytchip/1/YTCHIP_CMERROR_FLEXMEM_ECC_PROTECT_FSET_REG_DETECTED_SLICE","_component_id":"0","_subcomponent_id":"0","component":"fpc0/resiliencyd","device":"rtme-mx304-06.englab.juniper.net","host":"7829d0611225","path":"/junos/chassis/cmerror/counters"},"timestamp":1760540435}

2025-10-15 15:00:42,535 INFO [-] Received message on cmerror: {"fields":{"cmerror_clear":0,"cmerror_count":1,"cmerror_desc":"PIC Retimer Failure","cmerror_id":"/fpc/0:0/pic@0/0/cm/0/pic/0/PIC_Retimer_Failure","cmerror_slot":0,"cmerror_update":1760540427534},"name":"JUNOS_CMERROR","tags":{"/junos/chassis/cmerror/counters/name":"/fpc/0:0/pic@0/0/cm/0/pic/0/PIC_Retimer_Failure","_component_id":"0","_subcomponent_id":"0","component":"fpc0/resiliencyd","device":"rtme-mx304-06.englab.juniper.net","host":"7829d0611225","path":"/junos/chassis/cmerror/counters"},"timestamp":1760540435}


/fpc/0:0/pic@0/0/cm/0/pic/0/PIC_Retimer_Failure
/fpc/0/platformd/0/cm/0/ytchip/1/YTCHIP_CMERROR_FLEXMEM_ECC_PROTECT_FSET_REG_DETECTED_SLICE

MQSS_CMERROR_BCMF_ICM_FI_HPTRO_PROTECT_FSET_REG_CORRECTED_HPTR3B2),
196       MQSS_CMERROR_BCMF_ICM_FI_HPTRO_PROTECT_FSET_REG_CORRECTED_HPTR3B2,
197       CMERROR_LEVEL_MINOR, 1, 0, 0,
198       "BCMF_ICM_HPTRO_PROTECT: Corrected: HPTR3B2 memory",
199       CMERROR_SCOPE_PFE, CMERROR_CATEGORY_FUNCTIONAL,
200       CMERROR_LEVEL_MINOR_DEFAULT_ACTION,CMERROR_ACTION_LOCAL, 0 },






 test cmerror trigger-error 0x3f0001 1 YTCHIP_CMERROR_FLEXMEM_ECC_PROTECT_FSET_REG_DETECTED_SLICE 4
 test cmerror trigger-error 0x310007 0 PIC_Retimer_Failure 124


0x4502f5      0   Major      1        0       0        0        0                   pg_oct_8_cccdmacpcs_mac_intr_status_mac_tx_ovr_err


0x410001      2   Major      1        0       0        0        0                   fpc_link_to_sib_fault