"""Support for  HA_EPG."""

from __future__ import annotations
import logging

from typing import Final
import os
import datetime
from .guide_classes import Guide
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.config_entries import ConfigEntry

from homeassistant.components.sensor import (
    SensorEntity,
)
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)

import aiohttp
import pytz

from .const import (
    DOMAIN,
    ICON,
)
from datetime import timedelta
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

# Default scan interval
_LOGGER: Final = logging.getLogger(__name__)


class EpgDataUpdateCoordinator(DataUpdateCoordinator[Guide | None]):
    """Class to manage fetching EPG data."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, config: dict):
        """Initialize."""
        self.config_entry = config_entry
        self.config_options = config  # Store options from config entry
        self.hass = hass
        self._guide: Guide | None = None

        # Define the update interval
        update_interval = timedelta(hours=24)  # <--- Set your desired interval here

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {config_entry.entry_id}",
            update_interval=update_interval,
        )

    def need_to_update(self, file_path: str) -> bool:
        """Check if the file needs to be updated."""
        if not os.path.exists(file_path):
            return True
        file_mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
        return (datetime.datetime.now() - file_mod_time) > timedelta(hours=24)

    async def _async_update_data(self) -> Guide | None:
        """Fetch data from API endpoint.

        if not self.need_to_update(file_path):
        """
        _LOGGER.debug("Coordinator: Starting data update")
        file_name = self.config_options.get("file_name")
        generated = self.config_options.get("generated", False)
        selected_channels = self.config_options.get("selected_channels", [])
        file_path = self.config_options.get("file_path")
        time_zone = await self.hass.async_add_executor_job(
            pytz.timezone, self.hass.config.time_zone
        )
        if not self.need_to_update(file_path):
            try:
                # Read file content asynchronously using executor job
                local_data = await self.hass.async_add_executor_job(
                    read_file, file_path
                )
                if not local_data:
                    _LOGGER.warning(
                        "Local file '%s' exists but is empty or could not be read.",
                        file_path,
                    )

                else:
                    guide = await self.hass.async_add_executor_job(
                        Guide, local_data, selected_channels, time_zone
                    )
                    _LOGGER.info(
                        "Successfully loaded EPG guide from local file: %s", file_path
                    )
                    self._guide = guide  # Update internal state
                    return guide  # Return the guide loaded from the file

            except FileNotFoundError:
                _LOGGER.warning(
                    "Local file '%s' not found unexpectedly. Will attempt network fetch.",
                    file_path,
                )
            except Exception as err:
                _LOGGER.error(
                    "Failed to read or parse local EPG file '%s': %s. "
                    "Will attempt to fetch from network.",
                    file_path,
                    err,
                )
        if generated:
            guide_url = f"https://www.open-epg.com/generate/{file_name}.xml"
            selected_channels_param = "ALL"  # Guide class handles "ALL"
        else:
            # Ensure filename is clean for URL
            clean_file_name = "".join(file_name.split()).lower()
            guide_url = f"https://www.open-epg.com/files/{clean_file_name}.xml"
            selected_channels_param = selected_channels

        session = async_get_clientsession(self.hass)

        guide = None

        try:
            _LOGGER.debug("Coordinator: Fetching guide from %s", guide_url)
            response = await session.get(guide_url)
            response.raise_for_status()
            data = await response.text()

            if data and "channel" in data:
                _LOGGER.debug(
                    f"Coordinator: Successfully fetched guide data for {file_name}"
                )

                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                # Write the fetched data to the file asynchronously
                await self.hass.async_add_executor_job(write_file, file_path, data)
                # Parse the guide data
                guide = await self.hass.async_add_executor_job(
                    Guide, data, selected_channels_param, time_zone
                )
                _LOGGER.debug(
                    f"Coordinator: Guide parsed with {len(guide.channels()) if guide else 0} channels."
                )
                self._guide = guide  # Store the latest guide
                return guide
            else:
                _LOGGER.error(
                    f"Coordinator: No valid 'channel' data received from {guide_url}. Response snippet: {data[:200]}"
                )
                return self._guide  # Keep old data on error

        except aiohttp.ClientError as err:
            _LOGGER.error(f"Coordinator: Error fetching guide from {guide_url}: {err}")
            return self._guide  # Keep old data on transient error
        except Exception as err:
            _LOGGER.exception(
                f"Coordinator: Unexpected error during update for {file_name}: {err}"
            )
            # Raise UpdateFailed for unexpected errors
            raise UpdateFailed(f"Unexpected error during update: {err}")


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Set up the EPG sensor platform."""

    async def handle_update_channels(call):
        """Handle the service call to manually refresh."""
        entry_id_to_refresh = call.data.get(
            "entry_id", config_entry.entry_id
        )  # Refresh specific or this entry
        _LOGGER.info(f"Manual refresh requested for entry_id: {entry_id_to_refresh}")
        coordinator_to_refresh = hass.data[DOMAIN].get(entry_id_to_refresh)
        if coordinator_to_refresh:
            await coordinator_to_refresh.async_request_refresh()
        else:
            _LOGGER.warning(
                f"Could not find coordinator for entry_id: {entry_id_to_refresh} to refresh."
            )

    # --- Service Handler: Search Program ---
    async def handle_search_program(
        call: ServiceCall,
    ) -> ServiceResponse:
        """Handle the service call to search for programs and return results."""
        search_title = call.data.get("title", "").lower()
        search_channel_name = call.data.get("channel_name")
        date_filter = call.data.get("date_filter", "all_future")
        target_entry_id = call.data.get("entry_id")

        # Validate required input
        if not search_title:
            _LOGGER.error("Search program service called without a title.")
            return {"results": []}

        _LOGGER.info(
            f"Starting EPG search for program title containing '{search_title}', "
            f"channel: '{search_channel_name or 'Any'}', "
            f"date filter: '{date_filter}', entry_id: '{target_entry_id or 'All Entries'}'"
        )

        search_results = []
        coordinators_to_search: list[EpgDataUpdateCoordinator] = []

        # Determine which coordinator(s) to search based on target_entry_id
        all_coordinators = hass.data.get(DOMAIN, {})
        if target_entry_id:
            coordinator = all_coordinators.get(target_entry_id)
            if coordinator and isinstance(coordinator, EpgDataUpdateCoordinator):
                coordinators_to_search.append(coordinator)
                _LOGGER.debug(f"Searching within specified entry: {target_entry_id}")
            else:
                _LOGGER.warning(
                    f"Search target entry_id '{target_entry_id}' not found or is not a valid EPG coordinator."
                )
        else:
            coordinators_to_search = [
                coord
                for coord in all_coordinators.values()
                if isinstance(coord, EpgDataUpdateCoordinator)
            ]
            _LOGGER.debug(
                f"Searching across {len(coordinators_to_search)} EPG entries."
            )

        if not coordinators_to_search:
            _LOGGER.warning("No valid EPG coordinators found to perform search.")
            return {"results": []}  # Return empty results

        for coordinator in coordinators_to_search:
            if (
                not coordinator.last_update_success
                or not coordinator.data
                or not isinstance(coordinator.data, Guide)
            ):
                _LOGGER.debug(
                    f"Skipping coordinator {coordinator.config_entry.entry_id}: "
                    f"No valid guide data available (last update success: {coordinator.last_update_success})."
                )
                continue

            guide: Guide = coordinator.data

            for channel in guide.channels():
                # Filter by channel name if specified by the user
                # Note: Channel names in guide data might include suffixes like HD, +1 etc.
                if search_channel_name and channel.name() != search_channel_name:
                    continue  # Skip this channel if name doesn't match filter
                all_programmes = channel.get_programmes_per_day()

                if date_filter in ["today", "any"]:
                    for programme in all_programmes.get("today", []).values():
                        # programme=all_programmes.get("today", []).get(key)
                        if search_title in programme.get("title").lower():
                            hour, minute = map(int, programme.get("start").split(":"))
                            start_datetime_iso = (
                                datetime.datetime.now()
                                .replace(
                                    hour=hour, minute=minute, second=0, microsecond=0
                                )
                                .isoformat()
                            )
                            search_results.append(
                                {
                                    "channel_name": channel.name(),
                                    "title": programme.get("title"),
                                    "description": programme.get("desc")
                                    or "No description",
                                    "start_time": programme.get("start"),
                                    "end_time": programme.get("end"),
                                    "date": datetime.date.today(),
                                    "start_datetime_iso": start_datetime_iso,
                                }
                            )
                if date_filter in ["tomorrow", "any"]:
                    for programme in all_programmes.get("tomorrow", []).values():
                        # Filter by program title (case-insensitive partial match)
                        if search_title in programme.get("title").lower():
                            hour, minute = map(int, programme.get("start").split(":"))
                            start_datetime_iso = (
                                (datetime.datetime.now() + timedelta(days=1))
                                .replace(
                                    hour=hour, minute=minute, second=0, microsecond=0
                                )
                                .isoformat()
                            )
                            search_results.append(
                                {
                                    "channel_name": channel.name(),
                                    "title": programme.get("title"),
                                    "description": programme.get("desc")
                                    or "No description",
                                    "start_time": programme.get("start"),
                                    "end_time": programme.get("end"),
                                    "date": datetime.date.today()
                                    + timedelta(1),  # YYYY-MM-DD date string (local)
                                    "start_datetime_iso": start_datetime_iso,
                                }
                            )
        # --- Finalize and Return Results ---
        _LOGGER.info(
            f"EPG search completed. Found {len(search_results)} matches for title '{search_title}'."
        )

        # Sort the collected results chronologically by their start time
        sorted_results = sorted(search_results, key=lambda x: x["start_datetime_iso"])

        # Return the results dictionary directly, conforming to the response schema
        return {"results": sorted_results}

    _LOGGER.debug(
        f"Setting up entry: {config_entry.entry_id} with options: {config_entry.options}"
    )
    config_options = config_entry.options

    coordinator = EpgDataUpdateCoordinator(hass, config_entry, config_options)
    await coordinator.async_config_entry_first_refresh()

    # Store the coordinator instance
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = coordinator

    # --- Create entities based on initial coordinator data ---
    entities = []
    if (
        coordinator.data
    ):  # Check if the initial fetch was successful and returned a Guide
        guide: Guide = coordinator.data  # Type hint for clarity
        _LOGGER.debug(f"Found {len(guide.channels())} channels in initial guide data.")

        file_name = config_options.get("file_name")
        generated = config_options.get("generated", False)

        if generated:
            # For generated guides, add all channels found
            for channel in guide.channels():
                _LOGGER.debug(
                    f"Generated file ({file_name}): adding channel {channel.name()} with {len(channel.get_programmes())} programmes"
                )
                entities.append(
                    ChannelSensor(
                        coordinator, channel.id, channel.name(), config_options
                    )
                )
        else:
            # For specific files, add only selected channels
            selected_channels_names = config_options.get("selected_channels", [])
            _LOGGER.debug(
                f"File ({file_name}): looking for selected channels: {selected_channels_names}"
            )
            for channel_name in selected_channels_names:
                channel = guide.get_channel_by_id(channel_name)
                if channel:
                    _LOGGER.debug(
                        f"File ({file_name}): adding channel {channel.name()} with {len(channel.get_programmes())} programmes"
                    )
                    entities.append(
                        ChannelSensor(
                            coordinator, channel.id, channel.name(), config_options
                        )
                    )
                else:
                    _LOGGER.warning(
                        f"File ({file_name}): selected channel '{channel_name}' not found in the guide data."
                    )
    else:
        _LOGGER.warning(
            f"Initial guide data fetch failed or returned no data for entry {config_entry.entry_id}. No sensors will be created initially."
        )
        # Depending on requirements, you might still want to add entities in an 'unavailable' state
        # or rely on the coordinator retrying later.

    if entities:
        async_add_entities(entities)
        _LOGGER.debug(
            f"Added {len(entities)} channel sensors for {config_entry.entry_id}"
        )
    else:
        _LOGGER.debug(f"No channel sensors added for {config_entry.entry_id}")

    hass.services.async_register(
        DOMAIN,
        "handle_update_channels",
        handle_update_channels,
    )
    # Register the search service (ensure it's registered only once)
    if not hass.services.has_service(DOMAIN, "search_program"):
        hass.services.async_register(
            DOMAIN,
            "search_program",
            handle_search_program,
            supports_response=SupportsResponse.ONLY,
        )
        _LOGGER.debug("Registered service: epg.search_program")
    else:
        _LOGGER.debug("Service epg.search_program already registered.")


