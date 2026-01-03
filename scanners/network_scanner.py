"""
Network Scanner - סורק רשת ביתית
==================================

סורק את כל המכשירים המחוברים לרשת הביתית.

מה הוא עושה:
1. סורק את כל ה-IPs ברשת (192.168.1.0/24)
2. מזהה מכשירים פעילים (PING)
3. מחלץ MAC address
4. מזהה Vendor (יצרן המכשיר)
5. שומר device fingerprint

טכנולוגיות:
- scapy: packet crafting
- nmap: advanced scanning (אופציונלי)
"""

import subprocess
import re
import json
import socket
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class NetworkScanner:
    """
    סורק רשת ביתית ומזהה מכשירים
    """
    
    def __init__(self, network: str = "192.168.1.0/24"):
        """
        אתחול Scanner
        
        Args:
            network: טווח הרשת לסריקה (CIDR notation)
                    192.168.1.0/24 = 192.168.1.1 - 192.168.1.254
        """
        self.network = network
        self.devices = []
        self.known_devices = self.load_known_devices()
        
        # OUI Database - מזהה יצרן לפי MAC
        # 3 בתים ראשונים של MAC = Organization Unique Identifier
        self.vendor_db = {
            '00:1A:11': 'Google',
            '00:50:F2': 'Microsoft',
            'B8:27:EB': 'Raspberry Pi Foundation',
            'DC:A6:32': 'Raspberry Pi Trading',
            '3C:22:FB': 'Apple',
            '68:A8:6D': 'Apple',
            'AC:DE:48': 'Apple',
            '00:0C:29': 'VMware',
            '08:00:27': 'VirtualBox',
            '50:46:5D': 'Hon Hai Precision (Foxconn)',
            '00:E0:4C': 'Realtek',
            '00:1B:63': 'Apple',
            '28:6A:BA': 'Apple',
            'F0:18:98': 'Apple',
            'A4:5E:60': 'Apple',
            '00:25:00': 'Apple',
            '00:26:08': 'Apple',
        }
    
    def load_known_devices(self) -> Dict:
        """
        טוען מכשירים מוכרים מקובץ
        
        Returns:
            Dictionary של מכשירים מוכרים
        """
        try:
            with open('../data/known_devices.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.info("No known devices file found, starting fresh")
            return {}
    
    def save_known_devices(self):
        """
        שומר מכשירים מוכרים לקובץ
        """
        try:
            with open('../data/known_devices.json', 'w') as f:
                json.dump(self.known_devices, f, indent=2)
            logger.info(f"Saved {len(self.known_devices)} known devices")
        except Exception as e:
            logger.error(f"Failed to save known devices: {e}")
    
    def ping_sweep(self) -> List[str]:
        """
        סריקת PING לכל הרשת
        
        מוצא אילו IPs פעילים
        
        Returns:
            רשימת IPs פעילים
        """
        logger.info(f"Starting ping sweep on {self.network}")
        
        # חלץ את הprefix (192.168.1)
        base_ip = '.'.join(self.network.split('.')[:-1])
        
        active_ips = []
        
        # זיהוי מערכת הפעלה
        import platform
        is_windows = platform.system().lower() == 'windows'
        
        # סרוק 1-254 (דלג על 0 ו-255)
        for i in range(1, 255):
            ip = f"{base_ip}.{i}"
            
            # PING עם timeout קצר
            if is_windows:
                # Windows: ping -n 1 -w 1000
                result = subprocess.run(
                    ['ping', '-n', '1', '-w', '1000', ip],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                # Linux/Mac: ping -c 1 -W 1
                result = subprocess.run(
                    ['ping', '-c', '1', '-W', '1', ip],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            if result.returncode == 0:
                active_ips.append(ip)
                logger.debug(f"Found active device: {ip}")
        
        logger.info(f"Ping sweep complete: {len(active_ips)} active devices")
        return active_ips
    
    def get_mac_address(self, ip: str) -> Optional[str]:
        """
        מחזיר MAC address של IP
        
        משתמש ב-ARP table של המערכת
        
        Args:
            ip: כתובת IP
            
        Returns:
            MAC address או None
        """
        try:
            # קרא את ה-ARP table
            result = subprocess.run(
                ['arp', '-n', ip],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # חפש MAC בפורמט XX:XX:XX:XX:XX:XX
            match = re.search(
                r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})',
                result.stdout
            )
            
            if match:
                mac = match.group(0).upper()
                logger.debug(f"{ip} -> MAC: {mac}")
                return mac
            
        except Exception as e:
            logger.error(f"Failed to get MAC for {ip}: {e}")
        
        return None
    
    def get_vendor(self, mac: str) -> str:
        """
        מזהה יצרן לפי MAC address
        
        Args:
            mac: MAC address (XX:XX:XX:XX:XX:XX)
            
        Returns:
            שם היצרן או "Unknown"
        """
        # קח 3 בתים ראשונים (OUI)
        oui = ':'.join(mac.split(':')[:3]).upper()
        
        vendor = self.vendor_db.get(oui, 'Unknown')
        
        # אם לא מצאנו, נסה עם הבתים הראשונים
        if vendor == 'Unknown':
            # חיפוש חלקי
            for known_oui, known_vendor in self.vendor_db.items():
                if oui.startswith(known_oui[:5]):  # 2 בתים ראשונים
                    return known_vendor
        
        return vendor
    
    def get_hostname(self, ip: str) -> Optional[str]:
        """
        מנסה לקבל hostname של המכשיר
        
        Args:
            ip: כתובת IP
            
        Returns:
            Hostname או None
        """
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            logger.debug(f"{ip} -> Hostname: {hostname}")
            return hostname
        except socket.herror:
            return None
    
    def identify_device_type(self, vendor: str, hostname: Optional[str]) -> str:
        """
        מנסה לזהות סוג מכשיר
        
        Args:
            vendor: שם היצרן
            hostname: שם המכשיר
            
        Returns:
            סוג המכשיר
        """
        hostname_lower = hostname.lower() if hostname else ""
        vendor_lower = vendor.lower()
        
        # זיהוי לפי hostname
        if 'iphone' in hostname_lower or 'ipad' in hostname_lower:
            return 'Mobile Device (iOS)'
        elif 'android' in hostname_lower:
            return 'Mobile Device (Android)'
        elif 'laptop' in hostname_lower or 'pc' in hostname_lower:
            return 'Computer'
        elif 'tv' in hostname_lower:
            return 'Smart TV'
        elif 'router' in hostname_lower:
            return 'Router'
        
        # זיהוי לפי vendor
        if 'apple' in vendor_lower:
            return 'Apple Device'
        elif 'raspberry' in vendor_lower:
            return 'Raspberry Pi'
        elif 'samsung' in vendor_lower:
            return 'Samsung Device'
        elif 'google' in vendor_lower:
            return 'Google Device'
        
        return 'Unknown Device'
    
    def scan_device(self, ip: str) -> Dict:
        """
        סריקה מלאה של מכשיר בודד
        
        Args:
            ip: כתובת IP לסריקה
            
        Returns:
            Dictionary עם כל המידע על המכשיר
        """
        mac = self.get_mac_address(ip)
        hostname = self.get_hostname(ip)
        vendor = self.get_vendor(mac) if mac else "Unknown"
        device_type = self.identify_device_type(vendor, hostname)
        
        # בדוק אם זה מכשיר מוכר
        is_known = mac in self.known_devices if mac else False
        
        device_info = {
            'ip': ip,
            'mac': mac,
            'hostname': hostname,
            'vendor': vendor,
            'type': device_type,
            'is_known': is_known,
            'first_seen': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat()
        }
        
        # אם זה מכשיר חדש, סמן אותו
        if mac and not is_known:
            device_info['is_new'] = True
            logger.warning(f"🆕 NEW DEVICE DETECTED: {ip} ({vendor})")
        else:
            device_info['is_new'] = False
        
        return device_info
    
    def scan_network(self) -> List[Dict]:
        """
        סריקה מלאה של כל הרשת
        
        Returns:
            רשימת כל המכשירים שנמצאו
        """
        logger.info("="*70)
        logger.info("Starting Full Network Scan")
        logger.info("="*70)
        
        # שלב 1: מצא IPs פעילים
        active_ips = self.ping_sweep()
        
        # שלב 2: סרוק כל IP
        devices = []
        for ip in active_ips:
            device = self.scan_device(ip)
            devices.append(device)
        
        self.devices = devices
        
        logger.info("="*70)
        logger.info(f"Network Scan Complete: {len(devices)} devices found")
        logger.info("="*70)
        
        return devices
    
    def add_to_known_devices(self, device: Dict):
        """
        מוסיף מכשיר לרשימת המוכרים
        
        Args:
            device: פרטי המכשיר
        """
        if device['mac']:
            self.known_devices[device['mac']] = {
                'ip': device['ip'],
                'hostname': device['hostname'],
                'vendor': device['vendor'],
                'type': device['type'],
                'first_seen': device['first_seen'],
                'friendly_name': None  # למשתמש להוסיף
            }
            self.save_known_devices()
            logger.info(f"Added {device['mac']} to known devices")
    
    def print_devices(self):
        """
        מדפיס את רשימת המכשירים בפורמט יפה
        """
        if not self.devices:
            print("\nNo devices found!")
            return
        
        print("\n" + "="*90)
        print("🏠 HOME NETWORK DEVICES")
        print("="*90)
        print(f"{'IP':<15} {'MAC':<18} {'Vendor':<20} {'Type':<20} {'Status':<10}")
        print("-"*90)
        
        for device in self.devices:
            ip = device['ip']
            mac = device['mac'] or 'N/A'
            vendor = device['vendor']
            device_type = device['type']
            
            if device['is_new']:
                status = "🆕 NEW"
            elif device['is_known']:
                status = "✅ Known"
            else:
                status = "❓ Unknown"
            
            print(f"{ip:<15} {mac:<18} {vendor:<20} {device_type:<20} {status:<10}")
        
        print("="*90)
        
        # סיכום
        new_count = sum(1 for d in self.devices if d['is_new'])
        known_count = sum(1 for d in self.devices if d['is_known'])
        
        print(f"\nSummary:")
        print(f"  Total Devices: {len(self.devices)}")
        print(f"  Known Devices: {known_count}")
        print(f"  New Devices:   {new_count}")
        print("="*90 + "\n")


# ==== דוגמה לשימוש ====
if __name__ == "__main__":
    """
    סריקת רשת ביתית
    """
    import sys
    
    # הגדר logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    print("""
    ╔═══════════════════════════════════════════╗
    ║   ThetaWatch Home - Network Scanner       ║
    ║   Discovering devices on your network...  ║
    ╚═══════════════════════════════════════════╝
    """)
    
    # צור scanner
    # שנה את הרשת בהתאם לרשת שלך:
    # - HOT רוטר בדרך כלל: 192.168.1.0/24
    # - אם אתה משנה: 192.168.0.0/24 או 10.0.0.0/24
    scanner = NetworkScanner(network="192.168.1.0/24")
    
    try:
        # סרוק את הרשת
        devices = scanner.scan_network()
        
        # הדפס תוצאות
        scanner.print_devices()
        
        # שאל אם להוסיף מכשירים חדשים
        new_devices = [d for d in devices if d['is_new']]
        if new_devices:
            print(f"\n🆕 Found {len(new_devices)} new device(s)!")
            answer = input("Add them to known devices? (y/n): ")
            if answer.lower() == 'y':
                for device in new_devices:
                    scanner.add_to_known_devices(device)
                print("✅ New devices added to known list!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Scan interrupted by user")
        sys.exit(1)
    except PermissionError:
        print("\n\n❌ ERROR: Need sudo/root permissions for network scanning")
        print("   Try: sudo python3 network_scanner.py")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Scan failed: {e}", exc_info=True)
        sys.exit(1)
