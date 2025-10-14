#!/usr/bin/env python3
import sys
import os
import json
import logging
import re
import time
from datetime import datetime, timezone
from influxdb import InfluxDBClient
from lxml import etree
from pymongo import MongoClient
from jnpr.junos import Device
from jnpr.junos.utils.config import Config
from jnpr.junos.exception import ConnectError, RpcError, ConfigLoadError, CommitError

# Set up logging
# Create logs directory if it doesn't exist
log_dir = "/opt/stackstorm/logs"
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, "demo_logic.log")

# Initialize logger
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

# File handler only
file_handler = logging.FileHandler(log_file)
file_formatter = logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s')
file_handler.setFormatter(file_formatter)

# Avoid duplicate handlers if reloaded
if not LOG.handlers:
    LOG.addHandler(file_handler)

# Set MongoDB connection parameters
MONGO_URI = "mongodb://mongo:27017/"
DB_NAME = "networkdb"

######################################@ FUNCTIONS ################################
# Function definitions
##################################################################################

def check_fpc_major_alarm(router_name, fpc_slot=None):
    """
    Connects to a Juniper router using PyEZ, retrieves alarms, and checks
    for any 'Major' FPC-related alarm.
    
    If fpc_slot is specified, only alarms related to that FPC slot are considered.

    Args:
        router_name (str): Hostname or IP of the Juniper router.
        fpc_slot (int|str|None): Optional FPC slot number to filter alarms for.

    Returns:
        tuple: (alarm_description, err)
            alarm_description (str): Matching alarm description, or empty string.
            err (str): Error message if any exception occurs, else empty string.
    """
    dev = None
    alarm_desc = ""
    err = ""

    try:
        # Connect to the device
        dev = Device(host=router_name, user="lab", passwd="lab123")
        dev.open()

        # Execute RPC to get alarm information
        rsp = dev.rpc.get_alarm_information()

        # Parse alarm entries
        for alarm in rsp.findall('.//alarm-detail', namespaces=rsp.nsmap):
            alarm_class = alarm.findtext('alarm-class', default='').strip()
            alarm_description = alarm.findtext('alarm-description', default='').strip()

            # Check for major class
            if not re.search(r'major', alarm_class, re.IGNORECASE):
                continue

            # Base condition (same as before)
            if (re.search(r'fpc', alarm_description, re.IGNORECASE)
                and re.search(r'major', alarm_description, re.IGNORECASE)):
                
                # If a specific FPC slot is provided, restrict match
                if fpc_slot is not None:
                    pattern = rf'\b(fpc\s*{fpc_slot})\b'
                    if re.search(pattern, alarm_description, re.IGNORECASE):
                        alarm_desc = alarm_description
                        break
                else:
                    alarm_desc = alarm_description
                    break

    except (ConnectError, RpcError, Exception) as e:
        err = str(e)
    finally:
        if dev and dev.connected:
            dev.close()

    return alarm_desc, err

def get_interfaces_by_slot(router_name, fpc_slot, pfe_slot):
    """
    Connects to a Juniper router using PyEZ, retrieves interface configuration,
    and returns:
      - interfaces matching both FPC and PFE slots
      - interfaces matching only the FPC slot

    Args:
        router_name (str): Hostname or IP of the router.
        fpc_slot (int | str): FPC slot number to match.
        pfe_slot (int | str): PFE slot number to match.

    Returns:
        tuple: (interfaces_fpc_pfe, interfaces_fpc_only, err)
            interfaces_fpc_pfe (list): Interfaces matching both FPC and PFE slots.
            interfaces_fpc_only (list): Interfaces matching only the FPC slot.
            err (str): Error message if exception occurs, else empty string.
    """
    dev = None
    interfaces_fpc_pfe = []
    interfaces_fpc_only = []
    err = ""

    try:
        # Connect to the device
        dev = Device(host=router_name, user="lab", passwd="lab123")
        dev.open()

        # Retrieve the configuration of interfaces
        config = dev.rpc.get_config(filter_xml='interfaces', options={'format': 'xml'})

        # Regex patterns
        pattern_fpc_pfe = re.compile(
            rf"^(ge|xe|et)-{fpc_slot}/{pfe_slot}/\d+.*$",
            re.IGNORECASE
        )
        pattern_fpc_only = re.compile(
            rf"^(ge|xe|et)-{fpc_slot}/\d+/\d+.*$",
            re.IGNORECASE
        )

        # Iterate through interface entries
        for if_entry in config.findall('.//interface', namespaces=config.nsmap):
            name = if_entry.findtext('name', default='').strip()
            if not name:
                continue

            if pattern_fpc_pfe.match(name):
                interfaces_fpc_pfe.append(name)
            elif pattern_fpc_only.match(name):
                interfaces_fpc_only.append(name)ƒ◊

    except (ConnectError, RpcError, Exception) as e:
        err = str(e)
    finally:
        if dev and dev.connected:
            dev.close()

    return interfaces_fpc_pfe, interfaces_fpc_only, err

