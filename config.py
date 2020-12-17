librenms_apikey = "LIBRENMS API KEY"
librenms_ipaddress = "LIBRENMS IP or DNS NAME"
use_https = False
disable_tls_cert_check = False
debug_mode = False

# Do not edit below this line
api_endpoint = "/api/v0/devices"
if debug_mode:
    use_https = True
    disable_tls_cert_check = False
    librenms_ipaddress = "httpbin.org"
    api_endpoint = "/post"
