# HomeAssistant-EPG

Home Assistant integration for EPG (Electronic Program Guide) sensors, using the [open-epg.com EPG guide](https://www.open-epg.com/epg-guide/). This integration provides real-time program guide data as sensors within Home Assistant, allowing you to display current and upcoming TV programming.

## EPG Source Update

The integration now uses open-epg.com as its EPG data source. This change was implemented because bevy.be, the previous provider, has transitioned their services. This update is seamless for users and requires no configuration changes.

## Features
- Retrieve EPG data from open-epg.com to create program guide sensors in Home Assistant.
- Supports creating custom EPG files with specific channels for personalized tracking.
- Easy integration with Home Assistant's Lovelace UI to display TV programming data.

## Prerequisites
- **Home Assistant**: Ensure you have Home Assistant installed.
- **HACS**: [Home Assistant Community Store](https://hacs.xyz/) (recommended for easy installation).
- **open-epg.com Account**: Required if using custom EPG files.
  
## Installation 

### Installation via HACS (Recommended)
1. Open HACS in your Home Assistant dashboard.
2. Until this repository is part of HACS by default, you need to add it as a custom repository.
3. Go to *Integrations* > *Add custom repository* and enter:  ``` https://github.com/yohaybn/HomeAssistant-EPG ```


![Adding custom repository](/images/custom_repo.png)

4. Once added, search for "HomeAssistant-EPG" in HACS and install it.

[![My Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=HomeAssistant-EPG&owner=yohaybn)

### Manual Installation
1. Download the repository.
2. Copy the `custom_components/EPG` folder into your Home Assistant configuration directory under `custom_components`.



## Configuration

To configure EPG sensors for channels, add the following example entry to your `configuration.yaml` file:

    # Example configuration.yaml entry
    ...
    sensor:
      - platform: epg
        full_schedule: true
        files:
            - file: israelpremium
              name: all_israel
            - file: 122DjgdtAA
              generated: true
              name: channels
    ...

| Name | Type | Default |  Description |
| --- | --- | --- | --- | 
| `full_schedule` | bool | false |  Adds the full schedule (2 days) to attributes. May cause database issues with larger data (exceed maximum size of 16384 bytes) in Home Assistant. |
| `files` | file object array| **required** | Array of file objects. Each file object specifies an EPG file source (details below). |

| Name | Type | Default |  Description |
| --- | --- | --- | --- | 
| `file` | string | **required** | Name of the EPG file to use (e.g., argentinapremium2). File names can be found [here](https://www.open-epg.com/epg-guide/). |
| `name` | string | file name |  Name of the sensor for the file. A prefix of epg_ will be added (e.g., epg_all_israel).|
| `generated` | bool | false | Set to true if using custom files from open-epg.com. This will create a separate sensor for each channel in the file. See "Custom Files" for details. |


this will create sensor for each file contains the list of channels that can be tracked using service `track_channel`.

### Custom files
open-epg.com allows the creation of custom EPG files with selected channels. To create a custom file:
1. Register for a free account at open-epg.com.
2. Select channels to include in your custom EPG file.
3. Once generated (updated daily), use the unique file ID (e.g., 122DjgdtAA), visible in the generated URL.


## Services

The following services are implemented by the component:
- `track_channel` - add sensor for choosen channel
    ```
    service: epg.track_channel
    data:
        file: chinapremium2
        channel_id: AnhuiTV.cn
    ```
- `remove_channel` - delete sensor for choosen channel
  ```
     service: epg.remove_channel
    data:
        channel_id: AnhuiTV.cn
  ```





## Displaying Television Programming in Lovelace

Use the following example to display today’s programming on a Lovelace card:

```
type: markdown
content: |

  {% for time in states.sensor.epg_an_hui_wei_shi.attributes.today -%}
    {% set program=states.sensor.epg_an_hui_wei_shi.attributes.today[time] %}
     <details>  
     <summary>{{time}}: {{ program.title}}</summary>
      {{ program.desc}}
    </details>
   {%- endfor %}.
title: today

```
## Troubleshooting
- **Full Schedule Error**: If using full_schedule: true, you may encounter size limit issues in Home Assistant’s database. If so, set full_schedule: false.
- **Missing Channels**: Ensure you’re using the correct file ID, especially for custom files.
