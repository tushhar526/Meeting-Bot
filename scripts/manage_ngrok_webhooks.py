#!/usr/bin/env python3
"""
Ngrok Webhook Management Script
Helps manage webhook URLs when using ngrok for development
"""

import requests
import sys
import time

def check_ngrok_status():
    """Check ngrok status"""
    try:
        response = requests.get('http://127.0.0.1:4040/api/tunnels')
        response.raise_for_status()
        
        tunnels = response.json().get('tunnels', [])
        https_tunnel = None
        
        for tunnel in tunnels:
            if tunnel.get('proto') == 'https' and tunnel.get('status') == 'running':
                https_tunnel = tunnel
                break
        
        if https_tunnel:
            print(f"✅ Ngrok is running!")
            print(f"🌐 Public URL: {https_tunnel['public_url']}")
            print(f"📍 Local URL: {https_tunnel['config']['addr']}")
            return https_tunnel['public_url']
        else:
            print("❌ No active HTTPS tunnel found")
            print("📋 Available tunnels:")
            for tunnel in tunnels:
                print(f"   - {tunnel['proto']}: {tunnel['public_url']} -> {tunnel['config']['addr']}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Ngrok is not running or not accessible on port 4040")
        print("💡 Start ngrok with: ngrok http 5000")
        return None
    except Exception as e:
        print(f"❌ Error checking ngrok: {e}")
        return None

def update_webhooks(base_url):
    """Update all webhook URLs via API"""
    try:
        response = requests.post(f'{base_url}/webhooks/ngrok/update-webhooks')
        response.raise_for_status()
        
        result = response.json()
        if 'error' in result:
            print(f"❌ Failed to update webhooks: {result['error']}")
            return False
        
        print(f"✅ {result['message']}")
        print(f"🌐 New base URL: {result['new_base_url']}")
        
        if result.get('platform_counts'):
            print("📊 Updates by platform:")
            for platform, count in result['platform_counts'].items():
                print(f"   - {platform}: {count} webhooks")
        
        # Check if reintegration is required
        if result.get('reintegration_required'):
            print("\n⚠️  REINTEGRATION REQUIRED:")
            for platform in result['reintegration_required']:
                print(f"   ❌ {platform.title()} - Please reconnect your calendar")
            print("\n📝 Reconnect these platforms in your app to continue receiving webhook events.")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to app at {base_url}")
        print("💡 Make sure your Flask app is running")
        return False
    except Exception as e:
        print(f"❌ Error updating webhooks: {e}")
        return False

def check_webhook_status(base_url):
    """Check webhook status via API"""
    try:
        response = requests.get(f'{base_url}/webhooks/ngrok/status')
        response.raise_for_status()
        
        status = response.json()
        
        print("📊 Webhook Status:")
        print(f"   Ngrok Running: {'✅' if status['ngrok_running'] else '❌'}")
        print(f"   Current URL: {status['current_url'] or 'None'}")
        print(f"   Base URL: {status['webhook_base_url']}")
        print(f"   Status: {status['status']}")
        
        if status.get('error'):
            print(f"   Error: {status['error']}")
        
        return status
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to app at {base_url}")
        return None
    except Exception as e:
        print(f"❌ Error checking webhook status: {e}")
        return None

def main():
    """Main function"""
    print("🚀 Ngrok Webhook Manager")
    print("=" * 40)
    
    # Check if ngrok is running
    ngrok_url = check_ngrok_status()
    print()
    
    if not ngrok_url:
        print("❌ Please start ngrok first:")
        print("   ngrok http 5000")
        sys.exit(1)
    
    # Check webhook status
    print("📋 Checking webhook status...")
    webhook_status = check_webhook_status(ngrok_url)
    print()
    
    if webhook_status and webhook_status.get('ngrok_running'):
        print("🔄 Updating webhook URLs...")
        if update_webhooks(ngrok_url):
            print()
            print("✅ All done! Your webhooks are now updated to the new ngrok URL.")
            print(f"🌐 New webhook URLs will be: {ngrok_url}/webhooks/receive/{{platform}}")
        else:
            print("❌ Failed to update webhooks")
            sys.exit(1)
    else:
        print("❌ Webhook status check failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
