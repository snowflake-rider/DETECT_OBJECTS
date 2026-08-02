# Set Up a New Pi

> [Back to Pi8 Access](README.md)

## 1. Prepare the SSH key

Check the Mac first:

```bash
ls -l ~/.ssh/rpi_one_key ~/.ssh/rpi_one_key.pub
```

Reuse the files if they exist. Never overwrite or share the private file
`~/.ssh/rpi_one_key`.

If neither file exists, create them:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/rpi_one_key -C "pi8 access"
chmod 600 ~/.ssh/rpi_one_key
```

The `.pub` file is safe to copy:

```bash
cat ~/.ssh/rpi_one_key.pub
```

## 2. Write Raspberry Pi OS

In Raspberry Pi Imager:

1. Choose the correct Pi and storage device.
2. Choose a current 64-bit Raspberry Pi OS.
3. Set hostname and username to `pi8`.
4. Set Wi-Fi, country, timezone, and a recovery password.
5. Enable SSH with public-key authentication.
6. Add `~/.ssh/rpi_one_key.pub`.
7. Confirm the storage device before writing.

Writing the image erases the selected storage device.

## 3. Connect after first boot

Wait several minutes, then run on the Mac:

```bash
ssh -4 -F /dev/null \
  -i ~/.ssh/rpi_one_key \
  pi8@pi8.local
```

If local Wi-Fi blocks the connection, use [Direct Ethernet](02-direct-ethernet.md).

## 4. Update the Pi

```bash
hostname
whoami
sudo systemctl enable --now ssh
sudo apt update
sudo apt upgrade
```

`hostname` and `whoami` should both print `pi8`.

Finally, [install Tailscale](04-install-tailscale.md).
