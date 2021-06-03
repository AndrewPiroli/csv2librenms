import config
import csv
from http.client import HTTPConnection, HTTPSConnection
import json
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from queue import Empty as QEmptyException
from itertools import cycle
from multiprocessing import set_start_method

# Setup Requests Headers
headers = {
    "Content-Type": "application/json",
    "Accept-Language": "en-US,en;q=0.5",
    "User-Agent": "AndrewPiroli/csv2librenms",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "X-Auth-Token": config.librenms_apikey,
    "Connection": "keep-alive",
}


def update_if_exists(device_info, api_str, csv_header, csv_row):
    if config.debug_mode:
        print(f"{device_info=} {api_str=} {csv_header=} {csv_row=}")
    if csv_header in csv_row and csv_row[csv_header] != "":
        device_info.update({api_str: csv_row[csv_header]})


def mk_connection():
    connection = None
    connector = HTTPSConnection if config.use_https else HTTPConnection
    if config.use_https and config.disable_tls_cert_check:
        try:
            import ssl

            # You seriously think you know what you're talking about pylint? This is literally the shittiest linter in existence. Try to use at least half a braincell before you analyze code
            connection = connector(  # pylint: disable=unexpected-keyword-arg
                config.librenms_ipaddress, context=ssl._create_unverified_context()
            )
        except ImportError:
            print(
                "SSL module not available, it must be built into python to support your requested operation"
            )
            connection = connector(config.librenms_ipaddress)
    else:
        connection = connector(config.librenms_ipaddress)
    return connection


def device_add(request_q: mp.Queue):
    connection = None
    closed = False
    timeout = 0
    while True:
        try:
            request = request_q.get(timeout=1, block=True)
            timeout = 0
        except QEmptyException:
            timeout += 1
            if timeout == 90:
                request = "die"
            else:
                continue
        if request == "die":
            if connection is not None and closed is False:
                connection.close()
            return
        try:
            if connection is None or closed:
                connection = mk_connection()
        except Exception as err:
            e_name = get_full_class_name(err)
            print(f"device_add:mk_connection Error:  {e_name} {err}")
        try:
            response, closed, data = api_request(endpoint=config.api_endpoint, connection=connection, method="POST", request=request)
        except Exception as err:
            e_name = get_full_class_name(err)
            print(f"device_add Error in connection request or response: {e_name} {err}")
        if config.debug_mode and closed:
            print("Connection closed by server: will reopen on next request")

def api_request(endpoint, connection, method, request):
    if not isinstance(endpoint, str):
        raise TypeError("endpoint must be a str object")
    if not isinstance(connection, HTTPConnection):
        raise TypeError("connection must be a valid http.client.HTTPConnection")
    if not isinstance(method, str) or method not in ("POST", "PATCH"):
        raise TypeError("method must be \"POST\" or \"PATCH\"")
    if not isinstance(request, dict):
        raise TypeError("request must be a dict")
    response, closed, data = None, True, None
    try:
        connection.request(
            method, config.api_endpoint, json.dumps(request), headers
        )
        response = connection.getresponse()
        closed = response.isclosed()
        data = str(response.read().decode())
        print(f"{response.status} {response.reason} : {data}")
    except Exception as err:
        e_name = get_full_class_name(err)
        print(f"device_add Error in connection request or response: {e_name} {err}")
    finally:
        return (response, closed, data)
    

def process_csv(csvfile):
    with open(csvfile) as device_list:
        try:
            contents = [next(device_list) for _ in range(2)]  # read first 2 lines
        except StopIteration:  # The file has less than 2 lines...
            pass
        finally:
            contents = "".join(contents)
            device_list.seek(0)
        dialect = csv.Sniffer().sniff(contents)
        del contents
        reader = csv.reader(device_list, dialect)
        header = next(reader)
        for entry in reader:
            yield dict(zip(header, entry))


if __name__ == "__main__":
    set_start_method("spawn")
    # Create a round robin queue system
    # This lets us reuse a Keep-Alive HTTP connection without another process to keep track of the connection objects for each subprocess
    # I haven't tested this, so I will reccommend that most people just leave it at 1 connection, but the functionality is there for the brave.
    manager = mp.Manager()
    q_list = cycle([manager.Queue() for _ in range(config.num_connections)])
    request_process = ProcessPoolExecutor(max_workers=config.num_connections)
    for _ in range(config.num_connections):
        request_process.submit(device_add, next(q_list))
    for row in process_csv("data/bulkadd.csv"):
        if "hostname" not in row or "version" not in row:
            continue
        device_info = {"hostname": row["hostname"], "version": row["version"]}
        if row["version"] in ("v1", "v2c"):
            update_if_exists(
                device_info, "community", "v1v2community", row
            )
        elif row["version"] == "v3":
            update_if_exists(device_info, "authlevel", "v3authlevel", row)
            update_if_exists(device_info, "authname", "v3authname", row)
            update_if_exists(device_info, "authpass", "v3authpass", row)
            update_if_exists(device_info, "authalgo", "v3authalgo", row)
            update_if_exists(
                device_info, "cryptopass", "v3cryptopass", row
            )
            update_if_exists(
                device_info, "cryptoalgo", "v3cryptoalgo", row
            )
        elif row["version"] == "icmponly":
            device_info.pop("version", None)
            device_info.update({"snmp_disable": True})
            update_if_exists(device_info, "os", "os", row)
            update_if_exists(device_info, "hardware", "hardware", row)
        else:
            print(f"FATAL ERROR: snmp version not recognized {row}")
            continue
        update_if_exists(device_info, "overwrite_ip", "overwrite_ip", row)
        update_if_exists(device_info, "port", "port", row)
        update_if_exists(device_info, "transport", "transport", row)
        update_if_exists(device_info, "poller_group", "poller_group", row)
        update_if_exists(device_info, "force_add", "force_add", row)
        next(q_list).put(device_info)
    for _ in range(config.num_connections * 2):
        next(q_list).put("die")


def get_full_class_name(obj):
    module = obj.__class__.__module__
    if module is None or module == str.__class__.__module__:
        return obj.__class__.__name__
    return module + "." + obj.__class__.__name__
