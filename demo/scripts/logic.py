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
from jnpr.junos.utils.start_shell import StartShell
from slack_sdk import WebClient

# Set up logging
log_dir = "/opt/stackstorm/logs"
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, "demo_logic.log")

# Initialize logger
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# File handler
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(formatter)

# Stream (stdout) handler
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)

# Avoid duplicate handlers if reloaded
if not LOG.handlers:
    LOG.addHandler(file_handler)
    LOG.addHandler(stream_handler)

# Example usage
LOG.debug("Logger initialized. Writing to both file and stdout.")

# Set MongoDB connection parameters
MONGO_URI = "mongodb://mongo:27017/"
DB_NAME = "networkdb"

# SLACK TOKEN
SLACK_TOKEN="xoxb-9734040494420-9715232892391-1cGkjrl1qizLt3galCB50QnR"

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

        alarms = rsp.findall('.//alarm-detail', namespaces=rsp.nsmap)

        # Ensure it's always a list
        if not isinstance(alarms, (list, tuple)):
            alarms = [alarms]

        for alarm in alarms:
            alarm_class = alarm.findtext('alarm-class', default='').strip()
            alarm_description = alarm.findtext('alarm-description', default='').strip()

            # Check for major class
            if not re.search(r'major', alarm_class, re.IGNORECASE):
                continue

            # Base condition (same as before)
            if re.search(r'fpc', alarm_description, re.IGNORECASE):
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
        LOG.error(f"CMERROR: Unable to connect to {router_name} to check for Major alarms: {e}")
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
        interfaces = config.findall('.//interface', namespaces=config.nsmap) or []
        interfaces = interfaces if isinstance(interfaces, (list, tuple)) else [interfaces]

        for if_entry in interfaces:
            name = if_entry.findtext('name', default='').strip()
            if not name:
                continue

            if pattern_fpc_pfe.match(name):
                interfaces_fpc_pfe.append(name)
            elif pattern_fpc_only.match(name):
                interfaces_fpc_only.append(name)

    except (ConnectError, RpcError, Exception) as e:
        err = str(e)
    finally:
        if dev and dev.connected:
            dev.close()

    return interfaces_fpc_pfe, interfaces_fpc_only, err

def configure_interfaces_state(router_name, interfaces, action="disable"):
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

def get_evo_pfe_instance(router_name, fpc_slot, pfe_id):
    """
    Maps a PFE ID to its corresponding PFE instance number on a PTX router.

    Args:
        router_name (str): Hostname or IP of the router.
        fpc_slot (int | str): FPC slot number.
        pfe_id (str): PFE ID string (e.g., "0", "1", "2", etc.).

    Returns:
        tuple: (pfe_instance, err)
            pfe_instance (int | None): Corresponding PFE instance number, or None if not found.
            err (str): Error message if any exception occurs, otherwise empty string.
    """
    dev = None
    pfe_instance = None
    err = ""

    try:
        dev = Device(host=router_name, user="lab", passwd="lab123")
        dev.open()

        sh = StartShell(dev)
        sh.open()

        op = sh.run(f'cprod -A fpc{fpc_slot} -c "show pfe id info"')

        ppfe_to_inst = {}
        table_started = False

        for line in op[1].splitlines():
            line = line.strip()
            if not line:
                continue
            # detect table header, case-insensitive
            if re.match(r'pfeinst', line, re.IGNORECASE):
                table_started = True
                continue
            # skip separator
            if table_started and line.startswith('-'):
                continue
            # only parse lines starting with a number (PFEInst)
            if table_started and re.match(r'^\d+', line):
                parts = line.split()
                if len(parts) >= 3:
                    pfe_inst = int(parts[0])
                    ppfe_id = int(parts[2])
                    ppfe_to_inst[ppfe_id] = pfe_inst

    except (ConnectError, RpcError, Exception) as e:
        err = str(e)
    except Exception as e:
        LOG.info(f"CMERROR: get_evo_pfe_instance unexpected error {e}.")
    finally:
        if dev and dev.connected:
            dev.close()
            sh.close()

    
    pfe_instance = ppfe_to_inst.get(int(pfe_id)) if pfe_id.isdigit() else None
    return pfe_instance, err

