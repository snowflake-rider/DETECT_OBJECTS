# Pi8 Access Runbook

This directory documents how to reach the Raspberry Pi named `pi8` from the
Mac, recover access with a direct Ethernet cable, prepare a new Pi, manage
Wi-Fi, and install Tailscale.

## Quick answer

For normal use, run this on the Mac:

```bash
ssh pi8
```

This command currently uses Tailscale, not the local Wi-Fi address. It works
when the Mac and Pi have internet access and are signed in to the same
Tailscale network. They do not need to be on the same physical network.

Exit the Pi with:

```bash
exit
```

## Current configuration

| Setting | Value |
| --- | --- |
| Pi hostname and Linux user | `pi8` |
| Mac private key | `~/.ssh/rpi_one_key` |
| Tailscale DNS name | `pi8.tail34aafe.ts.net` |
| Tailscale IP (diagnostic only) | `100.109.1.106` |
| Local Bonjour name | `pi8.local` |
| Current operating system | Debian 13 `trixie`, ARM64 |

The Tailscale IP is normally stable, but the DNS name is the preferred
identifier. Never put Wi-Fi passwords or the private SSH key in this
repository.

## Choose an access method

| Situation | Command or guide |
| --- | --- |
| Normal access from any network | `ssh pi8` |
| Same Wi-Fi, bypass Tailscale | `ssh -4 -F /dev/null -i ~/.ssh/rpi_one_key pi8@pi8.local` |
| Mac connected directly by Ethernet | `ssh -6 -F /dev/null -i ~/.ssh/rpi_one_key pi8@pi8.local` |
| Brand-new or reimaged Pi | [Bootstrap a new Pi](03-new-pi-bootstrap.md) |
| Tailscale is missing | [Install Tailscale](04-install-tailscale.md) |
| Connection is failing | [Troubleshooting](06-troubleshooting.md) |

## Guides

1. [Daily access and same-Wi-Fi access](01-daily-and-same-wifi.md)
2. [Direct Ethernet access](02-direct-ethernet.md)
3. [Bootstrap a new Pi from scratch](03-new-pi-bootstrap.md)
4. [Install and authorize Tailscale](04-install-tailscale.md)
5. [Manage Wi-Fi profiles and ranking](05-wifi-management.md)
6. [Troubleshooting and recovery](06-troubleshooting.md)

## Security model

- Standard OpenSSH runs on the Pi.
- Tailscale supplies the encrypted network path.
- The Mac authenticates to OpenSSH with `~/.ssh/rpi_one_key`.
- Tailscale SSH is not enabled; existing OpenSSH key authentication remains in
  control.
- The private key must stay on the Mac. Only its `.pub` file may be copied.

