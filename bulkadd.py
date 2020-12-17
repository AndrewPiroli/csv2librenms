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


def device_add(add_request):
    connection = mk_connection()
    connection.request("POST", config.api_endpoint, json.dumps(add_request), headers)
    response = connection.getresponse()
    data = str(response.read())
    connection.close()
    print(f"{response.status} {response.reason} : {data}")


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
    for row in process_csv("data/bulkadd.csv"):
        device_info = {"hostname": row["hostname"], "version": row["version"]}
        if row["version"] in ("v1", "v2c"):
            device_info.update(
                {
                    "community": row["v1v2community"],
                }
            )
        elif row["version"] == "v3":
            device_info.update(
                {
                    "authlevel": row["v3authlevel"],
                    "authname": row["v3authname"],
                    "authpass": row["v3authpass"],
                    "authalgo": row["v3authalgo"],
                    "cryptopass": row["v3cryptopass"],
                    "cryptoalgo": row["v3cryptoalgo"],
                }
            )
        else:
            print(f"FATAL ERROR: snmp version not recognized {row}")
            continue
        device_add(device_info)
