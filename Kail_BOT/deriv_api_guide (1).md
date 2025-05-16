# Deriv API Setup Guide

This guide will help you set up your Deriv API token to use with the trading bot.

## Generate an API Token

1. Log in to your Deriv account at [app.deriv.com](https://app.deriv.com)
2. Click on your profile picture or icon in the top right corner
3. Select "Settings" from the dropdown menu
4. Click on "API token" in the left sidebar
5. Under "Create new token", enter a name for your token (e.g., "Trading Bot")
6. Enable the following permissions:
   - Read
   - Trade
   - Payments
   - Admin
7. Click "Create"
8. Copy your newly created API token (this will only be shown once)

## Configure the Bot

1. Open the `config.ini` file in a text editor
2. Replace `your_deriv_api_token` with the token you copied
3. Save the file

Example:
```ini
[API]
token = AbCdEfGhIjKlMnOpQrStUvWxYz1234567890
```

## Important Security Notes

- Never share your API token with anyone
- Store your config.ini file securely
- Consider using environment variables for the token in production

## Test Your Configuration

You can test if your API token is working correctly by running the bot in paper trading mode:

```bash
python trading_bot.py --paper
```

If the bot connects successfully and displays your account balance, your API token is working properly.

## Troubleshooting

If you encounter connection issues:

1. Verify your API token is entered correctly
2. Check that your Deriv account is active and not restricted
3. Ensure you have internet connectivity
4. Verify that you've granted all required permissions when creating the token
5. Try creating a new API token if issues persist

## Account Requirements

To use this bot with real trading:

1. You must have a funded Deriv account with binary options trading enabled
2. Your account should be set to USD as the base currency (recommended)
3. Ensure you have sufficient funds to meet the minimum stake requirements (usually $1 per trade)
4. Verify that the symbols you wish to trade are available during your trading hours

## API Rate Limits

Deriv imposes rate limits on API requests:
- No more than 5 requests per second
- No more than 60 requests per minute
- Excessive requests may result in temporary IP blocking

The bot is designed to respect these limits, but be aware if you're running multiple bots or applications using the same API token.

## Using Demo Accounts

For testing purposes, you can:

1. Create a Deriv demo account
2. Generate an API token for that demo account
3. Use that token in the bot configuration

This allows you to test the bot with virtual funds before risking real money.

## Additional Resources

- [Deriv API Documentation](https://developers.deriv.com/)
- [Deriv API Playground](https://api.deriv.com/playground/)
- [Binary Bot](https://bot.deriv.com/) (alternative visual bot builder)