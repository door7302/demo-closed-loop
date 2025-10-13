#!/usr/bin/env python3
import sys
import json

try:
    message = sys.argv[1]
    """
    Message example:
    {
    "fields":{
        "cmerror_clear":0,
        "cmerror_count":1,
        "cmerror_desc":"DRD_TOP_ECC2_PROTECT: Detected: FL FIFO MEM1",
        "cmerror_id":"/fpc/0/platformd/0/cm/0/mqss/0/MQSS_CMERROR_DRD_TOP_ECC2_PROTECT_FSET_REG_DETECTED_FL_FIFO_MEM1",
        "cmerror_slot":0,
        "cmerror_update":1760099160283
    },
    "name":"JUNOS_CMERROR",
    "tags":{
        "/junos/chassis/cmerror/counters/name":"/fpc/0/platformd/0/cm/0/mqss/0/MQSS_CMERROR_DRD_TOP_ECC2_PROTECT_FSET_REG_DETECTED_FL_FIFO_MEM1",
        "_component_id":"0",
        "_subcomponent_id":"0",
        "component":"fpc0/resiliencyd",
        "device":"rtme-mx304-06.englab.juniper.net",
        "host":"a4737c4624f4",
        "path":"/junos/chassis/cmerror/counters"
    },
    "timestamp":1760358802
    }
    """
    message = json.loads(message)

    # Parse fields
    cmerror_clear = message.get('fields', {}).get('cmerror_clear', None)
    cmerror_count = message.get('fields', {}).get('cmerror_count', None)
    cmerror_desc = message.get('fields', {}).get('cmerror_desc', None)
    cmerror_id = message.get('fields', {}).get('cmerror_id', None)
    cmerror_slot = message.get('fields', {}).get('cmerror_slot', None)
    cmerror_update = message.get('fields', {}).get('cmerror_update', None)
    # Parse tags
    cmerror_component = message.get('tags', {}).get('component', None)
    cmerror_device = message.get('tags', {}).get('device', None)
    cmerror_subcomponent_id = message.get('tags', {}).get('_subcomponent_id', None)
    


except IndexError:
    print("No message provided")
    raise SystemExit(1) 


print(f"LOGIC PARSES THE KAFKA MESSAGE: {message}")
