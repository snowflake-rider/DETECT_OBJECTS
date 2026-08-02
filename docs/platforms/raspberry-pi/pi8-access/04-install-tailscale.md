# Install and Authorize Tailscale

> [Back to the Pi8 Access Runbook](README.md)

Tailscale allows the Mac to reach the Pi when they are on different networks.
It supplies connectivity; the Pi's normal OpenSSH server still performs user
and SSH-key authentication.

Official references:

- [Install Tailscale on Linux](https://tailscale.com/docs/install/linux)
- [Stable package repository](https://pkgs.tailscale.com/stable/)
- [MagicDNS](https://tailscale.com/docs/features/magicdns)

These commands target Debian 13 `trixie`, which is the current operating system
on `pi8`. For another distribution or release, use the matching repository from
the official package page.

## 1. Confirm internet access

On the Pi:

```bash
. /etc/os-release
printf '%s %s\n' "$ID" "$VERSION_CODENAME"
dpkg --print-architecture
ip route
ping -c 2 1.1.1.1
```

Expected distribution codename and architecture are `trixie` and `arm64`.

## 2. Back up an existing repository configuration

Run these only if the target files already exist:

```bash
stamp=$(date +%Y%m%d-%H%M%S)
sudo cp -a /usr/share/keyrings/tailscale-archive-keyring.gpg \
  "/usr/share/keyrings/tailscale-archive-keyring.gpg.bak.$stamp"
sudo cp -a /etc/apt/sources.list.d/tailscale.list \
  "/etc/apt/sources.list.d/tailscale.list.bak.$stamp"
```

On a fresh install, both files are normally absent and no backup is needed.

## 3. Add the official stable repository

This method downloads repository metadata without piping an installer script
into a shell:

```bash
sudo install -d -m 0755 /usr/share/keyrings

curl -fsSL \
  https://pkgs.tailscale.com/stable/debian/trixie.noarmor.gpg \
  | sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null

curl -fsSL \
  https://pkgs.tailscale.com/stable/debian/trixie.tailscale-keyring.list \
  | sudo tee /etc/apt/sources.list.d/tailscale.list >/dev/null

sudo chmod 0644 \
  /usr/share/keyrings/tailscale-archive-keyring.gpg \
  /etc/apt/sources.list.d/tailscale.list
```

## 4. Install and start Tailscale

```bash
sudo apt update
sudo apt install tailscale
sudo systemctl enable --now tailscaled
```

Verify:

```bash
tailscale version
systemctl is-enabled tailscaled
systemctl is-active tailscaled
```

## 5. Authorize the Pi

```bash
sudo tailscale up
```

Open the one-time URL printed by the command. Sign in with the same Tailscale
account used by the Mac and approve the Pi.

Verify the result:

```bash
tailscale status
tailscale ip -4
tailscale status --json | grep -m1 '"DNSName"'
```

For the current Pi, the expected identity is:

```text
pi8.tail34aafe.ts.net
100.109.1.106
```

## 6. Test from the Mac

```bash
/Applications/Tailscale.app/Contents/MacOS/Tailscale status
/Applications/Tailscale.app/Contents/MacOS/Tailscale ping pi8
```

Test standard OpenSSH through the tailnet before changing aliases:

```bash
ssh -4 -F /dev/null \
  -i ~/.ssh/rpi_one_key \
  pi8@pi8.tail34aafe.ts.net
```

## 7. Configure the short SSH alias

Back up the Mac config:

```bash
cp -p ~/.ssh/config \
  "$HOME/.ssh/config.bak.$(date +%Y%m%d-%H%M%S)"
```

Then ensure `~/.ssh/config` contains a `pi8` entry using the MagicDNS name:

```sshconfig
Host pi8
  HostName pi8.tail34aafe.ts.net
  AddressFamily inet
  User pi8
  IdentityFile ~/.ssh/rpi_one_key
  IdentitiesOnly yes
  AddKeysToAgent yes
  UseKeychain yes
```

Test:

```bash
ssh -G pi8 | grep -E '^(hostname|user|identityfile) '
ssh pi8
```

## Reauthorization

If the Pi's Tailscale key expires or its machine authorization is removed:

```bash
sudo tailscale up --force-reauth
```

Do not disable key expiry globally merely to avoid maintenance. Reauthorize the
device or deliberately adjust the policy for a trusted, physically protected
device.
