# Bootstrap a New Pi from Scratch

> [Back to the Pi8 Access Runbook](README.md)

This guide prepares a new or reimaged Raspberry Pi so that the Mac can reach it
with the same `pi8` workflow.

Official reference: [Raspberry Pi getting-started documentation](https://www.raspberrypi.com/documentation/computers/getting-started.html).

## 1. Check the Mac SSH key

Run on the Mac:

```bash
ls -l ~/.ssh/rpi_one_key ~/.ssh/rpi_one_key.pub
```

If both files exist, reuse them. Do not overwrite the private key.

If neither file exists, create a new Ed25519 key:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/rpi_one_key -C "pi8 access"
```

Protect the private key:

```bash
chmod 600 ~/.ssh/rpi_one_key
```

The public key is safe to display and paste into Raspberry Pi Imager:

```bash
cat ~/.ssh/rpi_one_key.pub
```

Never display, copy, or share `~/.ssh/rpi_one_key` without the `.pub` suffix.

## 2. Prepare the storage device

Use Raspberry Pi Imager on the Mac:

1. Select the correct Raspberry Pi model.
2. Select a current 64-bit Raspberry Pi OS image.
3. Select the intended SD card or storage device carefully.
4. In OS customisation, set hostname `pi8`.
5. Set username `pi8` and a strong recovery password.
6. Configure at least one known Wi-Fi network, country, and timezone.
7. Enable SSH and choose public-key authentication.
8. Select or paste `~/.ssh/rpi_one_key.pub`.
9. Review the target device again before writing the image.

Writing an image erases the selected storage device. Do not proceed until its
identity is certain.

## 3. Boot and find the Pi

Insert the storage device, power on the Pi, and allow several minutes for the
first boot. On the Mac, try local discovery:

```bash
dscacheutil -q host -a name pi8.local
ping -c 2 pi8.local
```

Connect locally before the Tailscale alias is created:

```bash
ssh -4 -F /dev/null \
  -i ~/.ssh/rpi_one_key \
  pi8@pi8.local
```

If the Wi-Fi isolates clients, use the
[direct Ethernet guide](02-direct-ethernet.md).

## 4. Verify the base system

On the Pi:

```bash
cat /etc/os-release
hostname
id -un
hostname -I
sudo systemctl enable --now ssh
systemctl is-active ssh
```

Expected hostname and user are both `pi8`.

Install available security updates before deploying application workloads:

```bash
sudo apt update
sudo apt upgrade
```

Review the proposed package changes before confirming a large upgrade.

## 5. Add durable remote access

Continue with [Install Tailscale](04-install-tailscale.md). After authorization,
update the Mac SSH alias with the new Pi's MagicDNS name. A reimaged Pi can
receive a different MagicDNS suffix or machine name, especially if the old
machine entry remains in the tailnet.
