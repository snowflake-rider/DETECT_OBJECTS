# Pi8 Access

## Normal connection

Run on the Mac:

```bash
ssh pi8
```

This uses Tailscale, so the Mac and Pi can be on different networks.
The Pi still uses normal OpenSSH and the Mac SSH key; Tailscale only provides
the network path.

Exit with:

```bash
exit
```

## Other connection methods

| Situation | Use |
| --- | --- |
| Normal access | `ssh pi8` |
| Same Wi-Fi without Tailscale | [Local Wi-Fi access](01-daily-and-same-wifi.md) |
| No working network | [Direct Ethernet](02-direct-ethernet.md) |
| New or reimaged Pi | [New Pi setup](03-new-pi-bootstrap.md) |
| Tailscale is missing | [Install Tailscale](04-install-tailscale.md) |
| Change Wi-Fi | [Wi-Fi management](05-wifi-management.md) |
| Something failed | [Troubleshooting](06-troubleshooting.md) |

## Current Pi

| Setting | Value |
| --- | --- |
| Hostname | `pi8` |
| Linux user | `pi8` |
| SSH key on Mac | `~/.ssh/rpi_one_key` |
| Tailscale name | `pi8.tail34aafe.ts.net` |
| Local name | `pi8.local` |
| OS | Debian 13 ARM64 |

Never commit Wi-Fi passwords or `~/.ssh/rpi_one_key`. Only the public
`~/.ssh/rpi_one_key.pub` file may be shared.
