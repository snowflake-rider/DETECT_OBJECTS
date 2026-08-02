# Troubleshooting

> [Back to Pi8 Access](README.md)

Try these connection methods in order:

1. `ssh pi8`
2. [Same-Wi-Fi access](01-daily-and-same-wifi.md)
3. [Direct Ethernet](02-direct-ethernet.md)
4. A monitor and keyboard connected to the Pi

## `ssh pi8` fails

On the Mac:

```bash
/Applications/Tailscale.app/Contents/MacOS/Tailscale status
/Applications/Tailscale.app/Contents/MacOS/Tailscale ping pi8
ssh -G pi8 | grep -E '^(hostname|user|identityfile) '
ssh -vv pi8
```

On the Pi:

```bash
systemctl status tailscaled --no-pager
tailscale status
```

## `pi8.local` fails

On the Mac:

```bash
dscacheutil -q host -a name pi8.local
dns-sd -G v4v6 pi8.local
```

If nothing is found, the network may block communication between devices.

## SSH says `Permission denied`

On the Mac:

```bash
chmod 600 ~/.ssh/rpi_one_key

ssh -F /dev/null \
  -o IdentitiesOnly=yes \
  -i ~/.ssh/rpi_one_key \
  pi8@pi8.tail34aafe.ts.net
```

On the Pi, using a monitor or another working login:

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

Do not overwrite `authorized_keys`; it may contain other valid keys.

## SSH says the host changed

Stop and confirm that the Pi was deliberately replaced or reimaged. Only then
remove the old entry:

```bash
ssh-keygen -R pi8.tail34aafe.ts.net
```

Verify the new fingerprint before accepting it.

## Wi-Fi works but internet does not

On the Pi:

```bash
nmcli connection show --active
ip -4 route
ping -c 2 1.1.1.1
getent ahostsv4 tailscale.com
```

If needed, keep a working Ethernet session open while changing routes or Wi-Fi.
