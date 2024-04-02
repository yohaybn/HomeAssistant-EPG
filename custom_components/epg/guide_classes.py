from datetime import datetime, date, timedelta

from bs4 import BeautifulSoup

import time

from pytz import timezone


class Programme:
    def __init__(self, start, stop, title, desc) -> None:
        """Initialize the sensor."""
        self._start = datetime.strptime(start, "%Y%m%d%H%M%S %z")
        self._stop = datetime.strptime(stop, "%Y%m%d%H%M%S %z")
        self.start_hour = self._start.strftime("%H:%M")
        self.end_hour = self._stop.strftime("%H:%M")
        self.title = title
        self.desc = desc


class Channel:
    def __init__(self, id, name, lang) -> None:
        """Initialize the sensor."""
        self._programmes = []
        self._name = name
        self.id = id
        self._lang = lang
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
            ] = f"\n\tdesc: {programme.desc}\n\tstart: {programme.start_hour }\n\tend: {programme.stop_hour }"
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
        tz = timezone(Guide.tz)
        now = datetime.now(tz)
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

        tz = timezone(Guide.tz)
        now = datetime.now(tz)
        for programme in self._programmes:
            if (
                programme._start >= now
                and programme._start.date() == datetime.today().date()
            ):

                obj = {}
                obj["title"] = programme.title
                obj["desc"] = programme.desc
                ret["today"][programme.start_hour] = obj
        return ret

    def get_programmes_per_day(self) -> dict[str, str]:
        ret = {}
        ret["today"] = {}
        ret["tommorrow"] = {}
        tz = timezone(Guide.tz)
        now = datetime.now(tz)
        for programme in self._programmes:
            if programme._start >= now:
                if programme._start.date() == datetime.today().date():
                    obj = {}
                    obj["title"] = programme.title
                    obj["desc"] = programme.desc
                    ret["today"][programme.start_hour] = obj
                else:
                    obj = {}
                    obj["title"] = programme.title
                    obj["desc"] = programme.desc
                    ret["tommorrow"][programme.start_hour] = obj

        return ret

    def get_current_programme(self) -> Programme:
        tz = timezone(Guide.tz)
        now = datetime.now(tz)
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
    tz="Asia/Jerusalem"
    def __init__(self, text,tz="Asia/Jerusalem") -> None:
        """Initialize the class"""
        self._channels = []
        self.tz=tz
        soup = BeautifulSoup(text, "xml")

        for channel in soup.find_all("channel"):
            display_name = next(channel.children)
            _channel = Channel(channel["id"], display_name.text, display_name.get("lang"))
            for prog in soup.find_all("programme", {"channel": channel["id"]}):
                children = prog.children
                title = next(children).text
                try:
                    desc = next(children).text
                except:
                    desc=""
                _prog = Programme(prog["start"], prog["stop"], title, desc)
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
        return not ( channel._programmes and
            channel._programmes[-1]._start.date()
            == (datetime.today() + timedelta(days=1)).date()
        )