def read_file(file):
    with open(file, "r") as guide_file:
        content = guide_file.readlines()
    content = "".join(content)
    return content


def write_file(file, data):
    with open(file, "w") as file:
        file.write(data)
        file.close()


class ChannelSensor(CoordinatorEntity[EpgDataUpdateCoordinator], SensorEntity):
    """Representation of a ChannelSensor ."""

    _attr_icon: str = ICON
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: EpgDataUpdateCoordinator,
        channel_id: str,
        channel_name: str,
        config_options: dict,
    ) -> None:
        """Initialize the sensor."""
        # Pass the coordinator to CoordinatorEntity
        super().__init__(coordinator)

        self._channel_id = channel_id
        self._channel_name = channel_name  # Keep original name for reference if needed
        self._config_options = config_options

        # Set unique ID and device info if you have a device associated with the config entry
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self._channel_id}"
        # Example device info - link sensor to the config entry's device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": f"EPG {config_options.get('file_name', coordinator.config_entry.entry_id)}",
            "manufacturer": "Open-EPG",  # Or your integration name
            "entry_type": "service",  # Or DEVICE_INFO_ENTRY_TYPE_SERVICE if imported
        }
        self._attr_name = f"{channel_name}"

    @property
    def _channel_data(self) -> Guide.Channel | None:
        """Helper to get the specific channel data from the coordinator."""
        if self.coordinator.data:
            return self.coordinator.data.get_channel_by_id(self._channel_id)
        return None

    @property
    def available(self) -> bool:
        """Return True if coordinator has data and channel exists."""
        # Sensor is available if the coordinator successfully updated
        # and the specific channel data can be retrieved.
        return super().available and self._channel_data is not None

    @property
    def native_value(self):  # Use native_value instead of state
        """Return the state of the device."""
        channel = self._channel_data
        if channel:
            current_title = channel.get_current_title()
            return (
                current_title if current_title is not None else "Unavailable"
            )  # Or None
        return "Unavailable"  # Or None if the channel data isn't found

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the state attributes."""
        channel = self._channel_data
        if not channel:
            return None

        if self._config_options.get("full_schedule"):
            ret = channel.get_programmes_per_day()
        else:
            ret = channel.get_programmes_for_today()

        # Ensure 'desc' key exists even if description is None
        ret["desc"] = channel.get_current_desc() or "No description"
        ret["sub_title"] = channel.get_current_subtitle() or "No subtitle"
        # Add next program info?
        next_prog = channel.get_next_programme()
        if next_prog:
            ret["next_program_title"] = next_prog.title
            ret["next_program_start_time"] = next_prog.start_hour
            ret["next_program_end_time"] = next_prog.end_hour
            ret["next_program_desc"] = next_prog.desc or "No description"
            ret["next_program_sub_title"] = next_prog.sub_title or "No subtitle"
        else:
            ret["next_program_title"] = "Unavailable"

        # Add channel metadata if useful
        ret["channel_id"] = channel.id
        ret["channel_display_name"] = channel.name()

        return ret
