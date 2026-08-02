# Daily Access and Same-Wi-Fi Access

> [Back to the Pi8 Access Runbook](README.md)

## Recommended: access through Tailscale

Run on the Mac:

```bash
ssh pi8
```

Confirm that the session reached the intended Pi:

```bash
hostname
whoami
tailscale ip -4
```

Expected hostname and user:

```text
pi8
pi8
```

The Mac SSH configuration resolves the short alias to the Pi's Tailscale
MagicDNS name:

```sshconfig
Host pi8 pi1 pi8.local
  HostName pi8.tail34aafe.ts.net
  AddressFamily inet
  User pi8
  IdentityFile ~/.ssh/rpi_one_key
  IdentitiesOnly yes
  AddKeysToAgent yes
  UseKeychain yes
```

Inspect the effective configuration without connecting:

```bash
ssh -G pi8 | awk '$1 == "hostname" || $1 == "user" || $1 == "identityfile" {print}'
```

## Same Wi-Fi without Tailscale

Use this fallback when both devices are on the same ordinary LAN and local
device-to-device traffic is permitted:

```bash
ssh -4 -F /dev/null \
  -i ~/.ssh/rpi_one_key \
  pi8@pi8.local
```

`-F /dev/null` is important in the current setup. It bypasses the `pi8.local`
alias in `~/.ssh/config`, allowing Bonjour to resolve the Pi's local address.

To inspect local resolution on macOS:

```bash
dscacheutil -q host -a name pi8.local
ping -c 2 pi8.local
```

## When same Wi-Fi is not enough

Local access can fail even when both devices show the same Wi-Fi name. Guest
networks, corporate networks, and phone hotspots can isolate clients or block
Bonjour multicast. Use `ssh pi8` through Tailscale in those environments.

## Copy files

Copy a file to the Pi through the configured alias:

```bash
scp ./example.txt pi8:~/
```

Copy a directory:

```bash
scp -r ./example-directory pi8:~/
```