def configure_interfaces_disable_state(router_name, interfaces, action="disable"):
    """
    Connects to a Juniper router using PyEZ and sets or removes the 'disable'
    statement on a list of interfaces in a single commit.

    Args:
        router_name (str): Hostname or IP of the router.
        interfaces (list): List of interface names (e.g., ['ge-0/0/0', 'xe-1/0/2']).
        action (str): "disable" to disable interfaces or "enable" to re-enable them.

    Returns:
        str: Error message if any exception occurs, otherwise an empty string.
    """
    dev = None
    err = ""

    if action not in ["disable", "enable"]:
        return "Invalid action. Use 'disable' or 'enable'."

    if not interfaces:
        return "No interfaces provided."

    try:
        # Connect to the device
        dev = Device(host=router_name, user="lab", passwd="lab123")
        dev.open()

        # Start configuration session
        cu = Config(dev)

        # Build set-style configuration lines depending on action
        if action == "disable":
            config_lines = [f"set interfaces {iface} disable" for iface in interfaces]
            comment = "Disabled interfaces via PyEZ script"
        else:  # enable
            config_lines = [f"delete interfaces {iface} disable" for iface in interfaces]
            comment = "Enabled interfaces via PyEZ script"

        # Load configuration (merge mode)
        cu.load("\n".join(config_lines), format="set", merge=True)

        # Commit configuration
        cu.commit(comment=comment)

    except (ConnectError, RpcError, ConfigLoadError, CommitError, Exception) as e:
        err = str(e)
        # Try rollback if possible
        try:
            if cu:
                cu.rollback()
        except Exception:
            pass
    finally:
        if dev and dev.connected:
            dev.close()

    return err

def reboot_fpc_and_wait(router_name, fpc_slot):
    """
    Reboots a Juniper FPC (linecard) and waits until it is Online with non-zero heap memory.

    Args:
        router_name (str): Hostname or IP of the router.
        fpc_slot (int | str): FPC slot number to reboot.

    Returns:
        str: Empty string if success, otherwise an error message.
    """
    dev = None
    err = ""

    try:
        dev = Device(host=router_name, user="lab", passwd="lab123")
        dev.open()

        LOG.info(f"LOGIC: Triggering reboot of FPC {fpc_slot} on {router_name}...")
        dev.rpc.request_chassis_fpc_restart(slot=str(fpc_slot))

        # Build custom RPC manually
        rpc = etree.Element("request-chassis-fpc")
        etree.SubElement(rpc, "slot").text = str(fpc_slot)
        etree.SubElement(rpc, "restart")

        # Send the RPC
        dev.rpc(rpc)

        LOG.info("LOGIC: Reboot command sent. Waiting 30 seconds before monitoring...")
        time.sleep(30)

        timeout = 10 * 60   # 10 minutes
        interval = 10       # 10 seconds between checks
        waited = 0

        while waited < timeout:
            try:
                rsp = dev.rpc.get_fpc_information(slot=str(fpc_slot))
            except RpcError:
                # FPC may be unreachable during reboot
                LOG.info(f"LOGIC: [{waited}s] FPC {fpc_slot} not responding yet...")
                time.sleep(interval)
                waited += interval
                continue

            fpc = rsp.find('.//fpc', namespaces=rsp.nsmap)
            if fpc is None:
                LOG.info(f"LOGIC: [{waited}s] No FPC info yet...")
            else:
                state = fpc.findtext('state', default='Unknown').strip()
                heap_str = fpc.findtext('memory-heap-utilization', default='0').strip()

                try:
                    heap = int(heap_str)
                except ValueError:
                    heap = 0

                print(f"[{waited:>3}s] state={state}, heap={heap}%")

                if state.lower() == "online" and heap > 0:
                    LOG.info(f"LOGIC: FPC {fpc_slot} is Online with heap {heap}%.")
                    break

            time.sleep(interval)
            waited += interval

        if waited >= timeout:
            err = f"Timeout: FPC {fpc_slot} did not come online within 10 minutes."

    except (ConnectError, RpcError, Exception) as e:
        err = f"Error during FPC reboot: {e}"

    finally:
        if dev and dev.connected:
            dev.close()

    return err

