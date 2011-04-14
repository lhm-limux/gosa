#!/bin/sh
# Usage: send.sh user message

# Get full path of notify-send
NOTIFY=$(which notify-send)

# Collect potential addresses for all sessions
PIDS=$(pgrep -xfu $1 '(gnome-session|x-session-manager|/bin/sh /usr/bin/startkde)')
BAS=$(for P in $PIDS; do
    grep -z ^DBUS_SESSION_BUS_ADDRESS= /proc/$P/environ
    done | sort | uniq)

# Send notification
for BA in $BAS; do
    su "$1" -c "$BA $NOTIFY 'Test message' '$2'"
done
