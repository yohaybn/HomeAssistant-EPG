# HomeAssistant-Israeli_TV
HomeAssistant integration for Israeli TV channels.

The integration will create Media Source and services to play Israeli channels. also television programming will be provided in sensors.

## Installation

[![My Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=HomeAssistant-Israeli_TV&owner=yohaybn&category=Plugin)


Installation via [HACS](https://hacs.xyz/) (recommended) or by copying  `custom_components/israeli_tv` into your Home Assistant configuration directory.

## Configuration

The component requires configuration via the Home Assistant configuration file. The following parameters are required:

    # Example configuration.yaml entry
    ...
    israeli_tv:
        use_defaults: true #optinal- default = true 
        full_schedule: false #optinal- default = false 
        channels: #optinal
          - name: "כאן חינוכית"
            sensor_name: "kan_kids"
            url: https://kan23.media.kan.org.il/hls/live/2024691/2024691/master.m3u8
            thumbnail: https://www.kankids.org.il/favicon-kids/apple-touch-icon.png

    ...

To create sensors with television programming for the channels add 

    # Example configuration.yaml entry
    ...
    sensor:
      - platform: israeli_tv
    ...

| Name | Type | Default |  Description |
| --- | --- | --- | --- | 
| `use_defaults` | bool | true |  create sensors and services for israeli channels (11-14) |
| `full_schedule` | bool | false |  add full schedule to attributes (2 days). can create issues with recorder (`exceed maximum size of 16384 bytes. This can cause database performance issues; Attributes will not be stored`) |
| `channels` | channel array | optional | additional channels to use with services and media source  |
| `name` | string | **required** | name of channel as found [here](https://www.bevy.be/bevyfiles/israelpremium.xml.txt)   |
| `sensor_name` | string | **required** |  name for programming sensor |
| `url` | string | optional | m3u8 url that you provide. if not provided- just sensor will be created, but not media source |
| `thumbnail` | string | optional | thumbnail url that you provide for media source icon |



## Services

The following services are implemented by the component:
- `play_channel_XX` - enable you to play the selected channel in the media player that you choose

- `play_custom_channel` - enable you to play the selected channel (from the additional channels) in the media player that you choose
  ```
  service: israeli_tv.play_custom_channel
  data:
    channel_name: kan_kids ## the sensor_name from configuration entry
  target:
    entity_id: media_player.office_display```

- `get_channel_url` - get the url of channel in the response


## Automation example
```
- alias: Send channel 11
  description: 'Send link to mobile phone when show started'
  trigger:
  - platform: state
    entity_id:
    - sensor.israeli_tv_channel_11
      to: "חדשות הלילה"
  action:
  - service: israeli_tv.get_channel_url
    data: 
      channel_name: channel_11
    response_variable: channel
  - service: notify.mobile_app_XXXXX
    data:
      message: "האם תרצה לצפות?"
      title: "מתחילה עכשיו {{states( 'sensor.israeli_tv_channel_11')  }}"
      data:
        actions:
        - action: "URI" # Must be set to URI if you plan to use a URI
          title: "Open Url"
          uri: "{{channel.url }}"
  mode: single
```

## television programming lovelace card example
```
type: markdown
content: |

  {% for time in states.sensor.israeli_tv_channel_13.attributes.today -%}
    {% set program=states.sensor.israeli_tv_channel_13.attributes.today[time] %}
     <details>  
     <summary>{{time}}: {{ program.title}}</summary>
      {{ program.desc}}
    </details>
   {%- endfor %}.
title: שידורים להיום

```
## TODO

- Add more cahnnels.
- Make it generic
