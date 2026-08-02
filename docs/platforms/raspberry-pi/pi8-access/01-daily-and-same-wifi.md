# Daily and Same-Wi-Fi Access

> [Back to Pi8 Access](README.md)

## Recommended: Tailscale

Run on the Mac:

```bash
ssh pi8
```

Check that you reached the correct Pi:

```bash
hostname
whoami
```

Both should print `pi8`.

## Same Wi-Fi without Tailscale

```bash
ssh -4 -F /dev/null \
  -i ~/.ssh/rpi_one_key \
  pi8@pi8.local
```

`-F /dev/null` ignores the `pi8.local` alias in the Mac SSH configuration and
lets Bonjour find the local Pi.

This may fail on guest Wi-Fi, company networks, or phone hotspots that block
devices from talking to each other. Use `ssh pi8` when that happens.

## Copy files

```bash
scp ./example.txt pi8:~/
scp -r ./example-directory pi8:~/
```
