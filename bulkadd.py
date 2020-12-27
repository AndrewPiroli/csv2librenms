import config
import csv
from http.client import HTTPConnection, HTTPSConnection
import json
import multiprocessing as mp
from queue import Empty as QEmptyException

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
    return device_info


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
        if connection is None or closed:
            connection = mk_connection()
        connection.request("POST", config.api_endpoint, json.dumps(request), headers)
        response = connection.getresponse()
        closed = response.isclosed()
        data = str(response.read().decode())
        print(f"{response.status} {response.reason} : {data}")
        if config.debug_mode and closed:
            print("Connection closed by server: will reopen on next request")


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
    request_q = mp.Queue()
    request_process = mp.Process(target=device_add, args=(request_q,))
    request_process.start()
    for row in process_csv("data/bulkadd.csv"):
        device_info = {"hostname": row["hostname"], "version": row["version"]}
        if row["version"] in ("v1", "v2c"):
            update_if_exists(device_info, "community", "v1v2community", row)
        elif row["version"] == "v3":
            device_info = update_if_exists(device_info, "authlevel", "v3authlevel", row)
            device_info = update_if_exists(device_info, "authname", "v3authname", row)
            device_info = update_if_exists(device_info, "authpass", "v3authpass", row)
            device_info = update_if_exists(device_info, "authalgo", "v3authalgo", row)
            device_info = update_if_exists(
                device_info, "cryptopass", "v3cryptopass", row
            )
            device_info = update_if_exists(
                device_info, "cryptoalgo", "v3cryptoalgo", row
            )
        elif row["version"] == "icmponly":
            device_info.pop("version", None)
            device_info.update({"snmp_disable": True})
            device_info = update_if_exists(device_info, "os", "os", row)
            device_info = update_if_exists(device_info, "hardware", "hardware", row)
        else:
            print(f"FATAL ERROR: snmp version not recognized {row}")
            continue
        device_info = update_if_exists(device_info, "overwrite_ip", "overwrite_ip", row)
        device_info = update_if_exists(device_info, "port", "port", row)
        device_info = update_if_exists(device_info, "transport", "transport", row)
        device_info = update_if_exists(device_info, "poller_group", "poller_group", row)
        device_info = update_if_exists(device_info, "force_add", "force_add", row)
        request_q.put(device_info)
    request_q.put("die")
    request_process.join()