def write_log_to_influx(router_name, message, host="localhost", port=8086, db="demo"):
    """
    Writes a log message to InfluxDB in measurement 'logs' with a tag 'router_name'.
    Adds current UTC timestamp.

    Args:
        router_name (str): Router name tag.
        message (str): Log message to store.
        host (str): InfluxDB host (default: localhost).
        port (int): InfluxDB port (default: 8086).
        db (str): Database name (default: demo).

    Returns:
        str: Empty string if success, otherwise error message.
    """
    err = ""
    try:
        client = InfluxDBClient(host=host, port=port, database=db)

        # Current UTC timestamp in ISO 8601 format
        timestamp = datetime.now(timezone.utc).isoformat()

        json_body = [
            {
                "measurement": "logs",
                "tags": {
                    "router_name": router_name
                },
                "time": timestamp,
                "fields": {
                    "message": message
                }
            }
        ]

        client.write_points(json_body)

    except Exception as e:
        err = str(e)

    finally:
        try:
            client.close()
        except:
            pass

    return err

def mark_cmerror_as_handled(db, cmerror_device, cmerror_id):
    """
    Marks a cmerror as handled in MongoDB.

    Args:
        db: MongoDB database object.
        cmerror_device (str): Router name.
        cmerror_id (str): CM error ID.

    Returns:
        None
    """
    try:
        result = db.cmerrors.update_one(
            {"router_name": cmerror_device, "cmerror_id": cmerror_id},
            {"$set": {"handled": True}}  
        )

        if result.matched_count:
            LOG.info(f"LOGIC: CMERROR for {cmerror_device} - {cmerror_id} marked as handled")
        else:
            LOG.warning(f"LOGIC: CMERROR for {cmerror_device} - {cmerror_id} not found, cannot mark handled")

    except Exception as e:
        LOG.error(f"LOGIC: Unable to update 'handled' field in MongoDB: {e}")
        raise SystemExit(1)

def disable_interfaces_and_notify_noc(db, cmerror_device, cmerror_slot, cmerror_pfe, cmerror_id, cmerror_desc, interfaces):
    """
    Disables specified interfaces and notifies NOC team.

    Args:
        db: MongoDB database object.
        cmerror_device (str): Router name.
        cmerror_slot (int|str): FPC slot number.
        cmerror_pfe (int|str): PFE slot number.
        cmerror_id (str): CM error ID.
        cmerror_desc (str): CM error description.
        interfaces (list): List of interfaces to disable.

    Returns:
        None
    """
    LOG.info(f"LOGIC: INTERFACES TO DISABLE on {cmerror_device}: {interfaces}")
    
    err = configure_interfaces_disable_state(cmerror_device, interfaces, action="disable")
    if err:
        LOG.error(f"LOGIC: Unable to disable interfaces on {cmerror_device}: {err}")
        raise SystemExit(1) 
    
    LOG.info(f"LOGIC: INTERFACES DISABLED on {cmerror_device}")
    write_log_to_influx(cmerror_device, f"Disabling interfaces attached on {cmerror_device} and FPC slot {cmerror_slot} and pfe {cmerror_pfe}", host="influxdb", port=8086, db="demo")

    # Notify NOC team
    LOG.info(f"LOGIC: NOTIFY NOC TEAM - PARTIAL ACTION TAKEN - INTERFACES DISABLED: {interfaces}")
    write_log_to_influx(cmerror_device, f"NOC team should open a ticket for device {cmerror_device} and FPC slot {cmerror_slot} due to cmerror {cmerror_desc}", host="influxdb", port=8086, db="demo")

    mark_cmerror_as_handled(db, cmerror_device, cmerror_id)

