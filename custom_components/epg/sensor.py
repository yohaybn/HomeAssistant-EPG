"""Support for  HA_EPG."""
from __future__ import annotations
import logging

from typing import Final
import json
import os
from .guide_classes import Guide
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA as BASE_PLATFORM_SCHEMA,
        SensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
)
from homeassistant.helpers.entity_registry import async_get as get_entity_registry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
import aiohttp
from .const import (
    DOMAIN,
    ICON,
    UPDATE_TOPIC,
)


_LOGGER: Final = logging.getLogger(__name__)

_JSON_FILE = os.path.join(os.path.dirname(__file__), "userfiles/channels.json")



_config={}
async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the EPG sensor platform."""

    _config=config
    guides={}
    def read_json():

        with open(_JSON_FILE) as f:
          data = json.load(f)
        return data


    def write_json(data):
        _LOGGER.debug("write_packages_json")
        json_object = json.dumps(data, indent=4)
        with open(_JSON_FILE, "w") as outfile:
            outfile.write(json_object)


    async def track_channel(data):
        """track_channel"""
        _LOGGER.debug("track_channel")
        channel_id=data.data.get("channel_id")
        file=data.data.get("file")
        channel=guides.get(file).get_channel(channel_id)
        async_add_entities([ChannelSensor(hass,_config,  channel.name(), channel)], True)
        json = await hass.async_add_executor_job(read_json)
        json[channel_id] = file
        await hass.async_add_executor_job(write_json,json)


    async def remove_channel(in_data):
        _LOGGER.debug("remove_channel")
        channel_id=in_data.data.get("channel_id")
        registry = get_entity_registry(hass)
        registry.async_remove(next((x for x in registry.entities if registry.entities.get(x).unique_id == channel_id )))
        data = await hass.async_add_executor_job(read_json)
        del data[channel_id]
        await hass.async_add_executor_job(write_json,json)




    entities = []
    for file in _config.get("files"):
        guide = await get_guide(hass, _config, file)
        guides[file]=guide
        json_data =await hass.async_add_executor_job(read_json)
        for ch in json_data:
            if file == json_data.get(ch):
                channel=guide.get_channel(ch)
                entities.append(ChannelSensor(hass,_config, channel.name(), channel))
        entities.append(EPGSensor(hass,_config, file, guide))
    async_add_entities(entities, True)





    hass.services.async_register(
        DOMAIN,
        "track_channel",
        track_channel,
    )
    hass.services.async_register(
        DOMAIN,
        "remove_channel",
        remove_channel,
    )
def read_file(file):
    with open(file, "r") as guide_file:
        content = guide_file.readlines()
    content = "".join(content)
    return content
def write_file(file,data):
    with open(file, "w") as file:
        file.write(data)
        file.close()
async def get_guide(hass, _config, file):
    _GUIDE_URL = f"https://www.bevy.be/bevyfiles/{file}.xml"
    _GUIDE_FILE = os.path.join(os.path.dirname(__file__), f"userfiles/{file}.xml")
    if os.path.isfile(_GUIDE_FILE):
        #with open(_GUIDE_FILE, "r") as guide_file:
        #    content = guide_file.readlines()
        #content = "".join(content)
        content= await hass.async_add_executor_job(read_file, _GUIDE_FILE)
        guide = Guide(content,hass.config.time_zone)
    else:
        _LOGGER.debug("fetching the guide first time")
        os.makedirs(os.path.dirname(_GUIDE_FILE), exist_ok=True)
        guide = await fetch_guide(hass,_GUIDE_URL,_GUIDE_FILE)

    if guide is not None and guide.is_need_to_update():
        _LOGGER.debug("updating the guide")
        guide = await fetch_guide(hass,_GUIDE_URL,_GUIDE_FILE)
    return guide

async def fetch_guide(hass: HomeAssistant,url,file) -> Guide:
    session = async_get_clientsession(hass)
    _LOGGER.debug("timezone: "+hass.config.time_zone)
    guide = None
    try:
        response = await session.get(url)
        response.raise_for_status()
        data = await response.text()
        if data is not None:
            if "channel" in data:
                await hass.async_add_executor_job(write_file, file,data)
                #with open(file, "w") as file:
                #    file.write(data)
                #    file.close()
                guide = Guide(data,hass.config.time_zone)
            else:
                _LOGGER.error(data)
        else:
            _LOGGER.error("Unable to retrieve guide from %s", url)

    except aiohttp.ClientError as error:
        _LOGGER.error("Error while retrieving guide: %s", error)
    return guide


class ChannelSensor(SensorEntity):
    """Representation of a ChannelSensor ."""
    _attr_icon: str = ICON
    def __init__(self, hass,config, name, data) -> None:
        """Initialize the sensor."""
        _LOGGER.debug("ChannelSensor __init__ start")
        self._data = data
        self._attributes: {}
        self._state: data.get_current_title()
        self._attr_name = f"{DOMAIN}_{name}"
        self._hass = hass
        self._config=config

    @property
    def unique_id(self) -> str | None:
        return self._data.id

    @property
    def state(self):
        """Return the state of the device."""
        self._state = self._data.get_current_title()
        if self._state is None:
            return "Unavilable"
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        if self._config.get("full_schedule"):
            ret = self._data.get_programmes_per_day()
        else:
            ret = self._data.get_programmes_for_today()
        ret["desc"] = self._data.get_current_desc()
        return ret

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, UPDATE_TOPIC, self._force_update)
        )

    async def _force_update(self) -> None:
        """Force update of data."""
        self.async_write_ha_state()


class EPGSensor(SensorEntity):
    """Representation of a EPGSensor ."""
    _attr_icon: str = ICON
    def __init__(self, hass,config, name, data) -> None:
        """Initialize the sensor."""
        _LOGGER.debug("EPGSensor __init__ start")
        self._data = data
        self._attributes: {}
        self._state: len(data.channels())
        self._attr_name = f"{DOMAIN}_{name}"
        self._hass = hass
        self._config=config

    @property
    def unique_id(self) -> str | None:
        return self.name

    @property
    def state(self):
        if self._data.channels():
            return len(self._data.channels())
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        channels={}
        if self._data.channels():
            for ch in self._data.channels():
                channel = {"name":ch.name(),"id":ch.id}
                channels[ch.id]= channel
        attributes={"channels":channels}
        return attributes

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, UPDATE_TOPIC, self._force_update)
        )

    async def _force_update(self) -> None:
        """Force update of data."""
        self.async_write_ha_state()
