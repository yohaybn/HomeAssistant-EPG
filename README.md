# HomeAssistant-EPG
HomeAssistant integration for EPG (Electronic Program Guide) sensors using  [bevy.be EPG guide](https://www.bevy.be/epg-guide/). 

The integration will provide Program Guide in sensors.

## Installation 

Until the repository enters the default repository of HACS, you can add the repository to a custom repository in HACS
https://github.com/yohaybn/HomeAssistant-EPG

![custom_repo.png](/images/custom_repo.png)

[![My Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=HomeAssistant-EPG&owner=yohaybn)

Installation via [HACS](https://hacs.xyz/) (recommended) or by copying  `custom_components/EPG` into your Home Assistant configuration directory.

## Configuration

To create sensors with television programming for the channels add 

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
| `full_schedule` | bool | false |  add full schedule to attributes (2 days). can create issues with recorder (`exceed maximum size of 16384 bytes. This can cause database performance issues; Attributes will not be stored`) |
| `files` | file object array| **required** | array of file object (see table below) |

| Name | Type | Default |  Description |
| --- | --- | --- | --- | 
| `file` | string | **required** | file names which you want to use to create EPG. files name taken from  [here](https://www.bevy.be/epg-guide/), for example for https://www.bevy.be/bevyfiles/argentinapremium2.xml file enter `argentinapremium2` |
| `name` | string | file name |  sensor name for the file. will be with epg_ prefix. (e.g epg_all_israel) |
| `generated` | bool | false | flag for custom files, if true sensor will be create each channel in file. see below for more deatils  |


this will create sensor for each file contains the list of channels that can be tracked using service `track_channel`.

### Custom files
Thanks to the new feature bevy.be realeasd you can create custom file with channel that you choose.
To create custom file you need to open free account [here](https://www.bevy.be/app/register.php) and choose your channels.
once file generted  (once a day) you can use it. just put the ID that you get e.g. 122DjgdtAA (take it from URL that gennerated )


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





## television programming lovelace card example
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