##############################@ MAIN #############################################
# Main script logic
##################################################################################

# Get param from command line argument
try:
    param = sys.argv[1]
    LOG.info(f"LOGIC: PARSES THE KAFKA MESSAGE: {param}")
except IndexError:
    LOG.error("LOGIC: No parameter provided")
    raise SystemExit(1) 

# Parse message, which can be JSON or a Python dict string
try:
    message_dict = json.loads(param)
    LOG.info("LOGIC: Message parsed as JSON successfully")
except json.JSONDecodeError:
    # fallback: maybe it's a Python dict string
    LOG.warning("LOGIC: Message is not valid JSON, trying to parse as Python dict string")
    import ast
    message_dict = ast.literal_eval(param)

# Sample message structure
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

# Parse fields
cmerror_clear = message_dict.get('fields', {}).get('cmerror_clear', None)
cmerror_count = message_dict.get('fields', {}).get('cmerror_count', None)
cmerror_desc = message_dict.get('fields', {}).get('cmerror_desc', None)
cmerror_id = message_dict.get('fields', {}).get('cmerror_id', None)
cmerror_slot = message_dict.get('fields', {}).get('cmerror_slot', None)
cmerror_update = message_dict.get('fields', {}).get('cmerror_update', None)
# Parse tags
cmerror_component = message_dict.get('tags', {}).get('component', None)
cmerror_device = message_dict.get('tags', {}).get('device', None)
cmerror_pfe = message_dict.get('tags', {}).get('_subcomponent_id', None)
    
##############################@ LOGIC #################################

# Step 1: check if cmerror_clear is 0 or 1
if cmerror_clear == 1:
    LOG.info(f"LOGIC: CMERROR CLEARED for {cmerror_device} - {cmerror_desc} - NO ACTION REQUIRED")
    sys.exit(0)

# Step 2: check some data from MongoDB
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    # --- 1️⃣ Get router info ---
    router = db.routers.find_one({"router_name": cmerror_device}, {"_id": 0})
    if not router:
        LOG.error(f"LOGIC: Router {cmerror_device} not found in MongoDB")
        raise SystemExit(1)
    
    # --- 2️⃣ Get POP info ---
    pop_name = router.get("router_pop")
    pop_entry = db.pops.find_one({"pop_name": pop_name}, {"_id": 0})
    pop_routers = pop_entry.get("routers") if pop_entry else None

    # --- 3️⃣ Get CM error ---
    cm_error = db.cmerrors.find_one(
    {"router_name": cmerror_device, "cmerror_id": cmerror_id},
    {"_id": 0}  
    )

except Exception as e:
    LOG.error(f"LOGIC: Unable to connect to MongoDB: {e}")
    raise SystemExit(1)

# Step 3: Check if this cmerror_id already exists for this device

"""
cmerror structure:
  {
    "router_name": "rtme-mx304-06.englab.juniper.net",
    "cmerror_id": "...",
    "cmerror_count": 2,
    "cmerror_update": 1760099200000,
    "cmerror_slot": 1,
    "cmerror_desc": "...",
    "cmerror_pfe": 0,
    "handled": false
  }
"""

# Default no action required, 1 partial logic, 2 = full action required
action_required = 0

