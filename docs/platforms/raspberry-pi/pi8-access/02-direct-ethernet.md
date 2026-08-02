# Direct Ethernet

> [Back to Pi8 Access](README.md)

Use this when Wi-Fi and Tailscale are unavailable. Internet is not required.

## Connect

1. Power on the Pi.
2. Connect the Pi to the Mac with an Ethernet adapter.
3. Wait about 30 seconds.
4. Run on the Mac:

```bash
ssh -6 -F /dev/null \
  -i ~/.ssh/rpi_one_key \
  pi8@pi8.local
```

This uses local IPv6 and Bonjour.

## IPv4 fallback

If IPv6 does not work, temporarily configure the Mac Ethernet adapter:

- Address: `10.10.16.73`
- Subnet mask: `255.255.255.0`
- Router: blank

Then connect:

```bash
ssh -F /dev/null \
  -i ~/.ssh/rpi_one_key \
  pi8@10.10.16.72
```

Return the Mac adapter to DHCP afterward.

## Restore remote access

On the Pi:

```bash
nmcli device status
systemctl is-active ssh
systemctl is-active tailscaled
tailscale status
```

Keep Ethernet connected until Wi-Fi and Tailscale are working again.
