#!/usr/bin/env python3
"""
Twilio Voice Call Library
Can be used as a standalone script or imported into other Python scripts
"""

import os
import asyncio
import edge_tts
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import argparse
import json
from pathlib import Path
from typing import Optional, Dict, List, Union

class TwilioVoiceAPI:
    """
    Main Twilio Voice API class for making calls and managing voice services
    Can be imported and used in other scripts
    """
    
    def __init__(self, account_sid: Optional[str] = None, auth_token: Optional[str] = None):
        """
        Initialize Twilio Voice API
        
        Args:
            account_sid: Twilio Account SID (optional, will use env var if not provided)
            auth_token: Twilio Auth Token (optional, will use env var if not provided)
        """
        self.account_sid = account_sid or os.environ.get("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.environ.get("TWILIO_AUTH_TOKEN")
        self.client = None
        self.config_file = "voice_config.json"
        
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
    
    def is_configured(self) -> bool:
        """Check if Twilio credentials are properly configured"""
        return bool(self.account_sid and self.auth_token and self.client)
    
    def get_setup_instructions(self) -> str:
        """Get setup instructions for Twilio credentials"""
        return """
🔧 Twilio Setup Instructions:

1. Get credentials from: https://console.twilio.com/
2. Set environment variables:
   export TWILIO_ACCOUNT_SID='your_account_sid'
   export TWILIO_AUTH_TOKEN='your_auth_token'
3. Buy a Twilio phone number from console
4. Test your setup
        """.strip()
    
    def make_call(self, 
                  to_number: str, 
                  from_number: str, 
                  message: str, 
                  voice: str = "man") -> Optional[str]:
        """
        Make a voice call using Twilio
        
        Args:
            to_number: Phone number to call (e.g., "+1234567890")
            from_number: Your Twilio phone number
            message: Message to speak
            voice: Voice to use (alice, man, woman, Polly.Joanna, etc.)
            
        Returns:
            Call SID if successful, None if failed
        """
        if not self.is_configured():
            print("❌ Twilio not configured. Use get_setup_instructions() for help.")
            return None
        
        # Create TwiML response
        response = VoiceResponse()
        response.say(message, voice=voice)
        twiml = str(response)
        
        try:
            call = self.client.calls.create(
                twiml=twiml,
                to=to_number,
                from_=from_number,
            )
            
            return call.sid
            
        except Exception as e:
            print(f"❌ Error making call: {e}")
            return None
    
    def make_call_verbose(self, 
                         to_number: str, 
                         from_number: str, 
                         message: str, 
                         voice: str = "alice") -> Optional[str]:
        """
        Make a voice call with verbose output (good for testing/debugging)
        
        Args:
            to_number: Phone number to call
            from_number: Your Twilio phone number  
            message: Message to speak
            voice: Voice to use
            
        Returns:
            Call SID if successful, None if failed
        """
        if not self.is_configured():
            print("❌ Twilio credentials not found!")
            print(self.get_setup_instructions())
            return None
        
        print(f"📞 Making call...")
        print(f"   From: {from_number}")
        print(f"   To: {to_number}")
        print(f"   Message: {message}")
        print(f"   Voice: {voice}")
        
        call_sid = self.make_call(to_number, from_number, message, voice)
        
        if call_sid:
            print(f"✅ Call initiated successfully!")
            print(f"   Call SID: {call_sid}")
            
            # Save to config for later reference
            self._save_last_call(call_sid, to_number, from_number)
        
        return call_sid
    
    def get_call_status(self, call_sid: str) -> Optional[Dict]:
        """
        Get the status of a call
        
        Args:
            call_sid: Twilio Call SID
            
        Returns:
            Dict with call information or None if error
        """
        if not self.is_configured():
            return None
        
        try:
            call = self.client.calls(call_sid).fetch()
            return {
                'sid': call.sid,
                'status': call.status,
                'duration': call.duration,
                'price': call.price,
                'price_unit': call.price_unit,
                'from': call._from,
                'to': call.to,
                'date_created': call.date_created.isoformat() if call.date_created else None
            }
        except Exception as e:
            print(f"❌ Error fetching call status: {e}")
            return None
    
    def list_recent_calls(self, limit: int = 5) -> List[Dict]:
        """
        List recent calls
        
        Args:
            limit: Number of calls to retrieve
            
        Returns:
            List of call dictionaries
        """
        if not self.is_configured():
            return []
        
        try:
            calls = self.client.calls.list(limit=limit)
            return [
                {
                    'sid': call.sid,
                    'from': call.from_,
                    'to': call.to,
                    'status': call.status,
                    'duration': call.duration,
                    'date_created': call.date_created.strftime('%Y-%m-%d %H:%M:%S') if call.date_created else 'Unknown'
                }
                for call in calls
            ]
        except Exception as e:
            print(f"❌ Error listing calls: {e}")
            return []
    
    def play_audio_url(self, 
                       to_number: str, 
                       from_number: str, 
                       audio_url: str) -> Optional[str]:
        """
        Make a call that plays an audio file from a URL
        
        Args:
            to_number: Phone number to call
            from_number: Your Twilio phone number
            audio_url: URL to audio file (MP3, WAV, etc.)
            
        Returns:
            Call SID if successful, None if failed
        """
        if not self.is_configured():
            return None
        
        response = VoiceResponse()
        response.play(audio_url)
        twiml = str(response)
        
        try:
            call = self.client.calls.create(
                twiml=twiml,
                to=to_number,
                from_=from_number,
            )
            return call.sid
        except Exception as e:
            print(f"❌ Error making call: {e}")
            return None
    
    async def generate_voice_file(self, 
                                  text: str, 
                                  voice: str = "en-US-AriaNeural", 
                                  output_file: str = "voice.mp3") -> Optional[str]:
        """
        Generate voice file using Edge TTS
        
        Args:
            text: Text to convert to speech
            voice: Edge TTS voice to use
            output_file: Output filename
            
        Returns:
            Path to generated file or None if error
        """
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_file)
            return output_file
        except Exception as e:
            print(f"❌ Error generating voice: {e}")
            return None
    
    async def list_edge_voices(self) -> List[Dict]:
        """
        List available Edge TTS voices
        
        Returns:
            List of voice dictionaries
        """
        try:
            voices = await edge_tts.list_voices()
            return voices
        except Exception as e:
            print(f"❌ Error listing voices: {e}")
            return []
    
    def get_twilio_voices(self) -> List[str]:
        """
        Get list of available Twilio voices
        
        Returns:
            List of voice names
        """
        return [
            "alice",      # Female English (default)
            "man",        # Male English
            "woman",      # Female English
            "Polly.Joanna",   # AWS Polly Female US
            "Polly.Matthew",  # AWS Polly Male US
            "Polly.Amy",      # AWS Polly Female UK
            "Polly.Brian",    # AWS Polly Male UK
            "Polly.Emma",     # AWS Polly Female UK
        ]
    
    def _save_last_call(self, call_sid: str, to_number: str, from_number: str):
        """Save last call info to config file"""
        try:
            config = self._load_config()
            config.update({
                'last_call': call_sid,
                'last_to': to_number,
                'last_from': from_number
            })
            self._save_config(config)
        except:
            pass  # Ignore config errors
    
    def _load_config(self) -> Dict:
        """Load configuration from JSON file"""
        if Path(self.config_file).exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_config(self, config: Dict):
        """Save configuration to JSON file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except:
            pass  # Ignore save errors

# Convenience functions for quick usage
def quick_call(to_number: str, 
               from_number: str, 
               message: str, 
               voice: str = "alice") -> Optional[str]:
    """
    Quick function to make a call without creating a class instance
    
    Usage:
        from twilio_voice import quick_call
        quick_call("+1234567890", "+1987654321", "Hello World!")
    """
    api = TwilioVoiceAPI()
    return api.make_call(to_number, from_number, message, voice)

def quick_call_verbose(to_number: str, 
                      from_number: str, 
                      message: str, 
                      voice: str = "alice") -> Optional[str]:
    """
    Quick function to make a call with verbose output
    """
    api = TwilioVoiceAPI()
    return api.make_call_verbose(to_number, from_number, message, voice)

async def quick_generate_voice(text: str, 
                              voice: str = "en-US-AriaNeural", 
                              output_file: str = "voice.mp3") -> Optional[str]:
    """
    Quick function to generate voice file
    
    Usage:
        import asyncio
        from twilio_voice import quick_generate_voice
        asyncio.run(quick_generate_voice("Hello World!"))
    """
    api = TwilioVoiceAPI()
    return await api.generate_voice_file(text, voice, output_file)

# Command Line Interface (when run as script)
def print_banner():
    """Print application banner"""
    print("=" * 60)
    print("🎤 TWILIO VOICE API")
    print("Library + Command Line Interface")
    print("=" * 60)

async def main():
    """Main function for command line usage"""
    parser = argparse.ArgumentParser(description='Twilio Voice API')
    parser.add_argument('action', choices=['call', 'voices', 'status', 'history', 'generate', 'setup'], 
                       help='Action to perform')
    parser.add_argument('--to', help='Phone number to call (e.g., +1234567890)')
    parser.add_argument('--from', dest='from_number', help='Twilio phone number to call from')
    parser.add_argument('--message', help='Message to speak')
    parser.add_argument('--voice', default='alice', help='Voice to use (alice, man, woman, Polly.Joanna, etc.)')
    parser.add_argument('--call-sid', help='Call SID to check status')
    parser.add_argument('--text', help='Text for Edge TTS generation')
    parser.add_argument('--edge-voice', default='en-US-AriaNeural', help='Edge TTS voice')
    
    args = parser.parse_args()
    
    print_banner()
    
    api = TwilioVoiceAPI()
    
    if args.action == 'setup':
        print(api.get_setup_instructions())
        
    elif args.action == 'call':
        if not args.to or not args.from_number:
            print("❌ Missing required arguments: --to and --from")
            print("Example: python script.py call --to=+1234567890 --from=+1twilio_number --message='Hello'")
            return
        
        message = args.message or "Hello! This is a test call from your Linux system using Twilio."
        api.make_call_verbose(args.to, args.from_number, message, args.voice)
    
    elif args.action == 'voices':
        print("🎵 Twilio Built-in Voices:")
        for voice in api.get_twilio_voices():
            print(f"  - {voice}")
        
        print("\n🎵 Edge TTS Voices (first 10):")
        voices = await api.list_edge_voices()
        for voice in voices[:10]:
            print(f"  - {voice['Name']}: {voice['DisplayName']} ({voice['Locale']})")
        print(f"   ... and {len(voices)-10} more")
    
    elif args.action == 'status':
        call_sid = args.call_sid
        if not call_sid:
            config = api._load_config()
            call_sid = config.get('last_call')
        
        if call_sid:
            status = api.get_call_status(call_sid)
            if status:
                print(f"📊 Call Status for {call_sid}:")
                for key, value in status.items():
                    print(f"  {key}: {value}")
        else:
            print("❌ No call SID provided or found")
    
    elif args.action == 'history':
        calls = api.list_recent_calls(10)
        if calls:
            print("📋 Recent Calls:")
            for call in calls:
                print(f"  {call['date_created']} | {call['from']} → {call['to']} | {call['status']} | {call['duration']}s")
        else:
            print("No recent calls found")
    
    elif args.action == 'generate':
        if not args.text:
            print("❌ Missing --text argument")
            return
        
        output_file = await api.generate_voice_file(args.text, args.edge_voice)
        if output_file:
            print(f"✅ Voice saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(main())

# Usage Examples for importing into other scripts:
"""
# Example 1: Simple call from another script
from twilio_voice import quick_call
call_sid = quick_call("+1234567890", "+1987654321", "Hello from my script!")

# Example 2: Using the full API class
from twilio_voice import TwilioVoiceAPI
api = TwilioVoiceAPI()
if api.is_configured():
    call_sid = api.make_call("+1234567890", "+1987654321", "Hello!")
    status = api.get_call_status(call_sid)
    print(f"Call status: {status['status']}")

# Example 3: Generate voice file and play it
import asyncio
from twilio_voice import TwilioVoiceAPI

async def make_custom_voice_call():
    api = TwilioVoiceAPI()
    
    # Generate voice file
    voice_file = await api.generate_voice_file("Hello from custom voice!")
    
    # Upload to your server and get URL
    audio_url = "https://yourserver.com/voice.mp3"
    
    # Make call with custom audio
    call_sid = api.play_audio_url("+1234567890", "+1987654321", audio_url)
    return call_sid

# Run: asyncio.run(make_custom_voice_call())
"""
