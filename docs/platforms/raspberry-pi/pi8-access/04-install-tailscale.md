# Install Tailscale

> [Back to Pi8 Access](README.md)

These commands are for Debian 13 `trixie`. For another OS, use the
[official Linux instructions](https://tailscale.com/docs/install/linux).

## 1. Confirm the Pi version

```bash
. /etc/os-release
printf '%s %s\n' "$ID" "$VERSION_CODENAME"
dpkg --print-architecture
```

Expected: Debian, `trixie`, and `arm64`.

## 2. Add the Tailscale repository

If the keyring or repository file already exists, back it up before replacing
it.

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

## 3. Install and authorize

```bash
sudo apt update
sudo apt install tailscale
sudo systemctl enable --now tailscaled
sudo tailscale up
```

Open the URL printed by `tailscale up` and approve the Pi.

Verify:

```bash
tailscale status
tailscale ip -4
```

## 4. Test from the Mac

```bash
/Applications/Tailscale.app/Contents/MacOS/Tailscale ping pi8

ssh -4 -F /dev/null \
  -i ~/.ssh/rpi_one_key \
  pi8@pi8.tail34aafe.ts.net
```

## 5. Add the short SSH name

Back up the Mac SSH configuration:

```bash
cp -p ~/.ssh/config \
  "$HOME/.ssh/config.bak.$(date +%Y%m%d-%H%M%S)"
```

Then add this to `~/.ssh/config`:

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

Then test:

```bash
ssh pi8
```

To reauthorize an expired or removed device:

```bash
sudo tailscale up --force-reauth
```
