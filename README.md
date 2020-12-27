# csv2librenms

CSV bulk importer for LibreNMS, import devices as SNMP or ping only.

This will add a device for each row in data/bulkimport.csv.

Please add your LibreNMS API key in the config.py file. You can generate
them via the LibreNMS webgui. 

**Direction: python3 ./bulkadd.py**

#### CSV options
- **hostname**: IP/Hostname of device you want to add, required
- **version**: SNMP version of the device or "icmponly", required - Acceptable values: v1 v2c v3 icmponly
- **v1v2community**: SNMP community for v1 or v2c
- **v3authlevel**: SNMPv3 authentication level - Acceptable values: noAuthNoPriv, authNoPriv, authPriv)
- **v3authname**: SNMPv3 authentication username
- **v3authpass**: SNMPv3 authentication password
- **v3authalgo**: SNMPv3 authentication algorithm - Acceptable values: MD5, SHA
- **v3cryptopass**: SNMPv3 crypto password
- **v3cryptopass**: SNMPv3 crypto algorithm Acceptable values: AES, DES
- **os**: ICMP only, optional
- **hardware**: ICMP only, optional
- **overwite_ip**: Optional
- **port**: Optional
- **transport**: Optional
- **poller_group**: Optional
- **force_add**: Optional

The parser is smart, it will ignore options that don't make sense (like community strings when version is v3/icmponly, or v3 configurations when version is v1/v2c)

If a certain column is left blank for a given row, it is not included in the request. Most columns are optional and will take the default you set in LibreNMS global settings if left out or blank.

The only columns that are 100% required are hostname and version

#### User servicable config.py options
- **librenms_apikey**: set this to your API key generated in the web interface
- **librenms_ipaddress**: set this to either the IP or hostname of the server hosting the LibreNMS web interface - do not add the protocol prefix http:// or https://
- **use_https**: set to True to enable HTTPS
- **disable_tls_cert_check**: set to True to ignore certificate errors when using HTTPS
- **debug_mode**: set to True to print debug information and send requests to an HTTP reflection service instead of your LibreNMS
- **num_connections**: EXPIRAMENTAL: set to the number of concurrent connections to use when making API requests, this may speed up the process for large requests, but it is largely untested.
