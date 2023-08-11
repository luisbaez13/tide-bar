from datetime import datetime
import sqlite3
import time
import requests
import rumps

class TidesApp(rumps.App):
    def __init__(self):
        super(TidesApp, self).__init__('Tides')

    
        self.db_connection = sqlite3.connect("./tides.db")
        self.db_cur = self.db_connection.cursor()

        self.db_cur.execute("CREATE TABLE IF NOT EXISTS locations (id INTEGER, name TEXT, time REAL, UNIQUE(id))")

        #save default location incase its the first time startup
        self.db_cur.execute("INSERT OR IGNORE INTO locations VALUES (?, ?, ?)",
                   (8418150, "Portland, ME", time.time() )
                   )
        self.db_connection.commit()

        # get whatever was used last
        row = self.db_cur.execute("SELECT id, name, time FROM locations ORDER BY time DESC LIMIT 1",).fetchall()[0]
        self.station_id = row[0]
        self.location_name = row[1]

        self.icon = "./icons/waves.png"

        self.tides_info = [
            rumps.MenuItem('tide: NA'),
            rumps.MenuItem('tide: NA'),
            rumps.MenuItem('tide: NA'),
            rumps.MenuItem('tide: NA')
            ]

        self.location_description_menu = rumps.MenuItem(self.location_name+str(self.station_id))
        self.menu = [ 
            rumps.MenuItem("Refresh", callback=self.update_now), 
            self.location_description_menu,
            rumps.separator,
            self.tides_info[0],
            self.tides_info[1],
            self.tides_info[2],
            self.tides_info[3],
            rumps.separator,
            rumps.MenuItem("Metric", callback=self.change_to_metric),
            rumps.MenuItem("Imperial", callback=self.change_to_imperial),
            ("Change Location",[]),
        ]

        self.db_cur.execute("CREATE TABLE IF NOT EXISTS units (type TEXT, time REAL, UNIQUE(type))")
        self.db_cur.execute("INSERT OR IGNORE INTO units VALUES (?, ?)",
                        ("english" ,time.time() )
                   )
        row = self.db_cur.execute("SELECT type, time FROM units ORDER BY time DESC LIMIT 1",).fetchall()[0]
        self.db_connection.commit()
        self.units = row[0]
        if row[0] == "english":
            self.menu["Imperial"].state = 1
        elif row[0] == "metric":
            self.menu["Metric"].state = 1

        self.last_update = datetime.now().date()
        self.update()

    def update(self):
        base = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?date=today&"
        base += "station=" + str(self.station_id)
        base += "&product=predictions"
        base += "&interval=hilo"
        base += "&datum=MLLW"

        if time.localtime().tm_isdst:
            base += "&time_zone=lst_ldt" 
        else:
            base += "&time_zone=lst"

        base += "&units=" + self.units 
        base += "&format=json"

        r = requests.get(base)
        data = r.json()

        if self.menu["Imperial"].state:
            unit_str = "ft"
        else:
            unit_str = "m"

        if "predictions" not in data:
             return False

        p = data["predictions"]

        for i in range(4):
            if i < len(p) :
                self.tides_info[i].title = (p[i]["type"] + "  |  " + p[i]["v"] + " " + unit_str +"  |  " + p[i]["t"][-5:] )
            else:
                self.tides_info[i].title = "NA"

        #make another request to get the name of the station because you cant get the name and tide predictions in the same request
        nameQ = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/"
        nameQ += str(self.station_id) + ".json?type=tidepredictions&units=english"
        r = requests.get(nameQ)
        data = r.json()

        station = data["stations"][0]
        self.location_name = station["name"]

        state_name = station["state"]
        if state_name != "":
            self.location_name +=  ", " + state_name

        self.location_description_menu.title = self.location_name + ": " + str(self.station_id)

        #update time, or insert new row
        self.db_cur.execute("INSERT OR REPLACE INTO locations VALUES (?, ?, ?)",
                       (self.station_id, self.location_name, time.time())
                       )
        self.db_connection.commit()

        self.last_update = datetime.now().date()
        self.update_history()

        return True

    def update_now(self, _):
        self.update()

    # check if the app should update every hour, but only make the full update if its the next day and new predictions are out
    @rumps.timer(interval=60*60 )
    def auto_update(self, _):
        if self.last_update < datetime.now().date():
            print("Auto updated")
            self.update()

    def change_to_metric(self, _):
        self.units = "metric"
        self.menu["Imperial"].state = 0
        self.menu["Metric"].state = 1
        self.db_cur.execute("INSERT OR REPLACE INTO units VALUES (?, ?)",
                       ("metric", time.time())
                       )
        self.db_connection.commit()
        self.update()

    def change_to_imperial(self, _):
        self.units = "english"
        self.menu["Imperial"].state = 1
        self.menu["Metric"].state = 0
        self.db_cur.execute("INSERT OR REPLACE INTO units VALUES (?, ?)",
                       ("english", time.time())
                       )
        self.db_connection.commit()
        self.update()

    def add_station(self, _):
        window = rumps.Window(dimensions = (90, 25), default_text="0000000")
        window.message = 'Find the station id for your location here:\n\nhttps://tidesandcurrents.noaa.gov/stations.html?type=Harmonic%20Constituents&sort=1\n\nEnter the 7 digit Id below'
        window.icon = 'icons/waves.png'
        window.title = 'Change Location'
        loc = window.run().text
        loc = loc.strip("[]. '\"")
        self.station_id = loc
        sucsess = self.update()

        if sucsess:
            rumps.alert("Changed to " + self.location_name + ": " + str(self.station_id) + " successfully!")
        else:
             rumps.alert("Error: station '" + str(self.station_id)+ "' Not found!")

    def change_known(self,sender):
        self.station_id = int(sender.title[-7:])
        success = self.update()
        if not success:
            rumps.alert("Error: station '" + str(self.station_id)+ "' Not found!")

    def update_history(self):
        del self.menu["Change Location"]
        # for item in self.menu["Change Location"]:
        #     self.menu.__delitem__(item)
        self.locations_menu = ('Change Location',[])
        self.menu.insert_after("Imperial", 'Change Location')
        self.menu["Change Location"].add(rumps.MenuItem("Add New", callback=self.add_station))
        self.menu["Change Location"].add(rumps.separator)

        # #sort by time field...
        rows = self.db_cur.execute("SELECT id, name, time FROM locations ORDER BY time DESC LIMIT 20",).fetchall()

        for idx,r in enumerate(rows):
            formatted_name =r[1] +": "+ str(r[0])
            region_name = rumps.MenuItem(formatted_name, callback=self.change_known)
            if idx == 0:
                region_name.state = 1
            self.menu["Change Location"].add(region_name)

if __name__ == "__main__":
    TidesApp().run()