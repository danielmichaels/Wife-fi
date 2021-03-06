# !/usr/bin/env python3
"""Library for scanning wireless frames and locating MAC addresses of interest.

Using a wireless adapter capable of monitor mode and super user permissions
the library can search for a selection of MAC addresses and log their presence
or absence with both epoch and local system time to a sqlite database.

User must have sudo and aircrack-ng suite to monitor and cycle channels.
"""
from collections import namedtuple
from datetime import datetime
from scapy.all import *
from scapy.layers.dot11 import RadioTap, Dot11

# Import config
from config import *
# Import database
from database import SqlDatabase

# Globals
db = SqlDatabase('test.db')  # database for logging targets.
db.create_table()
Query = namedtuple('Query', 'target mac rssi epoch dtg msg')


def packet_handler(packet):
    """Sniff for ProbeAssoReq, ReassoReq and Probrequest.
    Display results to screen
    """
    management_frames = (0, 2, 4)

    if not packet.haslayer(Dot11):
        return

    if packet.type == 0 and packet.subtype in management_frames:

        ssid = packet.info
        mac = packet.addr2
        rssi = get_rssi(packet)
        epoch = epochtime()
        dtg = system_time(epoch)
        # print(f'{mac} broadcasts: {ssid}   rssi:{rssi}   @ {dtg}')
        last = last_seen()

        if mac in TARGET_LIST:
            try:
                print('{} {} {} {} {msg}'.format(mac, rssi, epoch, dtg,
                                                 msg='Alive'))
                report(target=None, mac=mac, rssi=rssi, epoch=epoch,
                       dtg=dtg, msg='Alive')
                time.sleep(5)  # to stop multiple entries
            except TypeError as e:
                print(e)

        if last is not None:
            if epoch >= (last.epoch + ALERT_THRESHOLD):
                if last.mac is None:
                    return
                # print(last.epoch + 60, 'last.epoch plus epoch')
                try:
                    print('Exceeded ALERT_THRESHOLD: {} {}'.format(last.mac,
                                                                   last.epoch))
                    report(target=None, mac=last.mac, rssi=rssi, epoch=epoch,
                           dtg=dtg, msg='Dead')
                    time.sleep(5)
                except Exception as e:
                    print(e)


def get_rssi(packet):
    """Gets the RSSI of packet from RadioTap"""
    if packet.haslayer(RadioTap):
        return packet.dbm_antsignal


def epochtime():
    """Get local time."""
    dt = datetime.utcnow()
    epoch = int(datetime.timestamp(dt))
    # epoch = datetime.timestamp(dt)
    return epoch


def system_time(epoch):
    """Return the epoch time in system time. Human readability paramount."""
    return time.ctime(epoch)


def last_seen():
    """Return the last row of 'epoch' as a integer."""
    last = db.get_last('logging', '*')
    if last is None:
        insert_dummy = db.write(target=None, mac=None, rssi=None,
                                epoch=epochtime(),
                                dtg=system_time(epochtime()), msg="Dummy Data")
        return insert_dummy

    query = Query(target=last[0], mac=last[1], rssi=last[2], epoch=last[3],
                  dtg=last[4], msg=last[5])

    return query


def report(target=None, mac=None, rssi=None, epoch=None, dtg=None,
           msg=None):
    """Alert if specified MAC is in range."""
    db.write(target, mac, rssi, epoch, dtg, msg)


if __name__ == '__main__':
    # sniff(iface=sys.argv[1], store=0, prn=packet_handler)
    sniff(iface=IFACE, store=0, prn=packet_handler)
