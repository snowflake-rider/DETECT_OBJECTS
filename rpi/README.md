# Raspberry Pi SSH Access

This guide explains how to connect to the Raspberry Pi without entering the
Pi account password every time.

## Connection details

- Username: `kcc-rpi`
- Hostname: `odai-rpi.local`
- Direct command: `ssh -t kcc-rpi@odai-rpi.local`
- Helper script: `./rpi/access-rpi-1.sh`

The computer connecting to `odai-rpi.local` normally needs to be on the same
local network as the Raspberry Pi.

## SSH keys in simple terms

An SSH key is created as a pair:

- The **private key** stays on the user's computer. Never copy or share it.
- The **public key** is added to the Raspberry Pi. It is safe to share.

When connecting, SSH checks whether the private key on the user's computer
matches a public key accepted by the Pi. A match allows the connection without
asking for the Pi account password.

Two SSH files are commonly confused:

- `~/.ssh/authorized_keys` on the Pi lists the public keys allowed to connect
  to the `kcc-rpi` account.
- `~/.ssh/known_hosts` remembers the identity of computers previously
  connected to. It does not grant anyone access.

The `-t` option only opens an interactive terminal. It does not create or
select an SSH key.

## First-time setup for a new user

### 1. Join the correct network

Connect the new user's computer to the same local network as the Raspberry Pi.

What happens: the computer can find the `.local` address `odai-rpi.local`.

### 2. Check for an existing key

Run this on the new user's computer:

```bash
ls ~/.ssh/id_ed25519 ~/.ssh/id_ed25519.pub
```

If both files exist, do not overwrite them. Continue to step 4.

What happens: this checks whether the user already has an Ed25519 SSH key pair.
It does not change anything.

### 3. Generate a key if one does not exist

Run this on the new user's computer:

```bash
ssh-keygen -t ed25519 -C "name@computer"
```

Press Enter to use the default file location. A passphrase is recommended. The
computer's keychain or SSH agent can remember it.

What happens: SSH creates:

- `~/.ssh/id_ed25519` — the private key, which must stay secret.
- `~/.ssh/id_ed25519.pub` — the public key, which can be copied to the Pi.

### 4. Add the public key to the Raspberry Pi

If the new user is allowed to enter the `kcc-rpi` account password, run:

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub kcc-rpi@odai-rpi.local
```

Enter the Pi account password when prompted. This should be the final time that
password is needed.

What happens: `ssh-copy-id` appends the new user's public key to
`~/.ssh/authorized_keys` on the Raspberry Pi. Existing keys remain in the file,
so existing users keep their access.

If `ssh-copy-id` is unavailable or the new user should not know the Pi
password, the new user should display their public key:

```bash
cat ~/.ssh/id_ed25519.pub
```

They should send that single public-key line to an existing authorized user.
The existing user can add it while logged in to the Pi:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
printf '%s\n' 'PASTE_THE_NEW_PUBLIC_KEY_HERE' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Only the `.pub` public key should be sent. Never send `id_ed25519`.

### 5. Test the connection

Run this on the new user's computer:

```bash
ssh -t kcc-rpi@odai-rpi.local
```

On the first connection, SSH may ask whether to trust the host. Confirm only
after checking that `odai-rpi.local` is the intended Raspberry Pi.

What happens: the Pi finds the new user's public key in `authorized_keys` and
asks their computer to prove it has the matching private key.

## Everyday access for an authorized user

Users who have already completed the setup do not need to generate or copy a
key again. Connect directly:

```bash
ssh -t kcc-rpi@odai-rpi.local
```

Or, from this repository, use:

```bash
./rpi/access-rpi-1.sh
```

What happens: SSH automatically looks for the user's private key in the
standard `~/.ssh` location and uses it to authenticate.

If an authorized user moves to a new computer, they should generate a new key
on that computer and add its public key by following the first-time setup. Do
not copy the old computer's private key to teammates.

## Check or remove access

On the Raspberry Pi, list the authorized public keys:

```bash
cat ~/.ssh/authorized_keys
```

Normally, each line represents one authorized key. The comment at the end of a
line, such as `name@computer`, helps identify its owner.

To remove someone's access, carefully delete only that user's line from
`~/.ssh/authorized_keys`. Other keys will continue to work. Keep at least one
tested administrator connection open while changing this file so that a
mistake does not lock everyone out.

## Common errors

- `Could not resolve hostname`: connect to the same network as the Pi and
  check that `odai-rpi.local` is correct.
- `Permission denied (publickey)`: the user's public key is not installed, the
  wrong private key is being used, or file permissions are incorrect.
- `REMOTE HOST IDENTIFICATION HAS CHANGED`: stop and verify why the Pi's host
  identity changed. Do not bypass this warning without checking.
