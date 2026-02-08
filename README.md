# PyBan Private MAC

Automatically detect and block devices using private/randomized MAC addresses on UniFi networks.

## Overview

This Docker container monitors your UniFi network and automatically blocks clients that use private or randomized MAC addresses. Private MACs are often enabled by default on modern mobile devices for privacy reasons, but can cause issues with network management, device tracking, and DHCP reservations.

## Features

- 🔍 Real-time monitoring of UniFi clients
- 🚫 Automatic blocking of devices with private MAC addresses
- ✅ Whitelist support to protect your own devices
- 🔔 Home Assistant notifications when devices are blocked
- 🐳 Easy Docker deployment
- 📊 Timestamped logging
- 🔐 Support for UniFi OS (UDM/UCG) and legacy controllers

## Private MAC Detection

A MAC address is considered private if the second character is `2`, `6`, `A`, or `E` (e.g., `c2:xx:xx:xx:xx:xx`).

## Prerequisites

- UniFi Network Controller (Cloud Gateway, Dream Machine, or standalone)
- Docker and Docker Compose
- (Optional) Home Assistant instance for notifications

## Installation

1. Clone this repository:
   ```bash
   git clone <your-repo-url>
   cd pyban_private_mac
   ```

2. Edit `docker-compose.yml` and configure your environment variables (see below)

3. Build and start the container:
   ```bash
   ./start.sh
   ```

## Configuration

### Environment Variables

Edit `docker-compose.yml` to set these required variables:

#### UniFi Controller Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `UNIFI_IP` | UniFi controller IP address | `192.168.3.1` | `192.168.2.1` |
| `UNIFI_PORT` | UniFi controller port | `443` (UniFi OS) or `8443` (legacy) | `443` |
| `UNIFI_OS` | Set to `true` for UniFi OS devices (UDM/UCG) | `false` | `true` |
| `UNIFI_USERNAME` | UniFi admin username | `ton_user` | `admin` |
| `UNIFI_PASSWORD` | UniFi admin password | `ton_password` | `your-password` |
| `UNIFI_SITE_ID` | UniFi site ID | `default` | `default` |
| `UNIFI_SSL_VERIFY` | Verify SSL certificate | `false` | `true` |

#### Whitelist Settings

| Variable | Description | Example |
|----------|-------------|---------|
| `WHITELIST` | Comma-separated list of MAC addresses to never block | `aa:bb:cc:dd:ee:ff,11:22:33:44:55:66` |
| `SCAN_INTERVAL` | Seconds between client scans | `10` |

#### Home Assistant Notifications (Optional)

| Variable | Description | Example |
|----------|-------------|---------|
| `HA_URL` | Home Assistant base URL | `http://homeassistant.local:8123` |
| `HA_TOKEN` | Home Assistant long-lived access token | `eyJ0eXAiOiJKV1...` |
| `HA_NOTIFY_SERVICE` | Notification service to use | `notify.mobile_app` or `notify.sms` |
| `HA_VERIFY` | Verify Home Assistant SSL certificate | `true` |

### Getting Home Assistant Token

1. Log into Home Assistant
2. Go to your profile (bottom left)
3. Scroll to "Long-Lived Access Tokens"
4. Click "Create Token"
5. Copy the token to `HA_TOKEN` in docker-compose.yml

### Finding Your UniFi Site ID

- Open your UniFi controller web interface
- Navigate to a site and check the URL: `/manage/site/<site_id>/...`
- Most installations use `default`

## Usage

### Start the container:
```bash
./start.sh
```

### View logs:
```bash
docker compose logs -f pyban_private_mac
```

### Stop the container:
```bash
docker compose down
```

### Backup configuration:
```bash
./backup.sh
```

## Example Log Output

```
[2026-02-08 17:30:45] 🔌 Connecting to UniFi controller (192.168.2.1:443)...
[2026-02-08 17:30:46] ✅ Connected successfully.
[2026-02-08 17:30:46] 🚀 Monitoring active. Press Ctrl+C to stop.
[2026-02-08 17:31:15] 🚨 DETECTION: iPhone uses private MAC (c2:c9:e9:50:36:6e)
[2026-02-08 17:31:15] 🔨 Blocking...
[2026-02-08 17:31:16] 💀 iPhone blocked successfully.
[2026-02-08 17:31:16] 📣 Sending Home Assistant notification to http://192.168.2.103:8123/api/services/notify/sms ...
[2026-02-08 17:31:18] 📣 Home Assistant response: 200 []
```

## Security Considerations

⚠️ **Important**: This script requires admin credentials to your UniFi controller. Use a dedicated local admin account with appropriate restrictions.

- Store credentials securely in your `docker-compose.yml` 
- Consider using Docker secrets in production
- Restrict network access to the container
- Regularly review the whitelist to ensure it includes all your devices

## Troubleshooting

### Login failed - status code: 404
- Check `UNIFI_OS` setting (set to `true` for UDM/UCG)
- Verify `UNIFI_PORT` (443 for UniFi OS, 8443 for legacy)
- Confirm controller IP address and credentials

### Home Assistant notification timeout
- Increase timeout in the code (currently 30s)
- Check Home Assistant is accessible from the container
- Verify the notification service exists and is working

### Not blocking devices
- Check logs for detection messages
- Verify the MAC is actually private (2nd char is 2/6/A/E)
- Ensure device is not in whitelist
- Check UniFi user has permission to block clients

## License

MIT License - feel free to modify and distribute.

## Contributing

Pull requests and issues welcome!