if cm_error and cm_error.get("handled"):
    # if same timestamp, ignore
    if cmerror_update == cm_error.get("cmerror_update"):
        LOG.info(f"LOGIC: CMERROR for {cmerror_device} - {cmerror_desc} - NO UPDATE (same timestamp)")
        sys.exit(0)

    # Check if cmerror_count is increased
    if cmerror_count > cm_error.get("cmerror_count"):
        LOG.info(f"LOGIC: CMERROR for {cmerror_device} - {cmerror_desc} - COUNT INCREASED")

        # If this new alarm update is within 24 hours of the last update, and the count is increased
        time_diff = (cmerror_update - cm_error.get("cmerror_update")) / 1000  # convert to seconds
        if time_diff < 86400:
            action_required = 1  # partial action required
            LOG.info(f"LOGIC: CMERROR for {cmerror_device} - {cmerror_desc} - PARTIAL ACTION REQUIRED (within 24 hours)")
        else:
            action_required = 2  # full action required
            LOG.info(f"LOGIC: CMERROR for {cmerror_device} - {cmerror_desc} - FULL ACTION REQUIRED (more than 24 hours)")

        # Prepare the cmerror document
        cmerror_doc = {
            "router_name": cmerror_device,
            "cmerror_id": cmerror_id,
            "cmerror_count": cmerror_count,
            "cmerror_update": cmerror_update,
            "cmerror_slot": cmerror_slot,
            "cmerror_desc": cmerror_desc,
            "cmerror_pfe": cmerror_pfe,
            "handled": False
        }
        try:
            # Upsert ensures a document is created if it doesn't exist
            result = db.cmerrors.update_one(
                {"router_name": cmerror_device, "cmerror_id": cmerror_id},  # unique key
                {"$set": cmerror_doc},
                upsert=True
            )
            if result.matched_count:
                LOG.info(f"LOGIC: CMERROR for {cmerror_device} - {cmerror_id} UPDATED in MongoDB")
            else:
                LOG.info(f"LOGIC: CMERROR for {cmerror_device} - {cmerror_id} CREATED in MongoDB")

        except Exception as e:
            LOG.error(f"LOGIC: Unable to update/create cmerror in MongoDB: {e}")
            raise SystemExit(1)
    else:
        LOG.info(f"LOGIC: CMERROR for {cmerror_device} - {cmerror_desc} - NO COUNT INCREASE")
        sys.exit(0)
else:
    action_required = 2 # full action required

    # Prepare the new cmerror entry
    new_error = {
        "router_name": cmerror_device,
        "cmerror_id": cmerror_id,
        "cmerror_count": cmerror_count,
        "cmerror_update": cmerror_update,
        "cmerror_slot": cmerror_slot,
        "cmerror_desc": cmerror_desc,
        "cmerror_pfe": cmerror_pfe,
        "handled": False
    }

    try:
        # Use update_one with upsert=True to ensure uniqueness
        result = db.cmerrors.update_one(
            {"router_name": cmerror_device, "cmerror_id": cmerror_id},  # unique key
            {"$set": new_error},  # update all other fields
            upsert=True
        )
        if result.matched_count:
            LOG.info(f"LOGIC: CMERROR for {cmerror_device} - {cmerror_id} updated")
        else:
            LOG.info(f"LOGIC: CMERROR for {cmerror_device} - {cmerror_id} created")

    except Exception as e:
        LOG.error(f"LOGIC: Unable to update cmerror in MongoDB: {e}")
        raise SystemExit(1)

# Step 4: For each router from the same POP, connect to the router and check if Major alarms exist for any FPC 

exesting_major_alarms = False
other_router = None

for router_name in pop_routers if pop_routers else []:
    # Skip the router where the cmerror was raised
    if router_name == cmerror_device:
        continue
    alarm_desc, err = check_fpc_major_alarm(router_name)
    if err:
        LOG.error(f"LOGIC: Unable to connect to {router_name}: {err}")
        continue
    if alarm_desc:
        exesting_major_alarms = True
        other_router = router_name

        # Override action_required to partial action only
        action_required = 1  # partial action required 
        
        LOG.info(f"LOGIC: MAJOR FPC ALARM EXISTS on {router_name}: {alarm_desc}")
        break

# Step 5: If no Major FPC alarms exist on any router in the POP, and action_required is set 

if action_required>0:
    write_log_to_influx(cmerror_device, f"On device {cmerror_device}, FPC slot {cmerror_slot} / PFE slot {cmerror_pfe} raised cmerror {cmerror_desc}", host="influxdb", port=8086, db="demo")
    
