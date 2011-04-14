#!/bin/sh
# Usage: send.sh user message

# Collect potential addresses
PIDS=$(pgrep -xfu $1 '(x-session-manager|.*ssh-agent.*)')

# Unique DBUS sessions for this user
BAS=$(for P in $PIDS; do grep -z ^DBUS_SESSION_BUS_ADDRESS= /proc/$P/environ; done | sort | uniq)

# Send notification
for BA in $BAS; do
    su "$1" -c "$BA notify-send 'Test message' '$2'"
done
