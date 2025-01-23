from datetime import datetime, date, timedelta
from bs4 import BeautifulSoup
import time
import logging
import pytz

_LOGGER = logging.getLogger(__name__)


class Programme:
    def __init__(self, start, stop, title, desc,time_zone) -> None:
        """Initialize the sensor."""

        #_LOGGER.debug(f"timezone: {time_zone}")
        self._start = datetime.strptime(start, "%Y%m%d%H%M%S %z")
        self._stop = datetime.strptime(stop, "%Y%m%d%H%M%S %z")
        self.start_hour = self._start.astimezone(time_zone).strftime("%H:%M")
        self.end_hour = self._stop.astimezone(time_zone).strftime("%H:%M")
        self.title = title
        self.desc = desc
        #_LOGGER.debug(f"{self.title}\n{self.desc}\nstart: {self._start}now: {self._stop} start_hour: {self.start_hour} end_hour: {self.end_hour}")


class Channel:
    def __init__(self, id, name, lang,time_zone) -> None:
        """Initialize the sensor."""
        self._programmes = []
        self._name = name
        self.id = id
        self._lang = lang
        self._time_zone=time_zone



    def name(self) -> str:
        return self._name
    def id(self) -> str:
        return self.id
    def add_programme(self, programme) -> None:
        """Initialize the sensor."""
        self._programmes.append(programme)

    def get_programmes(self) -> dict[str, str]:
        ret = {}
        for programme in self._programmes:
            ret[
                programme.title
            ] = f"\n\tdesc: {programme.desc}\n\tstart: {programme.start_hour }\n\tend: {programme.end_hour }"
        return ret

    def get_programmes_by_start(self) -> dict[str, str]:
        ret = {}
        for programme in self._programmes:
            ret[programme.start_hour] = (
                "{ " + f'"title":{programme.title },"desc":  {programme.desc}  ' + " }"
            )
        return ret

    def get_programmes_from_now_by_start(self) -> dict[str, str]:
        ret = {}
        now = self._time_zone.localize(datetime.now())
        for programme in self._programmes:
            if programme._start >= now:
                ret[programme.start_hour] = (
                    "{ "
                    + f'"title":{programme.title },"desc":  {programme.desc}  '
                    + " }"
                )
        return ret

    def get_programmes_for_today(self) -> dict[str, str]:
        ret = {}
        ret["today"] = {}

        now = self._time_zone.localize(datetime.now())
        utc_offset=now.utcoffset().total_seconds()/60/60
        for programme in self._programmes:
            # add timezone offset to fix issue with start date is wrong day
            _start_date=(programme._start+ timedelta(hours=utc_offset)).date() 
            if (
                programme._start >= now
                and _start_date == datetime.today().date()
            ):
                obj = {}
                obj["title"] = programme.title
                obj["desc"] = programme.desc
                obj["start"] = programme.start_hour
                obj["end"] = programme.end_hour
                ret["today"][programme.start_hour] = obj
        return ret

    def get_programmes_per_day(self) -> dict[str, str]:
        ret = {}
        ret["today"] = {}
        ret["tomorrow"] = {}
        now = self._time_zone.localize(datetime.now())
        
        utc_offset=now.utcoffset().total_seconds()/60/60
        for programme in self._programmes:
            if programme._start >= now:
                _start_date=(programme._start+ timedelta(hours=utc_offset)).date() # add timezone offset to fix issue with time zone for
                if _start_date == datetime.today().date():
                    obj = {}
                    obj["title"] = programme.title
                    obj["desc"] = programme.desc
                    obj["start"] = programme.start_hour
                    obj["end"] = programme.end_hour
                    ret["today"][programme.start_hour] = obj
                else:
                    obj = {}
                    obj["title"] = programme.title
                    obj["desc"] = programme.desc
                    obj["start"] = programme.start_hour
                    obj["end"] = programme.end_hour
                    ret["tomorrow"][programme.start_hour] = obj

        return ret

    def get_current_programme(self) -> Programme:
        now = self._time_zone.localize(datetime.now())
        return next(
            (
                programme
                for programme in self._programmes
                if programme._start <= now <= programme._stop
            ),
            None,
        )
    def get_current_title(self) -> str:
        p=self.get_current_programme()
        if p is None:
            return "Unavilable"
        return p.title
    def get_current_desc(self) -> str:
        p=self.get_current_programme()
        if p is None:
            return "Unavilable"
        return p.desc
class Guide:
    TIMEZONE=None
    def __init__(self, text,time_zone) -> None:
        """Initialize the class"""
        self._channels = []
        self.TIMEZONE=time_zone
        soup = BeautifulSoup(text, "xml")

        for channel in soup.find_all("channel"):
            display_name = next(channel.children)
            _channel = Channel(channel["id"], display_name.text, display_name.get("lang"),time_zone)
            for prog in soup.find_all("programme", {"channel": channel["id"]}):
                children = prog.children
                title = next(children).text
                try:
                    desc = next(children).text
                    if not desc: #for generated files that contains <Sub-title>
                        desc = next(children).text
                except:
                    desc=""
                _prog = Programme(prog["start"], prog["stop"], title, desc,time_zone)
                _channel.add_programme(_prog)
            self.add_cahnnel(_channel)

    def add_cahnnel(self, channel) -> None:
        """Initialize the sensor."""
        self._channels.append(channel)

    def get_channel(self, id) -> Channel:
        return next(
            (channel for channel in self._channels if channel.id == id), None
        )
    def channels(self) :
        return self._channels
    def is_need_to_update(self) -> bool:
        """check if need to take new guide from web. (take once a day- guide is for 2 days)"""
        channel = self._channels[0]
        return not ( channel._programmes and(
            channel._programmes[-1]._start.date()
            == (datetime.today() + timedelta(days=1)).date() or #handle timezone issues
            channel._programmes[-1]._start.date()
            > (datetime.today() + timedelta(days=1)).date() )
        )
