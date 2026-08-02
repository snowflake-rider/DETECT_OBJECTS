# Wi-Fi Management

> [Back to the Pi8 Access Runbook](README.md)

The Pi uses NetworkManager through `nmcli`.

## Inspect Wi-Fi

```bash
nmcli device status
nmcli connection show --active
nmcli -f IN-USE,SSID,SIGNAL,SECURITY device wifi list
nmcli -f NAME,TYPE,AUTOCONNECT,AUTOCONNECT-PRIORITY connection show
ip -4 address show wlan0
ip route
```

Show recent NetworkManager events:

```bash
journalctl -u NetworkManager --since "10 minutes ago"
```

## Add a visible Wi-Fi network securely

Use `--ask` so the password is entered at a prompt rather than stored in shell
history or documentation:

```bash
sudo nmcli --ask device wifi connect "SSID" \
  ifname wlan0 \
  name "PROFILE_NAME"
```

For a hidden SSID:

```bash
sudo nmcli --ask device wifi connect "SSID" \
  hidden yes \
  ifname wlan0 \
  name "PROFILE_NAME"
```

Switching the active Wi-Fi can interrupt SSH. Prefer a direct Ethernet session
while adding or testing a network. A Tailscale session may reconnect after the
new Wi-Fi obtains internet access, but do not rely on that as the only recovery
path during risky changes.

## Activate a saved profile

```bash
sudo nmcli device wifi rescan
sudo nmcli connection up "VEEWORK02_KT5G" ifname wlan0
```

Verify:

```bash
nmcli -f DEVICE,STATE,CONNECTION device status
ip -4 address show wlan0
ping -I wlan0 -c 2 1.1.1.1
```

## Auto-connect ranking

NetworkManager prefers a **higher** `connection.autoconnect-priority` value.
The current setup uses zero and negative values so a smaller human rank remains
more preferred:

| Human rank | Profile | NetworkManager priority |
| --- | --- | --- |
| 1 | `KCCI603_5G` | `0` |
| 2 | `iphone-hotspot` | `-1` |
| 3 | `VEEWORK02_KT5G` | `-2` |
| 4 | `VEEWORK01_KT5G` | `-3` |
| 5 | All remaining Wi-Fi profiles | `-10` |

Before changing existing profiles, back up NetworkManager's root-protected
configuration directory:

```bash
sudo cp -a /etc/NetworkManager/system-connections \
  "/etc/NetworkManager/system-connections.bak.$(date +%Y%m%d-%H%M%S)"
```

Apply the named priorities:

```bash
sudo nmcli connection modify "KCCI603_5G" \
  connection.autoconnect-priority 0
sudo nmcli connection modify "iphone-hotspot" \
  connection.autoconnect-priority -1
sudo nmcli connection modify "VEEWORK02_KT5G" \
  connection.autoconnect-priority -2
sudo nmcli connection modify "VEEWORK01_KT5G" \
  connection.autoconnect-priority -3
```

When connection names are duplicated, use the UUID from this command instead
of the ambiguous name:

```bash
nmcli -f NAME,UUID,TYPE,AUTOCONNECT-PRIORITY connection show
sudo nmcli connection modify "CONNECTION_UUID" \
  connection.autoconnect-priority -10
```

## Remove a profile carefully

First identify it by UUID:

```bash
nmcli -f NAME,UUID,TYPE connection show
```

Delete only after confirming the exact UUID and ensuring another working
network or Ethernet recovery path is available:

```bash
sudo nmcli connection delete "CONNECTION_UUID"
```
