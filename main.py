from make_call import TwilioVoiceAPI

def reminder(msg):
    api = TwilioVoiceAPI()
    if api.is_configured():
        # call_sid = api.make_call("+918883666174", "+12176725737", f"Reminder {msg}")
        status = api.get_call_status("CAf2e1f398f5b073bffd644c7327695bd6")
        print(status)


reminder("There is a meeting by 12:30")