# Direct Ethernet Access

> [Back to the Pi8 Access Runbook](README.md)

Use a direct cable when Wi-Fi or Tailscale is unavailable. This method does not
require internet access.

## Connect

1. Power on the Pi.
2. Connect the Pi's Ethernet port to the Mac's USB or Thunderbolt Ethernet
   adapter.
3. Wait approximately 30 seconds for link-local IPv6 and Bonjour discovery.
4. On the Mac, check that the adapter reports an active link:

```bash
ifconfig | grep -B 5 -A 3 'status: active'
```

Discover the Pi over Bonjour:

```bash
dns-sd -G v4v6 pi8.local
```

Stop `dns-sd` with Control-C after it reports an address.

## Connect over link-local IPv6

Run:

```bash
ssh -6 -F /dev/null \
  -i ~/.ssh/rpi_one_key \
  pi8@pi8.local
```

The direct link previously worked even when the Mac and Pi had incompatible
IPv4 addresses because IPv6 link-local discovery supplied the correct network
interface scope automatically.

## Optional IPv4 fallback

The Pi's Ethernet profile currently uses `10.10.16.72`. If IPv6 discovery does
not work, temporarily configure the Mac's USB Ethernet service with:

- Address: `10.10.16.73`
- Subnet mask: `255.255.255.0`
- Router: leave blank

Then connect with:

```bash
ssh -F /dev/null \
  -i ~/.ssh/rpi_one_key \
  pi8@10.10.16.72
```

Restore the Mac Ethernet service to DHCP after recovery unless the manual
address is intentionally permanent.

## Restore remote access

Once connected by cable:

```bash
nmcli device status
nmcli connection show --active
systemctl status ssh --no-pager
systemctl status tailscaled --no-pager
```

Bring up a saved Wi-Fi profile if necessary:

```bash
sudo nmcli connection up "VEEWORK02_KT5G" ifname wlan0
```

Switching Wi-Fi can briefly interrupt Tailscale. Keep the Ethernet session open
until `tailscale status` reports that the Pi is online again.
