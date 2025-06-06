# Telegram Coupon Bot

A powerful Telegram bot for managing and distributing digital coupons with QR code support

**Creator:** Anvarjon Toshmatov

## Features

### Admin Features
- 📝 Create new coupons with custom recipients and expiry dates
- 📊 View usage statistics and analytics
- 📋 List and manage all active coupons
- 🔍 Scan QR codes to validate coupons
- 📜 View history of used coupons
- 🗑 Delete coupons when needed

### User Features
- 🎫 View personal coupons
- 📱 Use coupons via QR code scanning

## Technical Requirements

- Python 3.7+
- Telegram Bot Token
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd coupon-bot
```

2. Create and activate a virtual environment:
```bash
python -m venv env
# On Windows
env\Scripts\activate
# On Unix or MacOS
source env/bin/activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with the following variables:
```
BOT_TOKEN=your_telegram_bot_token
ADMIN_ID=your_telegram_user_id
```

## Usage

1. Start the bot:
```bash
python bot.py
```

2. Open Telegram and start a chat with your bot

3. Use the following commands:
   - `/start` - Initialize the bot and show the main menu
   - For admins, additional commands will be available through the admin keyboard

## Data Storage

The bot uses three JSON files for data management:
- `coupons.json` - Stores active coupons
- `used_coupons.json` - Tracks used coupons
- `counters.json` - Maintains system counters

## Dependencies

- aiogram==3.3.0 - Telegram Bot Framework
- qrcode==7.4.2 - QR Code Generation
- fpdf2==2.7.6 - PDF Generation
- python-dotenv==1.0.0 - Environment Variable Management
- pillow==10.2.0 - Image Processing
- pyzbar==0.1.9 - QR Code Scanning
- numpy==1.26.4 - Numerical Operations
- opencv-python==4.9.0.80 - Computer Vision

## Security

- Admin-only access for sensitive operations
- Environment variables for secure configuration
- Unique coupon ID generation system
- QR code validation for coupon usage

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the repository or contact the maintainers.
