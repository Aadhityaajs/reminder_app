#!/usr/bin/env python3

import requests
import time
import json
import os
from datetime import datetime

# Configuration
BOT_TOKEN = "7989138426:AAFvbq8pYAAp5RGMhTbAxqoKvlx-60tvu2k"
CHAT_ID = "1945078410"

# User states for multi-step input
user_state = {}


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
    
    response = requests.post(url, data=data)
    return response.json()

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

def save_event(event_data):
    """Save event to events.json"""
    # Create events.json if it doesn't exist
    if not os.path.exists("events.json"):
        with open("events.json", "w") as file:
            json.dump([], file, indent=4)
    
    # Read existing events
    with open("events.json", "r") as file:
        events = json.load(file)
    
    # Add new event
    events.append(event_data)
    
    # Save back to file
    with open("events.json", "w") as file:
        json.dump(events, file, indent=4)

def check_yearly_events(target_date):
    """Check for yearly recurring events (birthdays, anniversaries)"""
    if not os.path.exists("events.json"):
        return []
    
    with open("events.json", "r") as file:
        events = json.load(file)
    
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
                from datetime import datetime, timedelta
                
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

def handle_callback_query(callback_query):
    """Handle button clicks"""
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
        
        if os.path.exists("events.json"):
            with open("events.json", "r") as file:
                events = json.load(file)
            
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
        send_message("🗑️ <b>Remove Event</b>\nThis feature will be available soon!")

def complete_event_creation():
    """Complete the event creation process"""
    if CHAT_ID not in user_state:
        return
        
    state = user_state[CHAT_ID]
    event = state["event"]
    event["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Save the event
    save_event(event)
    
    # Show confirmation
    confirmation = f"""
    ✅ <b>Event Added Successfully!</b>
    📋 <b>Event Details:</b>
    🏷️ <b>Type:</b> {event['type']}
    📝 <b>Note:</b> {event['note']}
    📅 <b>Date:</b> {event['date']}
    ⏰ <b>Time:</b> {event['time']}
    """

    if event.get("recurring") == "yearly":
        confirmation += f"\n🔄 <b>Recurring:</b> Every year"
        if event.get("reminder_type") == "previous_day":
            confirmation += f"\n🌃 <b>Special:</b> Night before reminder (for midnight wishes!)"
    
    confirmation += f"\n\nYour event has been saved!"
    
    send_message(confirmation)
    
    # Clear user state
    del user_state[CHAT_ID]

def handle_text_message(text):
    """Handle text messages based on user state"""
    if CHAT_ID not in user_state:
        return
    
    state = user_state[CHAT_ID]
    step = state["step"]
    
    if step == "note":
        state["event"]["note"] = text
        state["step"] = "date"
        
        if state["event"].get("recurring") == "yearly":
            send_message("➕ <b>Add New Event - Step 3/4</b>\n\nPlease enter the <b>birth/anniversary date</b>:\n(Format: YYYY-MM-DD, e.g., 1995-07-12)\n\n<i>Note: This will remind you every year on this date!</i>")
        else:
            send_message("➕ <b>Add New Event - Step 3/4</b>\n\nPlease enter the <b>date</b> for the reminder:\n(Format: YYYY-MM-DD, e.g., 2025-07-15)")
        
    elif step == "date":
        # Validate date format
        try:
            datetime.strptime(text, "%Y-%m-%d")
            state["event"]["date"] = text
            state["step"] = "time"
            
            keyboard = create_time_format_keyboard()
            send_message("➕ <b>Add New Event - Step 4/4</b>\n\nPlease select the <b>reminder time</b>:", keyboard)
            
        except ValueError:
            send_message("❌ Invalid date format! Please use YYYY-MM-DD format (e.g., 2025-07-15)")
            
    elif step == "custom_time":
        # Validate time format
        try:
            datetime.strptime(text, "%H:%M")
            state["event"]["time"] = text
            complete_event_creation()
            
        except ValueError:
            send_message("❌ Invalid time format! Please use HH:MM format (e.g., 14:30 or 09:15)")

def main():
    """Simple bot main loop"""
    print("🤖 Enhanced Event Bot Starting...")
    
    send_message("🤖 Enhanced Event Bot started!\nUse /menu to see options")
    
    # Create initial files if they don't exist
    if not os.path.exists("data.json"):
        with open("data.json", "w") as data:
            json.dump({"last_update_id": 0}, data, indent=4)
    
    if not os.path.exists("last_fetch.json"):
        with open("last_fetch.json", "w") as last_fetch:
            json.dump({}, last_fetch, indent=4)
    
    while True:
        try:
            # Read last update ID
            with open("data.json", "r") as data:
                last_update_id = json.load(data)["last_update_id"]
                print("last_update_id: ", last_update_id)

            # Read last fetch content
            with open("last_fetch.json", "r") as last_fetch:
                last_fetch_content = json.load(last_fetch)
                
            # Get new updates
            latest_msg = get_updates(last_update_id + 1)

            # Only update if there are actual new messages
            if latest_msg["ok"] and latest_msg["result"] and last_fetch_content != latest_msg:
                print(latest_msg)
                
                # Handle messages and button clicks
                for update in latest_msg["result"]:
                    
                    # Handle regular messages
                    if "message" in update:
                        message = update["message"]
                        text = message.get("text", "")
                        
                        if text == "/menu":
                            keyboard = create_main_keyboard()
                            send_message("📋 <b>Event Manager</b>\nSelect an option:", keyboard)
                        else:
                            # Handle text input for event creation
                            handle_text_message(text)
                    
                    # Handle button clicks (callback queries)
                    elif "callback_query" in update:
                        callback_query = update["callback_query"]
                        handle_callback_query(callback_query)
                
                # Update last_update_id correctly
                new_last_id = last_update_id
                for update in latest_msg["result"]:
                    new_last_id = update["update_id"]
                
                # Save new last_update_id
                with open("data.json", "w") as data:
                    json.dump({"last_update_id": new_last_id}, data, indent=4)

                # Save latest fetch (only when there are actual messages)
                with open("last_fetch.json", "w") as last_fetch:
                    json.dump(latest_msg, last_fetch, indent=4)
        
        except Exception as e:
            print(f"❌ Error: {e}")
        
        time.sleep(1)

if __name__ == "__main__":
    main()