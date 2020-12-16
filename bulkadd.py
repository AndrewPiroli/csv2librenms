import config
import csv
from http.client import HTTPConnection, HTTPSConnection
import json

# Setup Requests Headers
headers = {
    "Content-Type": "application/json",
    "Accept-Language": "en-US,en;q=0.5",
    "User-Agent": "AndrewPiroli/csv2librenms",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "X-Auth-Token": config.librenms_apikey,
    "Connection": "keep-alive",
}

def mk_connection():
    connection = None
    connector = HTTPSConnection if config.use_https else HTTPSConnection
    if config.use_https and config.disable_tls_cert_check:
        try:
            import ssl
            connection = connector(config.librenms_ipaddress, context=ssl._create_unverified_context())
        except ImportError:
            print("SSL module not available, it must be built into python to support your requested operation")
            connection = connector(config.librenms_ipaddress)
    else:
        connection = connector(config.librenms_ipaddress)
    return connection

def device_add(add_request):
    connection = mk_connection()
    connection.request("POST", "/api/v0/devices", json.dumps(add_request), headers)
    response = connection.getresponse()
    connection.close()
    data = str(response.read())
    print(f"{response.status} {response.reason} : {data}")


def process_csv(csvfile):
    with open(csvfile) as device_list:
        dialect = csv.Sniffer().sniff(device_list.read())
        device_list.seek(0)
        reader = csv.reader(device_list, dialect)
        header = next(reader)
        for entry in reader:
            yield dict(zip(header, entry))


if __name__ == "__main__":
    for row in process_csv("data/bulkadd.csv"):
        if row["version"] in ("v1", "v2c"):
            device_info = {
                "community": row["v1v2community"],
            }
        elif row["version"] == "v3":
            device_info = {
                "authlevel": row["v3authlevel"],
                "authname": row["v3authname"],
                "authpass": row["v3authpass"],
                "authalgo": row["v3authalgo"],
                "cryptopass": row["v3cryptopass"],
                "cryptoalgo": row["v3cryptoalgo"],
            }
        else:
            print(f"FATAL ERROR: snmp version not recognized {row}")
            continue
        device_info.update({"hostname": row["hostname"], "version": row["version"]})
        device_add(device_info)