def reboot_fpc_and_wait(router_name, fpc_slot, pfe_slot, router_type):
    """
    Reboots a Juniper FPC (linecard) and waits until it is Online with non-zero heap memory.

    Args:
        router_name (str): Hostname or IP of the router.
        fpc_slot (int | str): FPC slot number to reboot.
        pfe_slot (int | str): PFE slot number (not used for MX).
        router_type (str): "MX" or "PTX" 

    Returns:
        str: Empty string if success, otherwise an error message.
    """
    dev = None
    err = ""

    try:
        dev = Device(host=router_name, user="lab", passwd="lab123")
        dev.open()

        if router_type == "MX":
            LOG.info(f"CMERROR: Triggering reboot of FPC {fpc_slot} on {router_name}...")
            # Build custom RPC manually
            rpc = etree.Element("request-chassis-fpc")
            etree.SubElement(rpc, "slot").text = str(fpc_slot)
            etree.SubElement(rpc, "restart")
        elif router_type == "PTX":
            LOG.info(f"CMERROR: Triggering reboot of PFE {pfe_slot} of the FPC {fpc_slot} on {router_name}...")
            # Build custom RPC manually
            rpc = etree.Element("request-chassis-fpc")
            etree.SubElement(rpc, "slot").text = str(fpc_slot)
            etree.SubElement(rpc, "pfe-instance").text = str(pfe_slot)
            etree.SubElement(rpc, "restart")

        # Send the RPC
        dev.rpc(rpc)

        timeout = 10 * 60   # 10 minutes
        interval = 10       # 10 seconds between checks
        waited = 0

        while waited < timeout:
            try:
                if router_type == "MX":
                   rsp = dev.rpc.get_fpc_information(fpc_slot=str(fpc_slot))
                else:  # PTX
                   rsp = dev.rpc.get_fpc_information(fpc_slot=str(fpc_slot), pfe_instance=str(pfe_slot))

            except RpcError:
                # FPC may be unreachable during reboot
                LOG.info(f"CMERROR: [{waited}s] FPC {fpc_slot} not responding yet...")
                time.sleep(interval)
                waited += interval
                continue
            
            # Parse the response
            if router_type == "MX":
                try:
                    fpc = rsp.find('.//fpc', namespaces=rsp.nsmap)
                    if fpc is None:
                        LOG.info(f"CMERROR: [{waited}s] No FPC info yet...")
                    else:
                        state = fpc.findtext('state', default='Unknown').strip()
                        heap_str = fpc.findtext('memory-heap-utilization', default='0').strip()

                        try:
                            heap = int(heap_str)
                        except ValueError:
                            heap = 0

                        if state.lower() == "online" and heap > 0:
                            LOG.info(f"CMERROR: FPC {fpc_slot} is Online with heap {heap}%.")
                            break
                except Exception as e:
                    LOG.error(f"CMERROR: Failed to check FPC state: {e}")
                    
            if router_type == "PTX":
                try:
                    pfe_instances = rsp.findall('.//pfe-info-values', namespaces=rsp.nsmap) or []
                    pfe_instances = pfe_instances if isinstance(pfe_instances, (list, tuple)) else [pfe_instances]
                    if not pfe_instances:
                        LOG.warning("CMERROR: No PFE instances found in RPC reply.")
                    else:
                        all_online = True
                        for pfe in pfe_instances:
                            pfe_state = pfe.findtext('pfe-state', default='Unknown').strip()

                            if pfe_state.upper() != "ONLINE":
                                all_online = False

                        if all_online:
                            LOG.info(f"CMERROR: All Datapath of PFE {pfe_slot} of FPC {fpc_slot} are ONLINE")
                            break
                except Exception as e:
                    LOG.error(f"CMERROR: Failed to check PFE states: {e}")
                    
            time.sleep(interval)
            waited += interval

        if waited >= timeout:
            err = f"Timeout: FPC {fpc_slot} did not come online within 10 minutes."

    except (ConnectError, RpcError, Exception) as e:
        err = f"Error during FPC reboot: {e}"
    except Exception as e:
        LOG.info(f"CMERROR: FPC {fpc_slot} unexpected error {e}.")

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
                "measurement": "ST2LOGS",
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
        LOG.error(f"CMERROR: Unable to write log to InfluxDB: {e}")
        err = str(e)

    finally:
        try:
            client.close()
        except:
            pass
    
    try:
        client = WebClient(token=SLACK_TOKEN)

        response = client.chat_postMessage(
            channel="#noc-support",
            text=message
        )
    except Exception as e: 
       LOG.error(f"Error sending Slack message: {e.response['error']}")

    return err

