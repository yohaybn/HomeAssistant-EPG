"""Support for  HA_EPG."""
from __future__ import annotations
import logging

from typing import Final
import os
from .guide_classes import Guide
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import PlatformNotReady
from homeassistant.config_entries import ConfigEntry

from homeassistant.components.sensor import (
        SensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
)
import aiohttp
import pytz

from homeassistant.helpers.entity_registry import async_get as get_entity_registry
from .const import (
    DOMAIN,
    ICON,
    UPDATE_TOPIC,
)

# Default scan interval
_LOGGER: Final = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry, async_add_entities):
    """Set up the EPG sensor platform."""
    _config=config.data
    _hass=hass
    async def handle_update_channels(data):
        _LOGGER.debug(f"{data}")
        data=_hass.data[DOMAIN][data.data.get("entry_id")]
        await update_channels(data,True)

    async def update_channels(data,force):
        _LOGGER.debug("update_channels_start")
        _LOGGER.debug(f"data: {data}")
        entities = []
        guide = await get_guide(hass, data,force)
        generated= data.get("generated") or False
        name= data.get("file_name")
        if guide is not None:
            if generated:
                for channel  in guide.channels():
                    _LOGGER.debug(f"generated file ({name}): add cahnnel {channel.name()} with {len(channel.get_programmes())} programmes ")
                    entities.append(ChannelSensor(hass,data, channel.name(), channel))
            else:
                selected_channels =data.get("selected_channels")
                for ch in selected_channels:
                    channel=guide.get_channel(ch)
                    entities.append(ChannelSensor(hass,data, channel.name(), channel))
                    _LOGGER.debug(f"file ({name}): add cahnnel {ch} with {len(channel.get_programmes())} programmes ")
        else:
            _LOGGER.error(f"cannot load {name}")
        if force:
            registry = get_entity_registry(hass)
            for entity in entities:
                registry.async_remove(next((x for x in registry.entities if registry.entities.get(x).unique_id == entity.unique_id )))

        async_add_entities(entities, True)
        _LOGGER.debug("update_channels_end")




    await update_channels(_config,False)
    hass.services.async_register(
        DOMAIN,
        "handle_update_channels",
        handle_update_channels,
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



async def get_guide(hass: HomeAssistant, _config,force):
    file= _config.get("file_name")
    if _config.get("generated"):
        guide_url = f"https://www.open-epg.com/generate/{file}.xml"
    else:
        file=''.join(file.split()).lower()
        guide_url = f"https://www.open-epg.com/files/{file}.xml"
    guide_file = _config.get("file_path")

    if os.path.isfile(guide_file) and not force:
        _LOGGER.debug(f"Loading guide from existing file ({file})")
        content= await hass.async_add_executor_job(read_file, guide_file)
        time_zone= await hass.async_add_executor_job(pytz.timezone,hass.config.time_zone)
        guide = Guide(content,time_zone)
    else:
        if force:
            _LOGGER.debug(f"fetching the guide by force ({file})")
        else:
            _LOGGER.debug(f"fetching the guide first time ({file})")
        os.makedirs(os.path.dirname(guide_file), exist_ok=True)
        guide = await fetch_guide(hass,guide_url,guide_file)

    if guide is not None and guide.is_need_to_update():
        _LOGGER.debug(f"updating the guide ({file})")
        guide = await fetch_guide(hass,guide_url,guide_file)
    return guide

async def fetch_guide(hass: HomeAssistant,url,file) -> Guide:
    session = async_get_clientsession(hass)
    _LOGGER.debug("timezone: "+hass.config.time_zone)
    time_zone= await hass.async_add_executor_job(pytz.timezone,hass.config.time_zone)
    guide = None
    try:
        response = await session.get(url)
        response.raise_for_status()
        data = await response.text()
        if data is not None:
            if "channel" in data:
                await hass.async_add_executor_job(write_file, file,data)
                guide = Guide(data,time_zone)
            else:
                _LOGGER.error("Cannoat retrive date. data is: %s",data )
                raise PlatformNotReady("Connection to the service failed.\n %s",data )
        else:
            _LOGGER.error("Unable to retrieve guide from %s", url)
            raise PlatformNotReady("Connection to the service failed.")

    except aiohttp.ClientError as error:
        _LOGGER.error("Error while retrieving guide: %s", error)
        raise PlatformNotReady("Connection to the service failed.: %s", error)

    return guide


class ChannelSensor(SensorEntity):
    """Representation of a ChannelSensor ."""
    _attr_icon: str = ICON
    def __init__(self, hass,config, name, data) -> None:
        """Initialize the sensor."""
        self._data = data
        self._attributes: {}
        self._state: data.get_current_title()
        self._attr_name = f"{name[:-3]}"
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
        """Handle when the entity is added to Home Assistant."""

        self.async_on_remove(
            async_dispatcher_connect(self.hass, UPDATE_TOPIC, self._force_update)
        )

    async def _force_update(self) -> None:
        """Force update of data."""
        _LOGGER.debug("_force_update")
        self.async_write_ha_state()

