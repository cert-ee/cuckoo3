#!/bin/bash

# This script is used by Cuckoo rooter as an argument to 
# OpenVPN's route-up command. The env will contain the VPN server IP
# VPN default gateway, tun device name, etc.

# All CUCKOO_ vars are set by Cuckoo rooter when calling
# openvpn using --setenv.

env

if [ -z $CUCKOO_IP_PATH ]; then
    /bin/echo "Variable CUCKOO_IP_PATH not set!">&2; exit 2
fi

if [ -z $CUCKOO_ROUTING_TABLE ]; then
    /bin/echo "Variable CUCKOO_ROUTING_TABLE not set!">&2; exit 2
fi

if [ -z $CUCKOO_READY_FILE ]; then
    /bin/echo "Variable CUCKOO_READY_FILE not set!">&2; exit 2
fi

is_ip() {
  if [ "$1" != "${1#*[0-9].[0-9]}" ]; then
    return 0
  elif [ "$1" != "${1#*:[0-9a-fA-F]}" ]; then
    return 0
  fi

  return 1
}

# Add the default route of the VPN subnet for the new VPN dev to the routing table.
$CUCKOO_IP_PATH route add default via $route_vpn_gateway table $CUCKOO_ROUTING_TABLE dev $dev

# Read remote_1, remote_2, etc. Keep reading these variables until we find
# one that is not set by OpenVPN. Read all remote_<n> destinations.
remote_count=0
while true
do
    ((remote_count+=1))
    remote_name="remote_$remote_count"
    remote="${!remote_name}"
    if [ -z "$remote" ]; then
        break
    fi

    if ! is_ip "$remote"; then
      /bin/echo "Remote is not IP, getting IP for host: $remote">&2
      response=$(/usr/bin/getent ahosts "$remote" | /usr/bin/awk '{ print $1;exit }')
      if [ -z "$response" ]; then
        /bin/echo "No DNS response for $remote. Skipping it.">&2
        continue
      fi
      /bin/echo "$remote resolved to $response">&2
      remote=$response
    fi

    $CUCKOO_IP_PATH route add $remote dev $dev table $CUCKOO_ROUTING_TABLE
    /bin/echo "Added route to $remote $dev in table $CUCKOO_ROUTING_TABLE"

done

# Create the file Cuckoo asked us to created. Cuckoo will wait with using
# the VPN until this file has been created.
/usr/bin/touch "$CUCKOO_READY_FILE"
