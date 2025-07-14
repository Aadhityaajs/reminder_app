#!/usr/bin/env python3

import requests
import time
import json
import os
import threading
from datetime import datetime, timedelta
from make_call import TwilioVoiceAPI

# Configuration
BOT_TOKEN = "7989138426:AAFvbq8pYAAp5RGMhTbAxqoKvlx-60tvu2k"
CHAT_ID = "1945078410"

# User states for multi-step input
user_state = {}

# Global flag to control reminder checking
reminder_running = False

def send_message(text, keyboard=None):
    """Send message to Telegram with optional keyboard"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': CHAT_ID, 
        'text': text,
        'parse_mode': 'HTML'
    }
    
    if keyboard:
        data['reply_markup'] = json.dumps(keyboard)
    
    try:
        response = requests.post(url, data=data)
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

def get_updates(offset=0):
    """Get updates from Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {'offset': offset, 'timeout': 10}
    response = requests.get(url, params=params)
    return response.json()

def create_main_keyboard():
    """Create main menu keyboard"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "➕ Add New Event", "callback_data": "add_event"}
            ],
            [
                {"text": "📅 View Today's Events", "callback_data": "today_events"}
            ],
            [
                {"text": "📋 View All Events", "callback_data": "all_events"}
            ],
            [
                {"text": "🗑️ Remove Event", "callback_data": "remove_event"}
            ]
        ]
    }
    return keyboard

def create_event_type_keyboard():
    """Create event type selection keyboard"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🎂 Birthday", "callback_data": "type_birthday"},
                {"text": "💼 Meeting", "callback_data": "type_meeting"}
            ],
            [
                {"text": "📅 Appointment", "callback_data": "type_appointment"},
                {"text": "🎉 Anniversary", "callback_data": "type_anniversary"}
            ],
            [
                {"text": "💊 Medicine", "callback_data": "type_medicine"},
                {"text": "🏃 Exercise", "callback_data": "type_exercise"}
            ],
            [
                {"text": "📝 Other", "callback_data": "type_other"}
            ],
            [
                {"text": "❌ Cancel", "callback_data": "cancel_event"}
            ]
        ]
    }
    return keyboard

def create_date_keyboard():
    """Create date selection keyboard for quick options"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📅 Today", "callback_data": "date_today"}
            ],
            [
                {"text": "📝 Enter Custom Date", "callback_data": "date_custom"}
            ],
            [
                {"text": "❌ Cancel", "callback_data": "cancel_event"}
            ]
        ]
    }
    return keyboard

def create_time_format_keyboard():
    """Create time format selection keyboard"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🌅 Morning (6:00 AM)", "callback_data": "time_06:00"},
                {"text": "🌞 Noon (12:00 PM)", "callback_data": "time_12:00"}
            ],
            [
                {"text": "🌇 Evening (6:00 PM)", "callback_data": "time_18:00"},
                {"text": "🌙 Night (9:00 PM)", "callback_data": "time_21:00"}
            ],
            [
                {"text": "🌃 Night Before (11:30 PM)", "callback_data": "time_previous_23:30"}
            ],
            [
                {"text": "⏰ Custom Time", "callback_data": "time_custom"}
            ],
            [
                {"text": "❌ Cancel", "callback_data": "cancel_event"}
            ]
        ]
    }
    return keyboard

