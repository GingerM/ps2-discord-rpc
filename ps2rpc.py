import socket
import time
import subprocess
import logging
from pypresence import Presence

#TODO Imgur uploads
#TODO Dynamic dictionary
#TODO Kill RPC after disconnect in OPL
#TODO Extend ping TTL for fewer pings until timeout

client_id = "1112034192960798840"  # Fake ID, put your real one here

# the public network interface
HOST = "192.168.1.110"
PS2_IP = "192.168.1.114"
DVD_FILTER = bytes([0x5C, 0x00, 0x44, 0x00, 0x56, 0x00, 0x44, 0x00, 0x5C])
GAMES_BIN_FILTER = bytes(
    [
        0x5C,
        0x00,
        0x44,
        0x00,
        0x56,
        0x00,
        0x44,
        0x00,
        0x5C,
        0x00,
        0x67,
        0x00,
        0x61,
        0x00,
        0x6D,
        0x00,
        0x65,
        0x00,
        0x73,
        0x00,
        0x2E,
        0x00,
        0x62,
        0x00,
        0x69,
        0x00,
        0x6E,
    ]
)
PING_GRACE = 3

LARGE_IMAGE_MAP = {
    "SLUS_210.05" : "https://i.imgur.com/GXSok6D.jpg",
    "SLES_535.40" : "https://i.imgur.com/jjRCj7e.jpg",
}

SMALL_IMAGE_MAP = {
    "SLUS_210.05" : "https://i.imgur.com/9eC9WOP.png",
    "SLES_535.40" : "https://i.imgur.com/z4iSnFj.png",
}

# poor man's python
def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix) :]
    return text  # or whatever

def ping_ps2(ip=PS2_IP):
    # Define the ping command based on the operating system
    # ping_cmd = ["ping", "-c", "1", ip]  # For Linux/macOS
    ping_cmd = ["ping", "-n", "1", ip, "-w", "5000"]  # For Windows
    try:
        # Execute the ping command and capture the output
        result = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=5)
        output = result.stdout.lower()

        # Check the output for successful ping
        if "de" in output and "temps=" in output:
            logging.debug("PS2 is alive")
            return True
        else:
            return False
    except subprocess.TimeoutExpired:
        return False
    except Exception as e:
        logging.exception(f"An error occurred: {e}")
        return False


def main():
    RPC = Presence(client_id)  # Initialize the client class
    RPC.connect()  # Start the handshake loop
    # create a raw socket and bind it to the public interface
    s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
    s.bind((HOST, 0))
    # Include IP headers
    s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    # receive all packets
    s.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
    PS2Online = False
    while True:
        message, address = s.recvfrom(65565)
        ip, port = address
        if ip == PS2_IP:
            if not PS2Online:
                RPC.update(state="Idle",
                details="running OPL", 
                large_image="https://i.imgur.com/MXzehWn.png", 
                large_text="Open PS2 Loader", 
                start=time.time())
                logger.info("PS2 has come online")
                #print(message, len(message))
                PS2Online = True
            # drop last byte
            slice = message[128:-1]
            if slice.startswith(GAMES_BIN_FILTER):
                continue
            elif slice.startswith(DVD_FILTER):
                gamepath = bytes([c for c in slice if c != 0x00]).decode()
                gamecode, gamename, _ = remove_prefix(gamepath, "\\DVD\\").rsplit(
                    ".", 2
                )
                RPC.update(
                    state=gamecode,#middle text
                    details=gamename,#top text
                    large_image=LARGE_IMAGE_MAP.get(gamecode, "https://i.imgur.com/HjuVXhR.png"),
                    large_text=gamename,#hover text
                    small_image=SMALL_IMAGE_MAP.get(gamecode,"https://i.imgur.com/91Nj3w0.png"),
                    small_text="PlayStation 2",#hover text
                    start=time.time(),#timer
                )
                logger.info("RPC started: " + gamecode + " - " + gamename)
                time.sleep(10)#necessary wait to avoit dropped pings on game startup
                ping_count=1
                ping_lost=False
                while ping_count<=PING_GRACE:
                    if ping_ps2(PS2_IP):
                        ping_count=1
                        if ping_lost:
                            logging.info("PS2 has resumed pings")
                            ping_lost=False
                	    #wait before pinging again
                        time.sleep(3)
                    else:
                        logging.warning("No response from PS2, retrying.. ({}/{})".format(ping_count,PING_GRACE))
                        ping_lost=True
                        ping_count+=1
                PS2Online = False
                RPC.clear()
                logging.info("PS2 has gone offline, RPC terminated")
                #we don't talk about bruno
                s.recvfrom(65565)
                s.recvfrom(65565)
                s.recvfrom(65565)
                s.recvfrom(65565)
                s.recvfrom(65565)
                time.sleep(3)
    # receive a packet
    # disabled promiscuous mode
    s.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%F %H:%M",
        level=logging.INFO,
    )
    logger = logging.getLogger()
    main()