import config
import math
import sys
import csv
import http.client

# Setup Requests Headers
headers = {
    "Content-Type": "application/json",
    "Accept-Language": "en-US,en;q=0.5",
    "User-Agent": "AndrewPiroli/csv2librenms",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "X-Auth-Token": config.librenms_apikey,
    "Connection": "keep-alive",
}


def device_add(add_request):
    api_url = f"{config.request_type}://{config.librenms_ipaddress}/api/v0/devices"
    connection = (
        http.client.HTTPSConnection(api_url)
        if config.use_https
        else http.client.HTTPConnection(api_url)
    )
    connection.request("POST", "", add_request, headers)
    response = connection.getresponse()
    data = str(response.data())
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
                "version": row["version"],
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
            print("FATAL ERROR: snmp version not recognized")
            continue
        device_info.update({"hostname": row["hostname"], "version": row["version"]})
        device_add(device_info)
