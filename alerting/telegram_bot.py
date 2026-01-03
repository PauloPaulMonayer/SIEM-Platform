"""
Telegram Alerting - התראות לטלפון
===================================

שולח התראות אבטחה ישירות לטלגרם!

יכולות:
- התראות real-time
- סיכומים יומיים
- שליחת screenshots
- פקודות ניהול מרחוק

Setup:
1. פתח @BotFather בטלגרם
2. שלח /newbot
3. תן שם לבוט: "ThetaWatch Security Bot"
4. קבל TOKEN
5. שלח /start לבוט שלך
6. הרץ את get_chat_id() לקבל CHAT_ID
"""

import requests
import json
from datetime import datetime
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class TelegramAlerter:
    """
    מערכת התראות Telegram
    """
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        אתחול Telegram Bot
        
        Args:
            bot_token: Token של הבוט מ-@BotFather
            chat_id: Chat ID שלך (קבל ע"י get_chat_id)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
        # Test connection
        if self.test_connection():
            logger.info("✅ Telegram Bot connected successfully!")
        else:
            logger.error("❌ Failed to connect to Telegram Bot")
    
    def test_connection(self) -> bool:
        """
        בודק אם החיבור לבוט עובד
        
        Returns:
            True אם עובד, False אם לא
        """
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                bot_info = response.json()['result']
                logger.info(f"Bot Name: {bot_info['first_name']}")
                logger.info(f"Bot Username: @{bot_info['username']}")
                return True
            else:
                logger.error(f"API Error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def send_message(
        self,
        message: str,
        parse_mode: str = "Markdown",
        disable_notification: bool = False
    ) -> bool:
        """
        שליחת הודעה רגילה
        
        Args:
            message: תוכן ההודעה
            parse_mode: "Markdown" או "HTML"
            disable_notification: True = silent notification
            
        Returns:
            True אם נשלח בהצלחה
        """
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_notification": disable_notification
            }
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                logger.debug("Message sent successfully")
                return True
            else:
                logger.error(f"Failed to send message: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def send_alert(
        self,
        severity: str,
        title: str,
        description: str,
        details: Optional[dict] = None
    ) -> bool:
        """
        שליחת התראת אבטחה מעוצבת
        
        Args:
            severity: CRITICAL/HIGH/MEDIUM/LOW
            title: כותרת ההתראה
            description: תיאור
            details: מידע נוסף (dictionary)
            
        Returns:
            True אם נשלח
        """
        # Emoji לפי severity
        emoji_map = {
            'CRITICAL': '🔴',
            'HIGH': '🟠',
            'MEDIUM': '🟡',
            'LOW': '🔵',
            'INFO': 'ℹ️'
        }
        
        emoji = emoji_map.get(severity, '⚠️')
        
        # בנה הודעה
        message = f"{emoji} *{severity} ALERT*\n\n"
        message += f"*{title}*\n"
        message += f"{description}\n"
        
        # הוסף פרטים
        if details:
            message += "\n📋 *Details:*\n"
            for key, value in details.items():
                message += f"  • {key}: `{value}`\n"
        
        # Timestamp
        message += f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # שלח (בלי silent notification ל-HIGH ו-CRITICAL)
        silent = severity in ['LOW', 'INFO']
        
        return self.send_message(message, disable_notification=silent)
    
    def send_security_alert(self, alert_data: dict) -> bool:
        """
        שליחת התראה מה-Detection Engine
        
        Args:
            alert_data: Alert dictionary מהמערכת
            
        Returns:
            True אם נשלח
        """
        return self.send_alert(
            severity=alert_data['severity'],
            title=alert_data['rule_name'],
            description=alert_data['description'],
            details=alert_data.get('details', {})
        )
    
    def send_new_device_alert(self, device: dict) -> bool:
        """
        התראה על מכשיר חדש ברשת
        
        Args:
            device: מידע על המכשיר
            
        Returns:
            True אם נשלח
        """
        message = "🆕 *NEW DEVICE DETECTED*\n\n"
        message += f"A new device has connected to your network!\n\n"
        message += f"📱 *Device Info:*\n"
        message += f"  • IP: `{device['ip']}`\n"
        message += f"  • MAC: `{device.get('mac', 'Unknown')}`\n"
        message += f"  • Vendor: `{device.get('vendor', 'Unknown')}`\n"
        message += f"  • Type: `{device.get('type', 'Unknown')}`\n"
        
        if device.get('hostname'):
            message += f"  • Name: `{device['hostname']}`\n"
        
        message += f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        message += f"\n\n⚠️ If you don't recognize this device, it may be unauthorized!"
        
        return self.send_message(message, disable_notification=False)
    
    def send_daily_summary(self, stats: dict) -> bool:
        """
        סיכום יומי
        
        Args:
            stats: סטטיסטיקות היום
            
        Returns:
            True אם נשלח
        """
        message = "📊 *DAILY SECURITY SUMMARY*\n\n"
        message += f"🗓️ {datetime.now().strftime('%Y-%m-%d')}\n\n"
        
        message += f"📈 *Statistics:*\n"
        message += f"  • Total Alerts: {stats.get('total_alerts', 0)}\n"
        message += f"  • Critical: {stats.get('critical', 0)}\n"
        message += f"  • High: {stats.get('high', 0)}\n"
        message += f"  • Medium: {stats.get('medium', 0)}\n"
        message += f"  • Low: {stats.get('low', 0)}\n\n"
        
        message += f"🖥️ *Network:*\n"
        message += f"  • Active Devices: {stats.get('active_devices', 0)}\n"
        message += f"  • New Devices: {stats.get('new_devices', 0)}\n\n"
        
        message += f"✅ System Status: {'🟢 All Good' if stats.get('total_alerts', 0) == 0 else '🟠 Requires Attention'}"
        
        return self.send_message(message, disable_notification=True)
    
    def send_scan_results(self, devices: List[dict]) -> bool:
        """
        שליחת תוצאות סריקת רשת
        
        Args:
            devices: רשימת מכשירים
            
        Returns:
            True אם נשלח
        """
        message = "🔍 *NETWORK SCAN COMPLETE*\n\n"
        message += f"Found {len(devices)} device(s):\n\n"
        
        for device in devices[:10]:  # רק 10 ראשונים (הגבלת אורך)
            status = "🆕" if device.get('is_new') else "✅"
            message += f"{status} `{device['ip']}`"
            if device.get('hostname'):
                message += f" - {device['hostname']}"
            message += f" ({device.get('vendor', 'Unknown')})\n"
        
        if len(devices) > 10:
            message += f"\n... and {len(devices) - 10} more devices"
        
        message += f"\n\n🕐 {datetime.now().strftime('%H:%M:%S')}"
        
        return self.send_message(message, disable_notification=True)
    
    @staticmethod
    def get_chat_id(bot_token: str) -> Optional[str]:
        """
        Helper function לקבלת CHAT_ID
        
        שלבים:
        1. שלח /start לבוט שלך בטלגרם
        2. הרץ פונקציה זו
        3. תקבל את הCHAT_ID שלך
        
        Args:
            bot_token: Token של הבוט
            
        Returns:
            CHAT_ID או None
        """
        try:
            url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if data['result']:
                    chat_id = data['result'][0]['message']['chat']['id']
                    print(f"✅ Your CHAT_ID: {chat_id}")
                    print(f"   Save this in your config file!")
                    return str(chat_id)
                else:
                    print("❌ No messages found!")
                    print("   Please send /start to your bot first")
                    return None
            else:
                print(f"❌ API Error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None


# ==== דוגמה לשימוש ====
if __name__ == "__main__":
    """
    Setup ובדיקת Telegram Bot
    """
    print("""
    ╔═════════════════════════════════════════════════════╗
    ║      ThetaWatch Home - Telegram Setup               ║
    ╚═════════════════════════════════════════════════════╝
    
    📱 Setup Instructions:
    ----------------------
    1. Open Telegram and search for @BotFather
    2. Send: /newbot
    3. Choose a name: "ThetaWatch Security Bot"
    4. Choose username: "YourName_ThetaWatch_bot"
    5. Copy the TOKEN you receive
    
    """)
    
    # בדיקת setup
    choice = input("Do you already have a bot token? (y/n): ")
    
    if choice.lower() == 'y':
        bot_token = input("\n📝 Enter your BOT TOKEN: ").strip()
        
        print("\n📱 Now, open Telegram and send /start to your bot")
        input("   Press ENTER when done...")
        
        print("\n🔍 Finding your CHAT_ID...")
        chat_id = TelegramAlerter.get_chat_id(bot_token)
        
        if chat_id:
            print("\n✅ Setup complete! Testing...")
            
            # Test the bot
            alerter = TelegramAlerter(bot_token, chat_id)
            
            # שלח הודעת בדיקה
            print("\n📤 Sending test message...")
            alerter.send_message("🎉 *ThetaWatch Home SIEM*\n\nTelegram alerts are now active!")
            
            # שלח התראת בדיקה
            print("📤 Sending test alert...")
            alerter.send_alert(
                severity="INFO",
                title="System Test",
                description="This is a test alert to verify Telegram integration",
                details={
                    "Status": "Online",
                    "Test": "Successful"
                }
            )
            
            print("\n✅ Check your Telegram for messages!")
            print("\n💾 Save these credentials:")
            print(f"   BOT_TOKEN: {bot_token}")
            print(f"   CHAT_ID: {chat_id}")
            
        else:
            print("\n❌ Failed to get CHAT_ID")
            print("   Make sure you sent /start to your bot!")
    
    else:
        print("\n📚 Follow the instructions above to create a bot first!")
        print("   Then run this script again.")
