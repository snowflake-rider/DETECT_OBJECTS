# Wi-Fi Management

> [Back to Pi8 Access](README.md)

Run these commands on the Pi.

## View Wi-Fi

```bash
nmcli device status
nmcli connection show --active
nmcli -f IN-USE,SSID,SIGNAL,SECURITY device wifi list
```

## Add Wi-Fi

Use `--ask` so the password is not saved in shell history:

```bash
sudo nmcli --ask device wifi connect "SSID" \
  ifname wlan0 \
  name "PROFILE_NAME"
```

For a hidden network, add `hidden yes`.

Changing Wi-Fi can disconnect SSH. Use Ethernet when testing an uncertain
network.

## Use a saved network

```bash
sudo nmcli device wifi rescan
sudo nmcli connection up "PROFILE_NAME" ifname wlan0
```

## Auto-connect order

Higher priority wins.

Back up the NetworkManager profiles before changing them:

```bash
sudo cp -a /etc/NetworkManager/system-connections \
  "/etc/NetworkManager/system-connections.bak.$(date +%Y%m%d-%H%M%S)"
```

| Order | Profile | Priority |
| --- | --- | --- |
| 1 | `KCCI603_5G` | `0` |
| 2 | `iphone-hotspot` | `-1` |
| 3 | `VEEWORK02_KT5G` | `-2` |
| 4 | `VEEWORK01_KT5G` | `-3` |
| 5 | Other profiles | `-10` |

Change a priority:

```bash
sudo nmcli connection modify "PROFILE_NAME" \
  connection.autoconnect-priority -10
```

If names are duplicated, use the UUID:

```bash
nmcli -f NAME,UUID,AUTOCONNECT-PRIORITY connection show
```

## Remove a network

Find its exact UUID first:

```bash
nmcli -f NAME,UUID,TYPE connection show
sudo nmcli connection delete "CONNECTION_UUID"
```

Confirm another network or Ethernet recovery path works before deleting it.
