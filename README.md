# HomeAssistant-EPG
![icon](/images/icon@2x.png)

Home Assistant integration for EPG (Electronic Program Guide) sensors, using the [open-epg.com EPG guide](https://www.open-epg.com/app/index.php). This integration provides real-time program guide data as sensors within Home Assistant, allowing you to display current and upcoming TV programming.

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
2. Until this repository is part of HACS by default, you need to add it as a custom repository. (working on it)
3. Go to *Integrations* > *Add custom repository* and enter:  ``` https://github.com/yohaybn/HomeAssistant-EPG ```


![Adding custom repository](/images/custom_repo.png)

4. Once added, search for "HomeAssistant-EPG" in HACS and install it.

[![My Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=HomeAssistant-EPG&owner=yohaybn)

### Manual Installation
1. Download the repository.
2. Copy the `custom_components/EPG` folder into your Home Assistant configuration directory under `custom_components`.



## Configuration

### Using the Config Flow

The integration now uses Home Assistant's UI configuration flow, making it easier to set up and manage. Follow these steps to configure:

1.  Go to **Settings > Devices & Services** in Home Assistant.
    
2.  Click **Add Integration** and search for "EPG".
    
3.  Follow the prompts:
    
    -   **File Name**: Enter the file name or generated file code from open-epg.com.
        
    -   **Track Full Schedule**: Enable this option if you want to track the full schedule (2 days). Note that enabling this may increase database size significantly.
        
    -   **Generated File Code**: Specify if you're using a custom file.
  
        ![Config flow](/images/config_flow.png)
        
4.  Select the channels you want to track from the dynamically fetched list.
    
5.  Complete the setup to create sensors for the selected channels.

### Custom files
open-epg.com allows the creation of custom EPG files with selected channels. To create a custom file:
1. Register for a free account at open-epg.com.
2. Select channels to include in your custom EPG file.
3. Once generated (updated daily), use the unique file ID (e.g., 122DjgdtAA), visible in the generated URL.

## Assist Integration

You can integrate the EPG information with Home Assistant's assist feature using the following automation. **Please note that this is a basic implementation example and can be considered a "hack" to expose EPG sensor data to the Assist conversation agent.** You are free to modify the `command` triggers, the `id` of the automation, and even use a different conversation `agent_id` if you have other agents configured.

To add this automation to your Home Assistant configuration, you can either:

1.  **Use the Automation UI:** Go to **Settings > Automations & Scenes**, click on the **+** button to create a new automation, and then click on the three dots in the top right corner to select "Edit in YAML". Paste the YAML code below and save.
2.  **Use configuration.yaml:** Add the automation directly to your `automations.yaml` file (or include it from your `configuration.yaml`).
```yaml
alias: TV Guide Information
description: Provides TV program information by querying EPG entities.
id: your_unique_automation_id
triggers:
  - trigger: conversation
    command:
      - what's on {channal}
      - what's on {channal} at {time}
      - what is playing on {channal}
      - what is the program on {channal}
      - tell me what's on {channal}
      - what is next on {channal}
      - what's playing next on {channal}
      - when is {program_title} on
      - when is {program_title} playing
      - what time is {program_title} on
      - is {program_title} on today
      - is {program_title} on tomorrow
conditions: []
actions:
  - action: conversation.process
    metadata: {}
    data:
      agent_id: conversation.google_generative_ai
      text: >-
        '{{trigger.user_input.text }}? answer based on following information: {%
        for entity in integration_entities("epg") %}{{ state_attr(entity,
        "friendly_name") }} : current: {{ states(entity) }} {{state_attr(entity,
        "today") }} {%- endfor %}'
    response_variable: result
  - set_conversation_response: "{{ result.response.speech.plain.speech }}"
mode: single
```

## Services

The following services are implemented by the component:
### Update Channels

**Service Name:** `epg.update_channels`

**Description:** Force update Guide file.

**Fields:**

| Name       | Description                         | Required | Selector Type |
|------------|-------------------------------------|----------|---------------|
| `entry_id` | The ID of the config_entry to update| true     | Config Entry (filtered by 'epg' integration) |

**Example Service Call:**
You can call this service from the Developer Tools -> Services menu in Home Assistant.

```yaml
service: epg.update_channels
data:
  entry_id: a9dcc3edcdd1e421c62ea735a9747cd6 # Replace with the actual ID of your EPG config entry
Search EPG Program Service
```

### Search EPG Program Service


**Service Name:** `Search EPG Program`

**Description:** Searches for a program title across configured EPG channels and returns matching schedules directly in the response.

**Fields:**

| Name          | Description                                                                  | Required | Example        | Selector Type |
|---------------|------------------------------------------------------------------------------|----------|----------------|---------------|
| `title`       | The program title (or part of it) to search for (case-insensitive).          | true     | "News at Ten"  | Text input    |
| `channel_name`| (Optional) Filter results to only this specific channel name (exact match, case-sensitive from guide data). | false    | "BBC One HD"   | Text input    |
| `date_filter` | (Optional) Filter results by date. 'any' includes 'today' and 'tomorrow'.  | false    | 'today'        | Select input  |

**Example Service Call:**

```yaml
service: epg.search_program
data:
  title: "Good Men"
  channel_name: "AMC - Canada HD"  #Optional
  date_filter: "today"  #Optional

```

**Example Service Response:**

The service will return a list of matching programs with their details.
```yaml
results:
  - channel_name: AMC - Canada HD
    title: A Few Good Men
    description: >-
      Navy lawyers (Tom Cruise, Demi Moore) defend two Marines accused of
      killing a private at the naval station at Guantanamo Bay, Cuba. Starring
      Tom Cruise, Jack Nicholson, Demi Moore.
    start_time: "14:30"
    end_time: "17:30"
    date: "2025-04-27"
    start_datetime_iso: "2025-04-27T14:30:00"


```

## Assist Integration

You can integrate the EPG information with Home Assistant's assist feature using the following automation. **Please note that this is a basic implementation example and can be considered a "hack" to expose EPG sensor data to the Assist conversation agent.** You are free to modify the `command` triggers, the `id` of the automation, and even use a different conversation `agent_id` if you have other agents configured.

To add this automation to your Home Assistant configuration, you can either:

1.  **Use the Automation UI:** Go to **Settings > Automations & Scenes**, click on the **+** button to create a new automation, and then click on the three dots in the top right corner to select "Edit in YAML". Paste the YAML code below and save.
2.  **Use configuration.yaml:** Add the automation directly to your `automations.yaml` file (or include it from your `configuration.yaml`).

## Displaying Television Programming in Lovelace
Recommended: For a more visually appealing and feature-rich display of your EPG data, it's highly recommended to use the [Lovelace EPG Card](https://github.com/yohaybn/lovelace-epg-card).  This custom card is specifically designed to work seamlessly with the HomeAssistant-EPG integration and provides a dynamic timeline view of your TV programming.
![lovlace card image](https://github.com/yohaybn/lovelace-epg-card/blob/main/images/screenshot.png))

Alternative (Basic Markdown Example):  If you prefer a simpler approach, you can use the following example to display today’s programming on a Lovelace card using Markdown:

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


## Reporting Issues

If you encounter any problems or need assistance, you can open an issue on the [GitHub repository](https://github.com/yohaybn/HomeAssistant-EPG/issues). To help us debug the issue, please enable debug logging for the integration and provide relevant logs:

### Enabling Debug Logging

1.  Enable debug in the UI or add the following to your `configuration.yaml` file:
    
    ```
    logger:
      default: warning
      logs:
        custom_components.epg: debug
    ```
    
2.  Restart Home Assistant to apply the changes.
    
3.  Reproduce the issue and check the logs in **Settings > System > Logs** or the `home-assistant.log` file in your configuration directory.
    

### Providing Logs

When opening an issue, include:

-   A detailed description of the problem.
    
-   Steps to reproduce the issue.
    
-   Relevant logs from Home Assistant with debug mode enabled for the integration.


### Donate
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/yohaybn)

If you find it helpful or interesting, consider supporting me by buying me a coffee or starring the project on GitHub! ☕⭐
Your support helps me improve and maintain this project while keeping me motivated. Thank you! ❤️


