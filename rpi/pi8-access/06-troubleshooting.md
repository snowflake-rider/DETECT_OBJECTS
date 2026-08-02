# Troubleshooting and Recovery

> [Back to the Pi8 Access Runbook](README.md)

Start with the least network-dependent access path that is available:

1. `ssh pi8` through Tailscale.
2. Direct local SSH over the same Wi-Fi.
3. Direct Ethernet and link-local IPv6.
4. Monitor and keyboard attached to the Pi.

## `ssh pi8` fails

Check Tailscale on the Mac:

```bash
/Applications/Tailscale.app/Contents/MacOS/Tailscale status
/Applications/Tailscale.app/Contents/MacOS/Tailscale ping pi8
```

Inspect the SSH alias:

```bash
ssh -G pi8 | grep -E '^(hostname|user|addressfamily|identityfile) '
```

Run SSH with diagnostic output:

```bash
ssh -vv pi8
```

If the Pi is reachable locally, inspect its Tailscale service:

```bash
systemctl status tailscaled --no-pager
tailscale status
journalctl -u tailscaled --since "15 minutes ago"
```

Restart only after inspecting the status and logs:

```bash
sudo systemctl restart tailscaled
systemctl is-active tailscaled
tailscale status
```

## Local `pi8.local` access fails

On the Mac:

```bash
dscacheutil -q host -a name pi8.local
dns-sd -G v4v6 pi8.local
ping -c 2 pi8.local
```

Try the direct local command that bypasses the Tailscale alias:

```bash
ssh -4 -F /dev/null \
  -i ~/.ssh/rpi_one_key \
  pi8@pi8.local
```

If discovery returns nothing, verify that both devices are on the same subnet
and that the network is not a guest network with client isolation. Phone
hotspots commonly block direct client-to-client access.

## Direct Ethernet access fails

Check for an active Ethernet adapter on the Mac:

```bash
networksetup -listallhardwareports
ifconfig
```

Then try link-local IPv6:

```bash
ssh -6 -F /dev/null \
  -i ~/.ssh/rpi_one_key \
  pi8@pi8.local
```

If necessary, use the manual IPv4 fallback in
[Direct Ethernet Access](02-direct-ethernet.md).

## `Permission denied (publickey)`

Confirm the Mac key exists and has safe permissions:

```bash
ls -l ~/.ssh/rpi_one_key ~/.ssh/rpi_one_key.pub
chmod 600 ~/.ssh/rpi_one_key
```

Test it explicitly:

```bash
ssh -F /dev/null \
  -o IdentitiesOnly=yes \
  -i ~/.ssh/rpi_one_key \
  pi8@pi8.tail34aafe.ts.net
```

From a monitor/keyboard or another authorized session on the Pi, verify:

```bash
ls -ld ~/.ssh
ls -l ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

Do not replace `authorized_keys` blindly; it may contain access for other
authorized users.

## Host identification changed

Stop and determine whether the Pi was deliberately reimaged or replaced. View
the remembered entry:

```bash
ssh-keygen -F pi8.tail34aafe.ts.net
```

Only after independently confirming the new Pi's host key should the stale
entry be removed:

```bash
ssh-keygen -R pi8.tail34aafe.ts.net
```

Reconnect and verify the new fingerprint before accepting it.

## Wi-Fi connects but internet fails

On the Pi:

```bash
nmcli connection show --active
ip -4 route
ping -c 2 1.1.1.1
ping -I wlan0 -c 2 1.1.1.1
getent ahostsv4 tailscale.com
```

If the forced Wi-Fi ping works while the ordinary ping fails, another
interface has an invalid or overly preferred default route. Inspect connection
route metrics before changing them:

```bash
nmcli -f NAME,TYPE,DEVICE connection show --active
nmcli connection show "PROFILE_NAME" | grep -E 'route-metric|never-default|gateway'
```

Keep a working recovery session open and back up the affected connection
profile before modifying route settings.

## Collect a compact diagnostic report

Run on the Pi:

```bash
printf '== identity ==\n'
hostnamectl
printf '== interfaces ==\n'
nmcli device status
printf '== active connections ==\n'
nmcli connection show --active
printf '== routes ==\n'
ip -4 route
printf '== ssh ==\n'
systemctl is-active ssh
printf '== tailscale ==\n'
systemctl is-active tailscaled
tailscale status
```

Review the output before sharing it. Remove public IPs, account names, or other
details that should remain private.