def disable_interfaces(db, cmerror_device, cmerror_slot, cmerror_pfe, cmerror_id, cmerror_desc, interfaces):
    """
    Disables specified interfaces

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
    LOG.info(f"CMERROR: INTERFACES TO DISABLE on {cmerror_device}: {interfaces}")
    
    err = configure_interfaces_state(cmerror_device, interfaces, action="disable")
    if err:
        LOG.error(f"CMERROR: Unable to disable interfaces on {cmerror_device}: {err}")
        raise SystemExit(1) 
    
    LOG.info(f"CMERROR: INTERFACES DISABLED on {cmerror_device}")
    write_log_to_influx(cmerror_device, f"Disabling interfaces attached on {cmerror_device} and FPC slot {cmerror_slot} and pfe {cmerror_pfe}", host="influxdb", port=8086, db="demo")

def upsert_or_mark_cmerror(db, error=None, router_name=None, cmerror_id=None, handled=None):
    """
    Create, update, or mark a CMERROR entry in MongoDB.

    Modes:
        - Upsert mode: provide 'error' dict (must include router_name & cmerror_id)
        - Mark-handled mode: provide 'router_name', 'cmerror_id', and handled=True/False

    Args:
        db: MongoDB database handle (e.g. client["networkdb"])
        LOG: logger instance
        error (dict, optional): Full cmerror data to upsert
        router_name (str, optional): Router name (for mark-handled mode)
        cmerror_id (str, optional): CMERROR ID (for mark-handled mode)
        handled (bool, optional): Whether to mark handled/unhandled

    Returns:
        str: "created", "updated", "marked", or "not_found"
    """
    try:
        # --- Drop old single-field unique index if it exists ---
        indexes = db.cmerrors.index_information()
        for name, info in indexes.items():
            if info.get("key") == [("router_name", 1)]:
                LOG.debug(f"Dropping obsolete index: {name}")
                db.cmerrors.drop_index(name)

        # --- Ensure compound unique index (router_name, cmerror_id) ---
        db.cmerrors.create_index(
            [("router_name", 1), ("cmerror_id", 1)],
            unique=True,
            name="router_cmerror_unique"
        )

        # --- Upsert mode ---
        if error:
            if "router_name" not in error or "cmerror_id" not in error:
                raise ValueError("Error document must include 'router_name' and 'cmerror_id'")

            result = db.cmerrors.update_one(
                {"router_name": error["router_name"], "cmerror_id": error["cmerror_id"]},
                {"$set": error},
                upsert=True
            )

            if result.matched_count:
                LOG.debug(f"CMERROR: ALARM for {error['router_name']} - {error['cmerror_id']} updated")
                return "updated"
            else:
                LOG.debug(f"CMERROR: ALARM for {error['router_name']} - {error['cmerror_id']} created")
                return "created"

        # --- Mark-handled mode ---
        elif router_name and cmerror_id and handled is not None:
            result = db.cmerrors.update_one(
                {"router_name": router_name, "cmerror_id": cmerror_id},
                {"$set": {"handled": handled}}
            )

            if result.matched_count:
                state = "handled" if handled else "unhandled"
                LOG.debug(f"CMERROR: ALARM for {router_name} - {cmerror_id} marked as {state}")
                return "marked"
            else:
                LOG.warning(f"CMERROR: ALARM for {router_name} - {cmerror_id} not found")
                return "not_found"

        else:
            raise ValueError("Invalid arguments: provide either 'error' or (router_name, cmerror_id, handled)")

    except Exception as e:
        LOG.error(f"CMERROR: MongoDB operation failed: {e}")
        raise SystemExit(1)


##############################@ MAIN #############################################
# Main script logic
##################################################################################

# Get param from command line argument
try:
    param = sys.argv[1]
    LOG.debug("CMERROR: ----------------------------------------------------------------------------------- : LOGIC")
    LOG.debug(f"CMERROR: PARSES THE KAFKA MESSAGE: {param}")
except IndexError:
    LOG.error("CMERROR: No parameter provided")
    
    raise SystemExit(1) 

# Parse message, which can be JSON or a Python dict string
try:
    message_dict = json.loads(param)
except json.JSONDecodeError:
    # fallback: maybe it's a Python dict string
    LOG.warning("CMERROR: Message is not valid JSON, trying to parse as Python dict string")
    import ast
    message_dict = ast.literal_eval(param)


###############################@ PARSE MESSAGE #################################    
# Extract relevant fields from the message
################################################################################

cmerror_clear = message_dict.get('fields', {}).get('cmerror_clear', None)
cmerror_count = message_dict.get('fields', {}).get('cmerror_count', None)
cmerror_desc = message_dict.get('fields', {}).get('cmerror_desc', None)
cmerror_id = message_dict.get('fields', {}).get('cmerror_id', None)
cmerror_slot = message_dict.get('fields', {}).get('cmerror_slot', None)
cmerror_update = message_dict.get('fields', {}).get('cmerror_update', None)
# Parse tags
cmerror_component = message_dict.get('tags', {}).get('component', None)
cmerror_device = message_dict.get('tags', {}).get('device', None)
## CMERROR example: 
# /fpc/0/platformd/0/cm/0/mqss/0/MQSS_CMERROR_DRD_TOP_ECC2_PROTECT_FSET_REG_DETECTED_FL_FIFO_MEM1
# /fpc/0/platformd/0/cm/0/ytchip/1/YTCHIP_CMERROR_FLEXMEM_ECC_PROTECT_FSET_REG_DETECTED_SLICE 
split_id = cmerror_id.split('/')
cmerror_type = ""
cmerror_pfe = ""
cmerror_scope = ""
if len(split_id) > 1:
    cmerror_type = split_id[1].lower()
    if len(split_id) >= 9:
        cmerror_pfe = split_id[8].lower()
        cmerror_scope = split_id[7].lower()



##############################@ LOGIC ############################################
# Main logic starts here

# Connect to MongoDB
try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[DB_NAME]
except Exception as e:
    LOG.error(f"CMERROR: Unable to connect to MongoDB: {e}")
    
    raise SystemExit(1)

##################################################################################
# Step 1: check some conditions to exit early

if cmerror_type != "fpc":
    LOG.info(f"CMERROR: ALARM type is {cmerror_type}, not FPC - NO ACTION REQUIRED")
    
    sys.exit(0)
if cmerror_clear == 1:
    LOG.info(f"CMERROR: ALARM CLEARED for {cmerror_device} - {cmerror_desc} - NO ACTION REQUIRED")
    
    sys.exit(0)

# check if alarm is major 
alarm_desc, err = check_fpc_major_alarm(cmerror_device, cmerror_slot)
if err:
    LOG.error(f"CMERROR: Unable to connect to {cmerror_device} to check for Major alarms: {err}")
    
    raise SystemExit(1)
if not alarm_desc:
    LOG.debug(f"CMERROR: ALARM for {cmerror_device} - {cmerror_desc} is not Major - NO ACTION REQUIRED")
    sys.exit(0)

try:
    alarms = list(db.cmerrors.find({"router_name": cmerror_device}))
    if alarms:
        for alarm in alarms:
            if alarm.get("handled") == False:
                LOG.debug(f"CMERROR: Existing unhandled CMERROR: {alarm}")
                LOG.debug(f"CMERROR: Since there is already an unhandled ALARM for {cmerror_device}, SKIP THIS ALARM FOR NOW")
                LOG.debug("")
                sys.exit(0)
except Exception as e:
    LOG.error(f"CMERROR: Unable to fetch CMERRORs for {cmerror_device}: {e}")
    
    raise SystemExit(1)

##################################################################################
# Step 2: check some data from MongoDB

try:
    # --- 1️⃣ Get router info ---
    router = db.routers.find_one({"router_name": cmerror_device}, {"_id": 0})
    if not router:
        LOG.error(f"CMERROR: Router {cmerror_device} not found in MongoDB")
        
        raise SystemExit(1)
    
    router_model = router.get("router_model").lower()
    if not re.search(r'mx|ptx', router_model):
        LOG.error(f"CMERROR: Router model is {router_model}, not MX or PTX - MODEL NOT SUPPORTED - NO ACTION REQUIRED")
        
        raise SystemExit(0)
    else:
        router_type = "MX" if re.search(r'mx', router_model) else "PTX"
    
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
    LOG.error(f"CMERROR: Unable to fetch data from MongoDB: {e}")
    
    raise SystemExit(1)

##################################################################################
# Step 3: Check if this cmerror_id already exists for this device

##################################################################################
# Default action states:
# 0 = no action required
# 1 = partial action required (update within 24h)
# 2 = full action required (new or >24h old)
action_required = 0
less_than_24h = False
if cm_error and cm_error.get("handled"):
    previous_update = cm_error.get("cmerror_update")
    # Skip if same timestamp
    if cmerror_update == previous_update:
        LOG.debug(f"CMERROR: ALARM for {cmerror_device} - {cmerror_desc} - NO UPDATE (same timestamp)\n")
        sys.exit(0)

    # Calculate time delta in seconds
    time_diff = (cmerror_update - previous_update) / 1000

    if time_diff < 86400:  # < 24h
        action_required = 1
        less_than_24h = True
    else:
        action_required = 2

else:
    action_required = 2

# Prepare and upsert the ALARM entry
the_error = {
    "router_name": cmerror_device,
    "cmerror_id": cmerror_id,
    "cmerror_count": cmerror_count,
    "cmerror_update": cmerror_update,
    "cmerror_slot": cmerror_slot,
    "cmerror_desc": cmerror_desc,
    "cmerror_pfe": cmerror_pfe,
    "handled": False,
}

upsert_or_mark_cmerror(db, error=the_error)

##################################################################################
# Step 4: For each router from the same POP, connect to the router and check if Major alarms exist for any FPC 

exesting_major_alarms = False
other_router = None

for router_name in pop_routers if pop_routers else []:
    # Skip the router where the ALARM was raised
    if router_name == cmerror_device:
        continue
    alarm_desc, err = check_fpc_major_alarm(router_name)
    if err:
        LOG.error(f"CMERROR: Unable to connect to {router_name}: {err}")
        continue
    if alarm_desc:
        exesting_major_alarms = True
        other_router = router_name

        # Override action_required to partial action only
        action_required = 1  # partial action required 
        
        LOG.debug(f"CMERROR: MAJOR FPC ALARM EXISTS on {router_name}: {alarm_desc}")
        break

##################################################################################
# Step 5: If no Major FPC alarms exist on any router in the POP, and action_required is set 

if action_required>0:
    write_log_to_influx(cmerror_device, f"On device {cmerror_device}, FPC slot {cmerror_slot} / PFE slot {cmerror_pfe} raised cmerror {cmerror_desc}", host="influxdb", port=8086, db="demo")
    write_log_to_influx(cmerror_device, f"Follow details here: https://rtme-ubuntu-07.englab.juniper.net:8080/d/democlosedloop/demo-closed-loop?orgId=1&refresh=5s&var-rtr={cmerror_device}", host="influxdb", port=8086, db="demo")

if action_required == 1:
    # You need the support of NOC team to open a ticket and manage this case manually
    LOG.info(f"CMERROR: NOC ACTION REQUIRED - CONTACT NOC for FPC {cmerror_slot} on {cmerror_device}")

    if exesting_major_alarms:
        LOG.info(f"CMERROR: Major FPC alarm exists also in POP {pop_name}, for router {other_router}, NOC action required")
        write_log_to_influx(cmerror_device, f"Major FPC alarm exists also in POP {pop_name}, for router {router_name}, NOC action required", host="influxdb", port=8086, db="demo")
    if less_than_24h:    
        LOG.info(f"CMERROR: It's less than 24 hours the {cmerror_device} experienced the same cmerror, NOC action required")
        write_log_to_influx(cmerror_device, f"It's less than 24 hours the {cmerror_device} experienced the same cmerror, NOC action required", host="influxdb", port=8086, db="demo")
   
    write_log_to_influx(cmerror_device, f"NOC team should open a ticket for device {cmerror_device} and FPC slot {cmerror_slot} due to cmerror {cmerror_desc}", host="influxdb", port=8086, db="demo")
    write_log_to_influx(cmerror_device, f"For more details - Use show system error {cmerror_id} on {cmerror_device}", host="influxdb", port=8086, db="demo")
    upsert_or_mark_cmerror(db, router_name=cmerror_device, cmerror_id=cmerror_id, handled=True)

if action_required == 2:
    write_log_to_influx(cmerror_device, f"A new cmerror has been detected on {cmerror_device}, automatic recovery triggered", host="influxdb", port=8086, db="demo")

    if router_type == "MX":
        # Shut down ports attached to the affected FPC 
        LOG.info(f"CMERROR: AUTOMATIC ACTION - SHUTTING DOWN INTERFACES AND REBOOTING FPC {cmerror_slot} on {cmerror_device}")
        interfaces_fpc_pfe, interfaces_fpc , err = get_interfaces_by_slot(cmerror_device, cmerror_slot, cmerror_pfe)
        if err:
            LOG.error(f"CMERROR: Unable to get interfaces from {cmerror_device}: {err}")
            write_log_to_influx(cmerror_device, f"Unable to reboot FPC {cmerror_slot} on {cmerror_device}", host="influxdb", port=8086, db="demo")
            write_log_to_influx(cmerror_device, f"For more details - Use show system error {cmerror_id} on {cmerror_device}", host="influxdb", port=8086, db="demo")
            write_log_to_influx(cmerror_device, f"Need manual action on {cmerror_device}", host="influxdb", port=8086, db="demo")
            upsert_or_mark_cmerror(db, router_name=cmerror_device, cmerror_id=cmerror_id, handled=True)
            
            raise SystemExit(1) 
        disable_interfaces(db, cmerror_device, cmerror_slot, cmerror_pfe, cmerror_id, cmerror_desc, interfaces_fpc)
        write_log_to_influx(cmerror_device, f"Disabling interfaces attached on {cmerror_device}, and FPC slot {cmerror_slot}", host="influxdb", port=8086, db="demo")
        write_log_to_influx(cmerror_device, f"Rebooting FPC {cmerror_slot} on device {cmerror_device}", host="influxdb", port=8086, db="demo")
        err = reboot_fpc_and_wait(cmerror_device, cmerror_slot, cmerror_pfe, router_type)
        if err:
            LOG.error(f"CMERROR: Unable to reboot FPC {cmerror_slot} on {cmerror_device}: {err}")
            write_log_to_influx(cmerror_device, f"Unable to reboot FPC {cmerror_slot} on {cmerror_device}", host="influxdb", port=8086, db="demo")
            write_log_to_influx(cmerror_device, f"For more details - Use show system error {cmerror_id} on {cmerror_device}", host="influxdb", port=8086, db="demo")
            write_log_to_influx(cmerror_device, f"Need manual action on {cmerror_device}", host="influxdb", port=8086, db="demo")
            upsert_or_mark_cmerror(db, router_name=cmerror_device, cmerror_id=cmerror_id, handled=True)
            
            raise SystemExit(1) 
        LOG.info(f"CMERROR: FPC {cmerror_slot} REBOOTED on {cmerror_device}")
        write_log_to_influx(cmerror_device, f"FPC {cmerror_slot} on device {cmerror_device} rebooted successfully", host="influxdb", port=8086, db="demo")

    if router_type == "PTX":
        
        if "pfe" in cmerror_scope:
            # get the PFE instance number from the PFE ID
            cmerror_pfe_instance, err = get_evo_pfe_instance(cmerror_device, cmerror_slot, cmerror_pfe)
            if err:
                LOG.error(f"CMERROR: Unable to get PFE instance from {cmerror_device}: {err}")
                write_log_to_influx(cmerror_device, f"Unable to reboot PFE {cmerror_pfe} on FPC {cmerror_slot} on {cmerror_device}", host="influxdb", port=8086, db="demo")
                write_log_to_influx(cmerror_device, f"For more details - Use show system error {cmerror_id} on {cmerror_device}", host="influxdb", port=8086, db="demo")
                write_log_to_influx(cmerror_device, f"Need manual action on {cmerror_device}", host="influxdb", port=8086, db="demo")
                upsert_or_mark_cmerror(db, router_name=cmerror_device, cmerror_id=cmerror_id, handled=True)
                
                raise SystemExit(1) 
            if cmerror_pfe_instance is None:
                LOG.error(f"CMERROR: Unable to map PFE ID {cmerror_pfe} to instance on {cmerror_device}")
                write_log_to_influx(cmerror_device, f"Unable to reboot PFE {cmerror_pfe} on FPC {cmerror_slot} on {cmerror_device}", host="influxdb", port=8086, db="demo")
                write_log_to_influx(cmerror_device, f"For more details - Use show system error {cmerror_id} on {cmerror_device}", host="influxdb", port=8086, db="demo")
                write_log_to_influx(cmerror_device, f"Need manual action on {cmerror_device}", host="influxdb", port=8086, db="demo")
                upsert_or_mark_cmerror(db, router_name=cmerror_device, cmerror_id=cmerror_id, handled=True)
                
                raise SystemExit(1) 
            # Shut down ports attached to the affected FPC and PFE
            LOG.info(f"CMERROR: AUTOMATIC ACTION - SHUTTING DOWN INTERFACES AND REBOOTING PFE {cmerror_pfe_instance} of FPC {cmerror_slot} on {cmerror_device}")
            LOG.info(f"CMERROR: RESOLVE PFE INSTANCE {cmerror_pfe_instance} for PFE_ID {cmerror_pfe}")
            cmerror_pfe = str(cmerror_pfe_instance)
        elif "chip" in cmerror_scope:
            LOG.info(f"CMERROR: AUTOMATIC ACTION - SHUTTING DOWN INTERFACES AND REBOOTING PFE {cmerror_pfe} of FPC {cmerror_slot} on {cmerror_device}")
        else:
            LOG.info(f"CMERROR: AUTOMATIC ACTION - SHUTTING DOWN INTERFACES AND REBOOTING FPC {cmerror_slot} on {cmerror_device}")

        # Shut down ports attached to the affected FPC and PFE 
        interfaces_fpc_pfe, interfaces_fpc , err = get_interfaces_by_slot(cmerror_device, cmerror_slot, cmerror_pfe)
        if err:
            LOG.error(f"CMERROR: Unable to get interfaces from {cmerror_device}: {err}")
            write_log_to_influx(cmerror_device, f"Unable to reboot on PFE or FPC on {cmerror_device}", host="influxdb", port=8086, db="demo")
            write_log_to_influx(cmerror_device, f"For more details - Use show system error {cmerror_id} on {cmerror_device}", host="influxdb", port=8086, db="demo")
            write_log_to_influx(cmerror_device, f"Need manual action on {cmerror_device}", host="influxdb", port=8086, db="demo")
            upsert_or_mark_cmerror(db, router_name=cmerror_device, cmerror_id=cmerror_id, handled=True)
            
            raise SystemExit(1) 
        
        if "pfe" in cmerror_scope or "chip" in cmerror_scope:
            # Shut down ports attached to the affected FPC and PFE
            disable_interfaces(db, cmerror_device, cmerror_slot, cmerror_pfe, cmerror_id, cmerror_desc, interfaces_fpc_pfe)
            write_log_to_influx(cmerror_device, f"Disabling interfaces attached on {cmerror_device}, PFE {cmerror_slot} and FPC slot {cmerror_slot}", host="influxdb", port=8086, db="demo")
            write_log_to_influx(cmerror_device, f"Rebooting PFE {cmerror_pfe} of FPC {cmerror_slot} on device {cmerror_device}", host="influxdb", port=8086, db="demo")
            err = reboot_fpc_and_wait(cmerror_device, cmerror_slot, cmerror_pfe, router_type)
            if err:
                LOG.error(f"CMERROR: Unable to reboot PFE {cmerror_pfe} of FPC {cmerror_slot} on {cmerror_device}: {err}")
                write_log_to_influx(cmerror_device, f"Unable to reboot PFE {cmerror_pfe} on FPC {cmerror_slot} on {cmerror_device}", host="influxdb", port=8086, db="demo")
                write_log_to_influx(cmerror_device, f"For more details - Use show system error {cmerror_id} on {cmerror_device}", host="influxdb", port=8086, db="demo")
                write_log_to_influx(cmerror_device, f"Need manual action on {cmerror_device}", host="influxdb", port=8086, db="demo")
                upsert_or_mark_cmerror(db, router_name=cmerror_device, cmerror_id=cmerror_id, handled=True)
                
                raise SystemExit(1)  
            LOG.info(f"CMERROR: PFE {cmerror_pfe} of FPC {cmerror_slot} REBOOTED on {cmerror_device}")
            write_log_to_influx(cmerror_device, f"PFE {cmerror_pfe} of FPC {cmerror_slot} on device {cmerror_device} rebooted successfully", host="influxdb", port=8086, db="demo")
                                   
        else:
            # Shut down ports attached to the affected FPC only
            disable_interfaces(db, cmerror_device, cmerror_slot, cmerror_pfe, cmerror_id, cmerror_desc, interfaces_fpc)
            write_log_to_influx(cmerror_device, f"Disabling interfaces attached on {cmerror_device}, and FPC slot {cmerror_slot}", host="influxdb", port=8086, db="demo")
            # Override type to reboot the whole FPC
            err = reboot_fpc_and_wait(cmerror_device, cmerror_slot, cmerror_pfe, "MX")
            if err:
                LOG.error(f"CMERROR: Unable to reboot FPC {cmerror_slot} on {cmerror_device}: {err}")
                write_log_to_influx(cmerror_device, f"Unable to reboot FPC {cmerror_slot} on {cmerror_device}", host="influxdb", port=8086, db="demo")
                write_log_to_influx(cmerror_device, f"For more details - Use show system error {cmerror_id} on {cmerror_device}", host="influxdb", port=8086, db="demo")
                write_log_to_influx(cmerror_device, f"Need manual action on {cmerror_device}", host="influxdb", port=8086, db="demo")
                upsert_or_mark_cmerror(db, router_name=cmerror_device, cmerror_id=cmerror_id, handled=True)
                
                raise SystemExit(1) 
            LOG.info(f"CMERROR: FPC {cmerror_slot} REBOOTED on {cmerror_device}")
            write_log_to_influx(cmerror_device, f"FPC {cmerror_slot} on device {cmerror_device} rebooted successfully", host="influxdb", port=8086, db="demo")
        
    # wait 10 seconds 
    time.sleep(10)

    # Check if alarm is cleared
    alarm_desc, err = check_fpc_major_alarm(cmerror_device, cmerror_slot)
    if err:
        LOG.error(f"CMERROR: Unable to connect to {cmerror_device}: {err}")
        write_log_to_influx(cmerror_device, f"Unable to sanity check FPC {cmerror_slot} on {cmerror_device} after reboot", host="influxdb", port=8086, db="demo")
        write_log_to_influx(cmerror_device, f"For more details - Use show system error {cmerror_id} on {cmerror_device}", host="influxdb", port=8086, db="demo")
        write_log_to_influx(cmerror_device, f"Need manual action on {cmerror_device}", host="influxdb", port=8086, db="demo")
        upsert_or_mark_cmerror(db, router_name=cmerror_device, cmerror_id=cmerror_id, handled=True)
        
        raise SystemExit(1) 
    
    if alarm_desc:
        LOG.error(f"CMERROR: MAJOR FPC ALARM STILL EXISTS AFTER REBOOT on {cmerror_device}: {alarm_desc}")
        write_log_to_influx(cmerror_device, f"After rebooting FPC {cmerror_slot} on device {cmerror_device}, major alarm still exists: {alarm_desc}", host="influxdb", port=8086, db="demo")
        write_log_to_influx(cmerror_device, f"For more details - Use show system error {cmerror_id} on {cmerror_device}", host="influxdb", port=8086, db="demo")
        write_log_to_influx(cmerror_device, f"Need manual action on {cmerror_device}", host="influxdb", port=8086, db="demo")
        upsert_or_mark_cmerror(db, router_name=cmerror_device, cmerror_id=cmerror_id, handled=True)
        
        raise SystemExit(1)

    # Otherwise re-enable the interfaces
    if router_type == "MX":
        err = configure_interfaces_state(cmerror_device, interfaces_fpc, action="enable")
        if err:
            LOG.error(f"CMERROR: Unable to enable interfaces on {cmerror_device}: {err}")
            write_log_to_influx(cmerror_device, f"Unable to re-enable interfaces on {cmerror_device}", host="influxdb", port=8086, db="demo")
            write_log_to_influx(cmerror_device, f"Need manual action on {cmerror_device}", host="influxdb", port=8086, db="demo")
            upsert_or_mark_cmerror(db, router_name=cmerror_device, cmerror_id=cmerror_id, handled=True)
            
            raise SystemExit(1) 
        LOG.info(f"CMERROR: INTERFACES RE-ENABLED on {cmerror_device}")   
        write_log_to_influx(cmerror_device, f"Re-enabling interfaces attached on {cmerror_device} and FPC slot {cmerror_slot}", host="influxdb", port=8086, db="demo")
    elif router_type == "PTX":
        if "pfe" in cmerror_scope or "chip" in cmerror_scope:
            err = configure_interfaces_state(cmerror_device, interfaces_fpc_pfe, action="enable")
            if err:
                LOG.error(f"CMERROR: Unable to enable interfaces on {cmerror_device}: {err}")
                write_log_to_influx(cmerror_device, f"Unable to re-enable interfaces on {cmerror_device}", host="influxdb", port=8086, db="demo")
                write_log_to_influx(cmerror_device, f"Need manual action on {cmerror_device}", host="influxdb", port=8086, db="demo")
                upsert_or_mark_cmerror(db, router_name=cmerror_device, cmerror_id=cmerror_id, handled=True)
                
                raise SystemExit(1) 
            LOG.info(f"CMERROR: INTERFACES RE-ENABLED on {cmerror_device}")   
            write_log_to_influx(cmerror_device, f"Re-enabling interfaces attached on {cmerror_device}, PFE {cmerror_pfe} and FPC slot {cmerror_slot}", host="influxdb", port=8086, db="demo")
        else:
            err = configure_interfaces_state(cmerror_device, interfaces_fpc, action="enable")
            if err:
                LOG.error(f"CMERROR: Unable to enable interfaces on {cmerror_device}: {err}")
                write_log_to_influx(cmerror_device, f"Unable to re-enable interfaces on {cmerror_device}", host="influxdb", port=8086, db="demo")
                write_log_to_influx(cmerror_device, f"Need manual action on {cmerror_device}", host="influxdb", port=8086, db="demo")
                upsert_or_mark_cmerror(db, router_name=cmerror_device, cmerror_id=cmerror_id, handled=True)
                
                raise SystemExit(1) 
            LOG.info(f"CMERROR: INTERFACES RE-ENABLED on {cmerror_device}")   

            write_log_to_influx(cmerror_device, f"Re-enabling interfaces attached on {cmerror_device} and FPC slot {cmerror_slot}", host="influxdb", port=8086, db="demo")
        
    # Wait 1 minute more before checking back chassis alarms on this router - in case traffic triggers something
    time.sleep(60)
    alarm_desc, err = check_fpc_major_alarm(cmerror_device, cmerror_slot)
    if err:
        LOG.error(f"CMERROR: Unable to connect to {cmerror_device}: {err}")
        write_log_to_influx(cmerror_device, f"Unable to sanity check FPC {cmerror_slot} on {cmerror_device} after reboot", host="influxdb", port=8086, db="demo")
        write_log_to_influx(cmerror_device, f"For more details - Use show system error {cmerror_id} on {cmerror_device}", host="influxdb", port=8086, db="demo")
        write_log_to_influx(cmerror_device, f"Need manual action on {cmerror_device}", host="influxdb", port=8086, db="demo")
        upsert_or_mark_cmerror(db, router_name=cmerror_device, cmerror_id=cmerror_id, handled=True)
        
        raise SystemExit(1) 
    
    if alarm_desc:
        LOG.error(f"CMERROR: MAJOR FPC ALARM STILL EXISTS on {cmerror_device}: {alarm_desc}")
        write_log_to_influx(cmerror_device, f"After rebooting FPC {cmerror_slot} on device {cmerror_device}, major alarm still exists: {alarm_desc}", host="influxdb", port=8086, db="demo")
        write_log_to_influx(cmerror_device, f"Need manual action on {cmerror_device}", host="influxdb", port=8086, db="demo")
    else:
        LOG.info(f"CMERROR: MAJOR FPC ALARM CLEARED on {cmerror_device} EVERYTHING BACK TO NORMAL")
        write_log_to_influx(cmerror_device, f"FPC {cmerror_slot} on device {cmerror_device} is back online and major alarm cleared, interfaces re-enabled", host="influxdb", port=8086, db="demo")

    upsert_or_mark_cmerror(db, router_name=cmerror_device, cmerror_id=cmerror_id, handled=True)
    