if action_required == 1:
    if exesting_major_alarms:
        LOG.info(f"LOGIC: MAJOR FPC ALARMS EXIST in POP {pop_name} - NO ACTION REQUIRED")
        write_log_to_influx(cmerror_device, f"Major FPC alarm exists also in POP {pop_name}, for router {router_name}, partial action required", host="influxdb", port=8086, db="demo")
    else:
        LOG.info(f"LOGIC: NO MAJOR FPC ALARMS in POP {pop_name} - ACTION REQUIRED LEVEL {action_required}")
        write_log_to_influx(cmerror_device, f"It's less than 24 hours the {cmerror_device} experienced the same cmerror, partial action required", host="influxdb", port=8086, db="demo")
   
    # Shut down ports attached to the affected FPC and PFE 
    interfaces_fpc_pfe, interfaces_fpc , err = get_interfaces_by_slot(cmerror_device, cmerror_slot, cmerror_pfe)
    if err:
        LOG.error(f"LOGIC: Unable to get interfaces from {cmerror_device}: {err}")
        raise SystemExit(1) 

    disable_interfaces_and_notify_noc(db, cmerror_device, cmerror_slot, cmerror_pfe, cmerror_id, cmerror_desc, interfaces_fpc_pfe)

if action_required == 2:
   # Shut down ports attached to the affected FPC 
    interfaces_fpc_pfe, interfaces_fpc , err = get_interfaces_by_slot(cmerror_device, cmerror_slot, cmerror_pfe)
    if err:
        LOG.error(f"LOGIC: Unable to get interfaces from {cmerror_device}: {err}")
        raise SystemExit(1) 

    disable_interfaces_and_notify_noc(db, cmerror_device, cmerror_slot, cmerror_pfe, cmerror_id, cmerror_desc, interfaces_fpc)

    # Then reboot the Linecard
    write_log_to_influx(cmerror_device, f"Rebooting FPC {cmerror_slot} on device {cmerror_device}", host="influxdb", port=8086, db="demo")
    err = reboot_fpc_and_wait(cmerror_device, cmerror_slot)
    if err:
        LOG.error(f"LOGIC: Unable to reboot FPC {cmerror_slot} on {cmerror_device}: {err}")
        raise SystemExit(1) 
    
    LOG.info(f"LOGIC: FPC {cmerror_slot} REBOOTED on {cmerror_device}")
    write_log_to_influx(cmerror_device, f"FPC {cmerror_slot} on device {cmerror_device} rebooted successfully", host="influxdb", port=8086, db="demo")

    # wait 10 seconds before re-enabling interfaces
    time.sleep(10)

    err = configure_interfaces_disable_state(cmerror_device, interfaces_fpc, action="enable")
    if err:
        LOG.error(f"LOGIC: Unable to enable interfaces on {cmerror_device}: {err}")
        raise SystemExit(1) 
    LOG.info(f"LOGIC: INTERFACES RE-ENABLED on {cmerror_device}")   
    write_log_to_influx(cmerror_device, f"Re-enabling interfaces attached on {cmerror_device} and FPC slot {cmerror_slot}", host="influxdb", port=8086, db="demo")

    # Wait 1 minute more before checking back chassis alarms on this router 
    time.sleep(60)
    alarm_desc, err = check_fpc_major_alarm(cmerror_device, cmerror_slot)
    if err:
        LOG.error(f"LOGIC: Unable to connect to {cmerror_device}: {err}")
        raise SystemExit(1) 
    if alarm_desc:
        LOG.error(f"LOGIC: MAJOR FPC ALARM STILL EXISTS on {cmerror_device}: {alarm_desc}")
        write_log_to_influx(cmerror_device, f"After rebooting FPC {cmerror_slot} on device {cmerror_device}, major alarm still exists: {alarm_desc}", host="influxdb", port=8086, db="demo")

        # Shutdown interfaces again for the FPC slot and PFE slot only and contact NOC team
        disable_interfaces_and_notify_noc(db, cmerror_device, cmerror_slot, cmerror_pfe, cmerror_id, cmerror_desc, interfaces_fpc_pfe)
        
    else:
        LOG.info(f"LOGIC: MAJOR FPC ALARM CLEARED on {cmerror_device}")

        # Notify NOC team
        LOG.info(f"LOGIC: NOTIFY NOC TEAM - FULL ACTION SUCCESSFUL - INTERFACES RE-ENABLED: {interfaces_fpc}")
        write_log_to_influx(cmerror_device, f"FPC {cmerror_slot} on device {cmerror_device} is back online and major alarm cleared, interfaces re-enabled", host="influxdb", port=8086, db="demo")

        mark_cmerror_as_handled(db, cmerror_device, cmerror_id)