def create_confirmation_keyboard():
    """Create yes/no confirmation keyboard"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Yes, Delete", "callback_data": "confirm_delete"},
                {"text": "❌ No, Cancel", "callback_data": "cancel_delete"}
            ]
        ]
    }
    return keyboard

def save_event(event_data):
    """Save event to events.json"""
    # Create events.json if it doesn't exist
    if not os.path.exists("events.json"):
        with open("events.json", "w") as file:
            json.dump([], file, indent=4)
    
    # Read existing events
    with open("events.json", "r") as file:
        events = json.load(file)
    
    # Add new event with unique ID
    event_data["id"] = str(int(time.time() * 1000))  # Unique timestamp ID
    events.append(event_data)
    
    # Save back to file
    with open("events.json", "w") as file:
        json.dump(events, file, indent=4)

def load_events():
    """Load events from events.json"""
    if not os.path.exists("events.json"):
        return []
    
    try:
        with open("events.json", "r") as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading events: {e}")
        return []

def save_events(events):
    """Save events to events.json"""
    try:
        with open("events.json", "w") as file:
            json.dump(events, file, indent=4)
    except Exception as e:
        print(f"Error saving events: {e}")

def mark_event_as_reminded(event_id):
    """Mark an event as reminded to avoid duplicate reminders"""
    events = load_events()
    for event in events:
        if event.get("id") == event_id:
            event["reminded"] = True
            break
    save_events(events)

def check_yearly_events(target_date):
    """Check for yearly recurring events (birthdays, anniversaries)"""
    events = load_events()
    yearly_events = []
    target_month_day = target_date[5:]  # Get MM-DD part
    
    for event in events:
        if event.get("recurring") == "yearly":
            event_month_day = event["date"][5:]  # Get MM-DD part from event
            
            # Check for same day events
            if event_month_day == target_month_day:
                # Calculate age/years for birthdays
                if event["type"] == "Birthday":
                    birth_year = int(event["date"][:4])
                    current_year = int(target_date[:4])
                    age = current_year - birth_year
                    event["age"] = age
                yearly_events.append(event)
            
            # Check for previous day reminders (11:30 PM night before)
            elif event.get("reminder_type") == "previous_day":
                # Calculate the day before the event
                event_date = datetime.strptime(f"{target_date[:4]}-{event_month_day}", "%Y-%m-%d")
                previous_day = (event_date - timedelta(days=1)).strftime("%Y-%m-%d")
                
                if previous_day == target_date:
                    # This is the night before reminder
                    if event["type"] == "Birthday":
                        birth_year = int(event["date"][:4])
                        current_year = int(target_date[:4]) + 1  # Next day's year
                        age = current_year - birth_year
                        event["age"] = age
                    
                    event["is_previous_day_reminder"] = True
                    yearly_events.append(event)
    
    return yearly_events

def check_and_send_reminders():
    """Check for due events and send reminders"""
    print("🔔 Checking for due reminders...")
    
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    
    events = load_events()
    reminders_sent = 0
    
    # Check regular events for today
    for event in events:
        # Skip if already reminded today
        if event.get("reminded") and event.get("last_reminded") == current_date:
            continue
            
        # Check non-recurring events
        if not event.get("recurring"):
            if event.get("date") == current_date:
                event_time = event.get("time", "")
                
                # Check if it's time for reminder (within 1 minute window)
                if abs(time_to_minutes(current_time) - time_to_minutes(event_time)) <= 1:
                    send_reminder(event)
                    event["reminded"] = True
                    event["last_reminded"] = current_date
                    reminders_sent += 1
    
    # Check yearly recurring events
    yearly_events = check_yearly_events(current_date)
    for yearly_event in yearly_events:
        # Find the original event in the events list
        original_event = None
        for event in events:
            if event.get("id") == yearly_event.get("id"):
                original_event = event
                break
        
        # Skip if original event is already reminded today
        if original_event and original_event.get("reminded") and original_event.get("last_reminded") == current_date:
            continue
            
        event_time = yearly_event.get("time", "")
        
        # Check if it's time for reminder
        if abs(time_to_minutes(current_time) - time_to_minutes(event_time)) <= 1:
            send_reminder(yearly_event)
            
            # Mark original event as reminded
            if original_event:
                original_event["reminded"] = True
                original_event["last_reminded"] = current_date
            
            reminders_sent += 1
    
    # Save updated events
    if reminders_sent > 0:
        save_events(events)
        print(f"✅ Sent {reminders_sent} reminders")
    
    return reminders_sent

def time_to_minutes(time_str):
    """Convert time string to minutes for comparison"""
    try:
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes
    except:
        return 0

def send_reminder(event):
    """Send reminder message for an event"""
    reminder_msg = f"🔔 <b>REMINDER!</b>\n\n"
    reminder_msg += f"🏷️ <b>Event:</b> {event['type']}\n"
    reminder_msg += f"📝 <b>Note:</b> {event['note']}\n"
    reminder_msg += f"📅 <b>Date:</b> {event['date']}\n"
    reminder_msg += f"⏰ <b>Time:</b> {event['time']}\n"
    
    if event.get("is_previous_day_reminder"):
        reminder_msg += f"\n🌃 <b>Tomorrow's Event Reminder!</b>\n"
        reminder_msg += f"Don't forget to wish at midnight! 🎉\n"
        if event.get("age"):
            reminder_msg += f"🎂 They'll be turning {event['age']} years old!\n"
    elif event.get("age"):
        reminder_msg += f"\n🎂 <b>Happy Birthday!</b> Turning {event['age']} years old! 🎉\n"
    elif event.get("recurring") == "yearly":
        reminder_msg += f"\n🔄 <b>Yearly Event</b> 🎉\n"
    
    reminder_msg += f"\n⏰ <b>Current Time:</b> {datetime.now().strftime('%H:%M')}"
    
    send_message(reminder_msg)
    print(f"📤 Reminder sent: {event['type']} - {event['note']}")
    try:
        api = TwilioVoiceAPI()
        if api.is_configured():        
            # Create TwiML for voice message
            twiml_message = f"Hello! This is a reminder from your event bot. You have a {event['type']} event: {event['note']} scheduled for {event['time']}. Please don't forget!"
            call_sid = api.make_call("+918883666174", "+12176725737", f"{twiml_message}")
            status = api.get_call_status(call_sid)
            print(status)
    except Exception as e:
        print(f"❌ Twilio call failed: {e}")
        print("💡 Please check your Twilio credentials and phone numbers")

def reminder_daemon():
    """Background daemon to check for reminders every minute"""
    global reminder_running
    reminder_running = True
    
    print("🔄 Reminder daemon started")
    
    while reminder_running:
        try:
            check_and_send_reminders()
            time.sleep(60)  # Check every minute
        except Exception as e:
            print(f"❌ Error in reminder daemon: {e}")
            time.sleep(60)  # Continue even if there's an error

def start_reminder_daemon():
    """Start the reminder daemon in a separate thread"""
    reminder_thread = threading.Thread(target=reminder_daemon, daemon=True)
    reminder_thread.start()
    print("🚀 Reminder daemon thread started")

def complete_event_creation():
    """Complete the event creation process"""
    try:
        if CHAT_ID not in user_state:
            return
            
        state = user_state[CHAT_ID]
        event = state["event"]
        
        # Validate event data
        if not event.get("type") or not event.get("note") or not event.get("date") or not event.get("time"):
            send_message("❌ Event creation failed: Missing required information. Please try again with /menu")
            if CHAT_ID in user_state:
                del user_state[CHAT_ID]
            return
        
        event["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        event["reminded"] = False  # Initialize reminder flag
        
        # Save the event
        save_event(event)
        
        # Show confirmation
        confirmation = f"""✅ <b>Event Added Successfully!</b>

