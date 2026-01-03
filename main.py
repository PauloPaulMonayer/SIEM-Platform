#!/usr/bin/env python3
"""
ThetaWatch Home SIEM - Main Application
========================================

מערכת ניטור אבטחה ביתית מלאה!

מה המערכת עושה:
1. סורקת את הרשת הביתית
2. מזהה מכשירים חדשים
3. מריצה detection rules
4. שולחת התראות Telegram
5. שומרת הכל ב-Database

Usage:
    python3 main.py              # הרצה רגילה
    python3 main.py --scan-once  # סריקה אחת
    python3 main.py --daemon     # רץ ברקע (24/7)
"""

import sys
import os
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime
import yaml

# הוסף את src ל-path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from scanners.network_scanner import NetworkScanner
    from alerting.telegram_bot import TelegramAlerter
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    print("Make sure you're running from the thetawatch-home directory")
    sys.exit(1)


class ThetaWatchHome:
    """
    ThetaWatch Home SIEM - מערכת ניטור אבטחה ביתית
    """
    
    def __init__(self, config_file: str = "../config/config.yaml"):
        """
        אתחול המערכת
        
        Args:
            config_file: נתיב לקובץ config
        """
        self.config_file = config_file
        self.config = None
        self.scanner = None
        self.alerter = None
        self.running = False
        
        # Setup logging
        self.setup_logging()
        
        # Load configuration
        self.load_config()
        
        # Initialize components
        self.initialize_components()
    
    def setup_logging(self):
        """
        הגדרת מערכת לוגים
        """
        # צור תיקיית logs
        log_dir = Path(__file__).parent.parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        # הגדר logging
        log_file = log_dir / 'thetawatch_home.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        global logger
        logger = logging.getLogger(__name__)
    
    def load_config(self):
        """
        טעינת קובץ config
        """
        try:
            config_path = Path(__file__).parent / self.config_file
            
            if not config_path.exists():
                logger.warning(f"Config file not found: {config_path}")
                logger.info("Using default configuration...")
                self.config = self.get_default_config()
                return
            
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            logger.info("✅ Configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            logger.info("Using default configuration...")
            self.config = self.get_default_config()
    
    def get_default_config(self):
        """
        הגדרות ברירת מחדל
        """
        return {
            'network': {
                'home_network': '192.168.1.0/24',
                'scan_interval_minutes': 5
            },
            'telegram': {
                'enabled': False,
                'send_new_device_alerts': True
            },
            'detection': {
                'unknown_device': {
                    'enabled': True,
                    'alert_severity': 'HIGH'
                }
            }
        }
    
    def initialize_components(self):
        """
        אתחול כל הרכיבים
        """
        logger.info("="*70)
        logger.info("ThetaWatch Home SIEM v1.0")
        logger.info("="*70)
        logger.info("Initializing components...")
        
        try:
            # 1. Network Scanner
            logger.info("Creating Network Scanner...")
            network = self.config.get('network', {}).get('home_network', '192.168.1.0/24')
            self.scanner = NetworkScanner(network=network)
            logger.info(f"Network Scanner ready (monitoring {network})")
            
            # 2. Telegram Alerter (אם מופעל)
            telegram_config = self.config.get('telegram', {})
            if telegram_config.get('enabled', False):
                logger.info("📱 Creating Telegram Alerter...")
                bot_token = telegram_config.get('bot_token', '')
                chat_id = telegram_config.get('chat_id', '')
                
                if bot_token and chat_id and bot_token != 'YOUR_BOT_TOKEN_HERE':
                    self.alerter = TelegramAlerter(bot_token, chat_id)
                    logger.info("Telegram Alerter ready")
                else:
                    logger.warning("Telegram not configured (add bot_token and chat_id to config)")
                    logger.info("   Run: python3 src/alerting/telegram_bot.py to setup")
                    self.alerter = None
            else:
                logger.info("Telegram alerts disabled in config")
                self.alerter = None
            
            logger.info("="*70)
            logger.info("All components initialized successfully!")
            logger.info("="*70)
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    def scan_network_once(self):
        """
        סריקה חד-פעמית של הרשת
        """
        logger.info("\n" + "="*70)
        logger.info("Starting Network Scan...")
        logger.info("="*70)
        
        try:
            # סרוק את הרשת
            devices = self.scanner.scan_network()
            
            # הדפס תוצאות
            self.scanner.print_devices()
            
            # בדוק מכשירים חדשים
            new_devices = [d for d in devices if d.get('is_new', False)]
            
            if new_devices:
                logger.warning(f"\nNEW DEVICE(S) FOUND: {len(new_devices)}")
                
                # שלח התראות Telegram
                if self.alerter:
                    for device in new_devices:
                        logger.info(f"Sending Telegram alert for {device['ip']}")
                        self.alerter.send_new_device_alert(device)
                
                # שאל אם להוסיף למכשירים מוכרים
                if not self.running:  # רק במצב interactive
                    try:
                        answer = input("\n❓ Add new devices to known list? (y/n): ")
                        if answer.lower() == 'y':
                            for device in new_devices:
                                self.scanner.add_to_known_devices(device)
                            logger.info("✅ New devices added to known list!")
                    except (EOFError, KeyboardInterrupt):
                        logger.info("\nSkipping device approval...")
            
            # שלח סיכום Telegram (אם מופעל)
            if self.alerter and self.config.get('telegram', {}).get('send_scan_results', False):
                self.alerter.send_scan_results(devices)
            
            return devices
            
        except Exception as e:
            logger.error(f"Network scan failed: {e}")
            return []
    
    def run_daemon(self):
        """
        מצב Daemon - רץ ברקע ללא הפסקה
        """
        logger.info("\n" + "="*70)
        logger.info("Starting Daemon Mode (24/7 Monitoring)")
        logger.info("="*70)
        logger.info("Press Ctrl+C to stop\n")
        
        self.running = True
        scan_interval = self.config.get('network', {}).get('scan_interval_minutes', 5)
        
        scan_count = 0
        
        try:
            while self.running:
                scan_count += 1
                
                logger.info(f"\n{'='*70}")
                logger.info(f"Scan #{scan_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"{'='*70}")
                
                # סרוק את הרשת
                devices = self.scan_network_once()
                
                # המתן לסריקה הבאה
                logger.info(f"\nSleeping for {scan_interval} minute(s)...")
                logger.info(f"   Next scan: {datetime.now().strftime('%H:%M')} + {scan_interval} min")
                
                time.sleep(scan_interval * 60)
                
        except KeyboardInterrupt:
            logger.info("\n\n⚠️  Daemon stopped by user")
            self.running = False
    
    def print_welcome(self):
        """
        הדפסת מסך פתיחה
        """
        print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   🏠 ThetaWatch Home SIEM v1.0                                    ║
║   Professional Home Network Security Monitor                      ║
║                                                                   ║
║   Created by: Paulo Monayer                                       ║
║   https://paulomonayer.com                                        ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝

📡 Monitoring Network: {network}
📊 Scan Interval: {interval} minute(s)
📱 Telegram Alerts: {telegram}

""".format(
            network=self.config.get('network', {}).get('home_network', '192.168.1.0/24'),
            interval=self.config.get('network', {}).get('scan_interval_minutes', 5),
            telegram='✅ Enabled' if self.alerter else '❌ Disabled'
        ))
    
    def print_summary(self):
        """
        סיכום סופי
        """
        logger.info("\n" + "="*70)
        logger.info("SESSION SUMMARY")
        logger.info("="*70)
        logger.info("ThetaWatch Home SIEM session ended")
        logger.info("Logs saved to: logs/thetawatch_home.log")
        logger.info("="*70 + "\n")


def main():
    """
    נקודת הכניסה הראשית
    """
    # Parse arguments
    parser = argparse.ArgumentParser(description='ThetaWatch Home SIEM')
    parser.add_argument('--scan-once', action='store_true', 
                       help='Run a single network scan and exit')
    parser.add_argument('--daemon', action='store_true',
                       help='Run in daemon mode (continuous monitoring)')
    parser.add_argument('--config', type=str, default='../config/config.yaml',
                       help='Path to config file')
    
    args = parser.parse_args()
    
    try:
        # צור את המערכת
        siem = ThetaWatchHome(config_file=args.config)
        
        # הדפס welcome
        siem.print_welcome()
        
        # בחר מצב הרצה
        if args.daemon:
            # מצב Daemon - 24/7
            siem.run_daemon()
        else:
            # סריקה אחת (default)
            siem.scan_network_once()
        
        # סיכום
        siem.print_summary()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Exiting...")
        return 130
    
    except PermissionError:
        print("\n❌ ERROR: Permission denied!")
        print("   Network scanning requires root/admin privileges")
        print("\n💡 Try running with sudo:")
        print("   sudo python3 src/main.py")
        return 1
    
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
