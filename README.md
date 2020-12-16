# csv2librenms

CSV bulk importer for LibreNMS, import devices as SNMP, ping only not supported.

This will add a device for each row in data/bulkimport.csv.

Please add your LibreNMS API key in the config.py file. You can generate
them via the LibreNMS webgui. 

**Direction: python3 ./bulkadd.py**

#### CSV - SNMP Settings
- **Hostname**: IP/Hostname of device you want to add
- **version**: SNMP version of the device. Acceptable values: v1 v2c v3
- **v1v2community**: SNMP community for v1 or v2c
- **v3authlevel**: SNMPv3 authentication level (noAuthNoPriv, authNoPriv, authPriv)
- **v3authname**: SNMPv3 authentication username
- **v3authpass**: SNMPv3 authentication password
- **v3authalgo**: SNMPv3 authentication algorithm (MD5, SHA)
- **v3cryptopass**: SNMPv3 crypto password
- **v3cryptopass**: SNMPv3 crypto algorithm (AES, DES)