📋 <b>Event Details:</b>
🏷️ <b>Type:</b> {event['type']}
📝 <b>Note:</b> {event['note']}
📅 <b>Date:</b> {event['date']}
⏰ <b>Time:</b> {event['time']}"""

        if event.get("recurring") == "yearly":
            confirmation += f"\n🔄 <b>Recurring:</b> Every year"
            if event.get("reminder_type") == "previous_day":
                confirmation += f"\n🌃 <b>Special:</b> Night before reminder (for midnight wishes!)"
        
        confirmation += f"\n\n🔔 <b>Reminder Status:</b> Active\nYour event has been saved and will remind you automatically!"
        
        send_message(confirmation)
        
        # Clear user state
        if CHAT_ID in user_state:
            del user_state[CHAT_ID]
            
    except Exception as e:
        print(f"❌ Error in complete_event_creation: {e}")
        # Clean up user state on error
        if CHAT_ID in user_state:
            del user_state[CHAT_ID]
        send_message("❌ Failed to create event. Please try again with /menu")

def handle_text_message(text):
    """Handle text messages based on user state"""
    try:
        if CHAT_ID not in user_state:
            return
        
        state = user_state[CHAT_ID]
        step = state["step"]
        
        if step == "note":
            state["event"]["note"] = text
            state["step"] = "date_selection"
            
            # For yearly events, show different message but same options
            if state["event"].get("recurring") == "yearly":
                keyboard = create_date_keyboard()
                send_message("➕ <b>Add New Event - Step 3/4</b>\n\nPlease select the <b>birth/anniversary date</b>:", keyboard)
            else:
                keyboard = create_date_keyboard()
                send_message("➕ <b>Add New Event - Step 3/4</b>\n\nPlease select the <b>event date</b>:", keyboard)
            
        elif step == "date":
            # Validate date format - accept both formats
            try:
                # Try YYYY MM DD format first
                if len(text.split()) == 3:
                    year, month, day = text.split()
                    formatted_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    datetime.strptime(formatted_date, "%Y-%m-%d")
                    state["event"]["date"] = formatted_date
                # Try YYYY-MM-DD format as fallback
                else:
                    datetime.strptime(text, "%Y-%m-%d")
                    state["event"]["date"] = text
                    
                state["step"] = "time"
                
                keyboard = create_time_format_keyboard()
                send_message("➕ <b>Add New Event - Step 4/4</b>\n\nPlease select the <b>reminder time</b>:", keyboard)
                
            except ValueError:
                send_message("❌ Invalid date format! Please use YYYY MM DD format (e.g., 2025 07 15)\nOr YYYY-MM-DD format (e.g., 2025-07-15)")
                
        elif step == "remove_select":
            # User entered a number to select event for removal
            try:
                selected_num = int(text)
                events = state.get("events", [])
                
                if 1 <= selected_num <= len(events):
                    selected_event = events[selected_num - 1]
                    
                    # Store the event to delete and change step
                    state["event_to_delete"] = selected_event
                    state["step"] = "remove_confirm"
                    
                    # Show the selected event details and confirmation
                    confirmation_msg = f"🗑️ <b>Confirm Event Deletion</b>\n\n"
                    confirmation_msg += f"📋 <b>Selected Event #{selected_num}:</b>\n\n"
                    confirmation_msg += f"🏷️ <b>Type:</b> {selected_event['type']}\n"
                    confirmation_msg += f"📝 <b>Note:</b> {selected_event['note']}\n"
                    confirmation_msg += f"📅 <b>Date:</b> {selected_event['date']}\n"
                    confirmation_msg += f"⏰ <b>Time:</b> {selected_event['time']}\n"
                    
                    if selected_event.get("recurring") == "yearly":
                        confirmation_msg += f"🔄 <b>Recurring:</b> Every year\n"
                        if selected_event.get("reminder_type") == "previous_day":
                            confirmation_msg += f"🌃 <b>Special:</b> Night before reminder\n"
                    
                    confirmation_msg += f"\n⚠️ <b>Are you sure you want to delete this event?</b>\n"
                    confirmation_msg += f"<i>This action cannot be undone.</i>"
                    
                    keyboard = create_confirmation_keyboard()
                    send_message(confirmation_msg, keyboard)
                    
                else:
                    send_message(f"❌ Invalid number! Please enter a number between 1 and {len(events)}")
                    
            except ValueError:
                send_message("❌ Invalid input! Please enter a valid number.")
                
        elif step == "custom_time":
            # Validate time format
            try:
                datetime.strptime(text, "%H:%M")
                state["event"]["time"] = text
                complete_event_creation()
                
            except ValueError:
                send_message("❌ Invalid time format! Please use HH:MM format (e.g., 14:30 or 09:15)")
                
    except Exception as e:
        print(f"❌ Error in handle_text_message: {e}")
        # Clean up user state on error
        if CHAT_ID in user_state:
            del user_state[CHAT_ID]
        send_message("❌ An error occurred while processing your message. Please try again with /menu")

def handle_callback_query(callback_query):
    """Handle button clicks"""
    try:
        callback_data = callback_query.get("data", "")
        callback_id = callback_query.get("id", "")
        
        # Answer the callback query (removes loading state)
        answer_url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
        requests.post(answer_url, data={"callback_query_id": callback_id})
        
        if callback_data == "add_event":
            user_state[CHAT_ID] = {"step": "event_type", "event": {}}
            keyboard = create_event_type_keyboard()
            send_message("➕ <b>Add New Event - Step 1/4</b>\n\nPlease select the <b>event type</b>:", keyboard)
            
        elif callback_data.startswith("type_"):
            event_type = callback_data[5:].replace("_", " ").title()
            user_state[CHAT_ID]["event"]["type"] = event_type
            user_state[CHAT_ID]["step"] = "note"
            
            # Set recurring for yearly events
            if event_type in ["Birthday", "Anniversary"]:
                user_state[CHAT_ID]["event"]["recurring"] = "yearly"
            
            send_message(f"➕ <b>Add New Event - Step 2/4</b>\n\nEvent Type: <b>{event_type}</b>\n\nPlease enter a <b>note</b> for this event:\n(e.g., John's birthday, Team meeting)")
            
        elif callback_data == "today_events":
            # Read and display today's events (including yearly recurring)
            today = datetime.now().strftime("%Y-%m-%d")
            today_events = []
            
            events = load_events()
            
            # Regular events for today
            today_events = [event for event in events if event.get("date") == today and not event.get("recurring")]
            
            # Yearly recurring events
            yearly_events = check_yearly_events(today)
            today_events.extend(yearly_events)
            
            if today_events:
                message = "📅 <b>Today's Events:</b>\n\n"
                for i, event in enumerate(today_events, 1):
                    message += f"{i}. <b>{event['type']}</b>\n"
                    message += f"   📝 {event['note']}\n"
                    message += f"   ⏰ {event['time']}\n"
                    
                    if event.get("is_previous_day_reminder"):
                        message += f"   🌃 <b>TOMORROW's reminder!</b> (Midnight wish alert)\n"
                        if event.get("age"):
                            message += f"   🎂 Will be turning {event['age']} years old tomorrow!\n"
                    elif event.get("age"):
                        message += f"   🎂 Turning {event['age']} years old!\n"
                    elif event.get("recurring") == "yearly":
                        message += f"   🔄 Yearly reminder\n"
                    
                    message += "\n"
            else:
                message = "📅 <b>Today's Events:</b>\n\nNo events scheduled for today."
            
            send_message(message)
            
        elif callback_data == "all_events":
            events = load_events()
            
            if events:
                message = "📋 <b>All Events:</b>\n\n"
                for i, event in enumerate(events, 1):
                    message += f"{i}. <b>{event['type']}</b>\n"
                    message += f"   📝 {event['note']}\n"
                    message += f"   📅 {event['date']}\n"
                    message += f"   ⏰ {event['time']}\n"
                    
                    if event.get("recurring") == "yearly":
                        message += f"   🔄 Yearly event\n"
                        if event.get("reminder_type") == "previous_day":
                            message += f"   🌃 Night before reminder\n"
                    
                    message += "\n"
            else:
                message = "📋 <b>All Events:</b>\n\nNo events found."
            
            send_message(message)
            
        elif callback_data.startswith("date_"):
            if callback_data == "date_today":
                # Set today's date automatically
                today_date = datetime.now().strftime("%Y-%m-%d")
                user_state[CHAT_ID]["event"]["date"] = today_date
                user_state[CHAT_ID]["step"] = "time"
                
                keyboard = create_time_format_keyboard()
                send_message(f"➕ <b>Add New Event - Step 4/4</b>\n\n📅 <b>Date set to:</b> {today_date} (Today)\n\nPlease select the <b>reminder time</b>:", keyboard)
                
            elif callback_data == "date_custom":
                user_state[CHAT_ID]["step"] = "date"
                
                if user_state[CHAT_ID]["event"].get("recurring") == "yearly":
                    send_message("➕ <b>Add New Event - Step 3/4</b>\n\nPlease enter the <b>birth/anniversary date</b>:\n(Format: YYYY MM DD, e.g., 1995 07 12)\n\n<i>Note: This will remind you every year on this date!</i>")
                else:
                    send_message("➕ <b>Add New Event - Step 3/4</b>\n\nPlease enter the <b>date</b> for the reminder:\n(Format: YYYY MM DD, e.g., 2025 07 15)")
        
        elif callback_data.startswith("time_"):
            if callback_data == "time_custom":
                user_state[CHAT_ID]["step"] = "custom_time"
                send_message("➕ <b>Add New Event - Step 4/4</b>\n\nPlease enter <b>custom time</b>:\n(Format: HH:MM, e.g., 14:30 or 09:15)")
            elif callback_data == "time_previous_23:30":
                # Set reminder for previous day at 11:30 PM
                user_state[CHAT_ID]["event"]["time"] = "23:30"
                user_state[CHAT_ID]["event"]["reminder_type"] = "previous_day"
                complete_event_creation()
            else:
                time_value = callback_data[5:]  # Remove "time_" prefix
                user_state[CHAT_ID]["event"]["time"] = time_value
                complete_event_creation()
                
        elif callback_data == "cancel_event":
            if CHAT_ID in user_state:
                del user_state[CHAT_ID]
            send_message("❌ Event creation cancelled.")
            
        elif callback_data == "remove_event":
            events = load_events()
            
            if not events:
                send_message("🗑️ <b>Remove Event</b>\n\nNo events found to remove.")
                return
            
            # Set user state for removal process
            user_state[CHAT_ID] = {"step": "remove_select", "events": events}
            
            message = "🗑️ <b>Remove Event - Select Event to Delete</b>\n\n"
            for i, event in enumerate(events, 1):
                message += f"{i}. <b>{event['type']}</b>\n"
                message += f"   📝 {event['note']}\n"
                message += f"   📅 {event['date']}\n"
                message += f"   ⏰ {event['time']}\n"
                
                if event.get("recurring") == "yearly":
                    message += f"   🔄 Yearly event\n"
                    if event.get("reminder_type") == "previous_day":
                        message += f"   🌃 Night before reminder\n"
                
                message += "\n"
            
            message += f"\n📝 <b>Please enter the number (1-{len(events)}) of the event you want to remove:</b>"
            send_message(message)
            
        elif callback_data == "confirm_delete":
            if CHAT_ID in user_state and user_state[CHAT_ID].get("step") == "remove_confirm":
                # Get the event to delete
                event_to_delete = user_state[CHAT_ID]["event_to_delete"]
                events = load_events()
                
                # Remove the event
                updated_events = [e for e in events if e.get("id") != event_to_delete.get("id")]
                save_events(updated_events)
                
                # Clear user state
                del user_state[CHAT_ID]
                
                send_message(f"✅ <b>Event Deleted Successfully!</b>\n\n🗑️ The following event has been removed:\n\n<b>{event_to_delete['type']}</b>\n📝 {event_to_delete['note']}\n📅 {event_to_delete['date']}\n⏰ {event_to_delete['time']}")
            else:
                send_message("❌ No event selected for deletion.")
                
        elif callback_data == "cancel_delete":
            if CHAT_ID in user_state:
                del user_state[CHAT_ID]
            send_message("❌ Event deletion cancelled.")
            
    except Exception as e:
        print(f"❌ Error in handle_callback_query: {e}")
        print(f"Callback data: {callback_data}")
        import traceback
        traceback.print_exc()

def main():
    """Main bot loop with reminder daemon"""
    print("🤖 Enhanced Event Bot Starting...")
    
    # Start the reminder daemon
    start_reminder_daemon()
    
    send_message("🤖 Enhanced Event Bot started!\n🔔 Reminder system is now active!\nUse /menu to see options")
    
    # Create initial files if they don't exist
    if not os.path.exists("data.json"):
        with open("data.json", "w") as data:
            json.dump({"last_update_id": 0}, data, indent=4)
    
    if not os.path.exists("last_fetch.json"):
        with open("last_fetch.json", "w") as last_fetch:
            json.dump({}, last_fetch, indent=4)
    
    # Reset all reminder flags for today (fresh start)
    try:
        events = load_events()
        today = datetime.now().strftime("%Y-%m-%d")
        for event in events:
            if event.get("last_reminded") != today:
                event["reminded"] = False
        save_events(events)
    except Exception as e:
        print(f"❌ Error resetting reminder flags: {e}")
    
    while True:
        try:
            # Read last update ID
            try:
                with open("data.json", "r") as data:
                    last_update_id = json.load(data)["last_update_id"]
            except Exception as e:
                print(f"❌ Error reading data.json: {e}")
                last_update_id = 0

            # Read last fetch content
            try:
                with open("last_fetch.json", "r") as last_fetch:
                    last_fetch_content = json.load(last_fetch)
            except Exception as e:
                print(f"❌ Error reading last_fetch.json: {e}")
                last_fetch_content = {}
                
            # Get new updates
            latest_msg = get_updates(last_update_id + 1)

            # Only update if there are actual new messages
            if latest_msg.get("ok") and latest_msg.get("result") and last_fetch_content != latest_msg:
                print("📨 New message received")
                
                # Handle messages and button clicks
                for update in latest_msg["result"]:
                    try:
                        # Handle regular messages
                        if "message" in update:
                            message = update["message"]
                            text = message.get("text", "")
                            user_id = str(message.get("from", {}).get("id", ""))
                            
                            # Check if message is from authorized user
                            if user_id != CHAT_ID:
                                print(f"⚠️ Unauthorized user {user_id} attempted to use bot")
                                continue
                            
                            if text == "/menu":
                                keyboard = create_main_keyboard()
                                send_message("📋 <b>Event Manager</b>\n🔔 Reminder system is active!\n\nSelect an option:", keyboard)
                            elif text == "/status":
                                events = load_events()
                                active_reminders = len([e for e in events if not e.get("reminded", False)])
                                send_message(f"📊 <b>Bot Status:</b>\n🔔 Reminder daemon: Active\n📅 Total events: {len(events)}\n⏰ Pending reminders: {active_reminders}")
                            elif text.startswith("/"):
                                send_message("❓ Unknown command. Use /menu to see available options.")
                            else:
                                # Handle text input for event creation
                                handle_text_message(text)
                        
                        # Handle button clicks (callback queries)
                        elif "callback_query" in update:
                            callback_query = update["callback_query"]
                            user_id = str(callback_query.get("from", {}).get("id", ""))
                            
                            # Check if callback is from authorized user
                            if user_id != CHAT_ID:
                                print(f"⚠️ Unauthorized user {user_id} attempted to use bot")
                                continue
                                
                            handle_callback_query(callback_query)
                            
                    except Exception as e:
                        print(f"❌ Error processing update: {e}")
                        print(f"Update data: {update}")
                        continue
                
                # Update last_update_id correctly
                try:
                    new_last_id = last_update_id
                    for update in latest_msg["result"]:
                        if "update_id" in update:
                            new_last_id = update["update_id"]
                    
                    # Save new last_update_id
                    with open("data.json", "w") as data:
                        json.dump({"last_update_id": new_last_id}, data, indent=4)

                    # Save latest fetch (only when there are actual messages)
                    with open("last_fetch.json", "w") as last_fetch:
                        json.dump(latest_msg, last_fetch, indent=4)
                        
                except Exception as e:
                    print(f"❌ Error saving update data: {e}")
        
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
            global reminder_running
            reminder_running = False
            break
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
        
        time.sleep(1)

if __name__ == "__main__":
    main()