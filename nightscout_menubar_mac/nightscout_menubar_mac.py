import datetime
import json
import traceback
import webbrowser

import requests
import rumps


class NightscoutMenuBarApp(object):
    def __init__(self):
        self.config = {
            "app_name": "Nightscout",
            "interval": 30,
            "ns_url": "https://ns.cormac.xyz",
            "alerts_enabled": True,
            "snooze_until": None
        }
        self.app = rumps.App(self.config["app_name"])
        self.timer = rumps.Timer(self.on_update, self.config["interval"])
        self.timer.start()
        
        self.url_button = rumps.MenuItem(
            title="Open Nightscout", callback=self.url_callback
        )
        self.battery = rumps.MenuItem(title="loading...")
        self.iob = rumps.MenuItem(title="loading...")
        self.cob = rumps.MenuItem(title="loading...")
        self.submenu = {
            'Preferences': [
                rumps.MenuItem(title="Enable Alerts", callback=self.alerts_callback),
                rumps.MenuItem(title="Disable Alerts", callback=self.alerts_callback),
                rumps.MenuItem(title="Snooze Alerts", callback=self.snooze_callback),
            ]
        }
        self.submenu["Preferences"][0].state = 1

        self.app.menu = [
            self.iob,
            self.cob,
            self.battery,
            None,
            self.url_button,
            self.submenu,
            None
        ]

    def on_update(self, sender):
        title = self.get_title()
        self.app.title = title
        extras = self.get_extras()
        self.iob.title = extras[0]
        self.cob.title = extras[1]
        self.battery.title = extras[2]
        self.run_alerts()


    def get_title(self):
        try:
            resp = requests.get(f"{self.config['ns_url']}/pebble")
            j = resp.json()
            bg = j["bgs"][0]
            sgv = bg["sgv"]
            delta = bg["bgdelta"]
            # If the delta doesn't start with a -, then we want to add a + to the front
            if not delta.startswith("-"):
                delta = f"+{delta}"
            direction = bg["direction"]
            direction = {
                "DoubleUp": "⇈",
                "SingleUp": "↑",
                "FortyFiveUp": "↗",
                "Flat": "→",
                "FortyFiveDown": "↘",
                "SingleDown": "↓",
                "DoubleDown": "⇊",
            }.get(direction, direction)
            time_delta = j["status"][0]["now"] - bg["datetime"]

            seconds = int(time_delta / 1000.0)
            mins = int(seconds / 60.0)

            age = {
                0: "\N{CIRCLED IDEOGRAPH ONE}",
                1: "\N{CIRCLED DIGIT ONE}",
                2: "\N{CIRCLED DIGIT TWO}",
                3: "\N{CIRCLED DIGIT THREE}",
                4: "\N{CIRCLED DIGIT FOUR}",
                5: "\N{CIRCLED DIGIT FIVE}",
                6: "\N{CIRCLED DIGIT SIX}",
                7: "\N{CIRCLED DIGIT SEVEN}",
                8: "\N{CIRCLED DIGIT EIGHT}",
                9: "\N{CIRCLED DIGIT NINE}",
            }.get(mins, mins)
            if age != mins:
                title = f"{age} {sgv} {delta}{direction}"
            else:
                if mins < 20:
                    title = f"{age}:{sgv} {delta}{direction}"
                else:
                    title = f"{mins} ago"
        except BaseException:
            title = "☠ error"
        print(f"{__file__} {datetime.datetime.utcnow()} {title}")
        return title

    def get_extras(self):
        try:
            resp = requests.get(f"{self.config['ns_url']}/pebble")
            j = resp.json()
            bg = j["bgs"][0]
            iob = f"💉 {bg['iob']}u"
            cob = f"🍞 {bg['cob']}g"
            battery = f"🔋 {bg['battery']}%"
        except BaseException:
            return []
        return [iob, cob, battery]

    def run_alerts(self):
        """ Send a notification if the glucose is above or below the thresholds """
        if not self.config["alerts_enabled"]:
            return
        if self.config["snooze_until"] is not None:
            if datetime.datetime.utcnow() < self.config["snooze_until"]:
                return
            else:
                self.config["snooze_until"] = None
                self.submenu["Preferences"][2].state = 0
        else:
            print("No snooze")
            try:
                resp = requests.get(f"{self.config['ns_url']}/pebble")
                j = resp.json()
                bg = j["bgs"][0]
                sgv = float(bg["sgv"])
                if sgv > 9.9:
                    rumps.notification(
                        title="High Glucose",
                        subtitle="Your glucose is above 9.9",
                        message=f"Your glucose is {sgv}",
                        sound=False,
                    )
                elif sgv < 3.9:
                    rumps.notification(
                        title="Low Glucose",
                        subtitle="Your glucose is below 3.9",
                        message=f"Your glucose is {sgv}",
                        sound=False,
                    )
            except BaseException:
                print(traceback.format_exc())

    def run(self):
        self.app.run()

    def url_callback(self, sender):
        webbrowser.open_new_tab(self.config["ns_url"])

    def alerts_callback(self, sender):
        # If the sender is Enable Alerts, then we want to set the config to True
        # If the sender is Disable Alerts, then we want to set the config to False
        # Put a checkmark next to the one that is enabled
        if sender.title == "Enable Alerts":
            self.config["alerts_enabled"] = True
            self.submenu["Preferences"][0].state = 1
            self.submenu["Preferences"][1].state = 0
        elif sender.title == "Disable Alerts":
            self.config["alerts_enabled"] = False
            self.submenu["Preferences"][1].state = 1
            self.submenu["Preferences"][0].state = 0
        else:
            raise ValueError("Unknown sender title")

    def snooze_callback(self, sender):
        # When the user clicks the snooze button, we want to set the snooze_until to the current time + 30 minutes
        print(self.config["snooze_until"])
        current_time = datetime.datetime.utcnow()
        self.config["snooze_until"] = current_time + datetime.timedelta(minutes=30)
        print(self.config["snooze_until"])
        self.submenu["Preferences"][2].state = 1

if __name__ == "__main__":
    app = NightscoutMenuBarApp()
    app.run()
