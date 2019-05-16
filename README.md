# cisco_wlc
Device Tracker platform for Home Assist


This project takes the cisco_ios device_tracker for home-assistant and make it work with a Cisco WLC.

It's very straight-foward and worked on the first try.

It's entirely based on the work of @fbradyirl from the home-assistant project.

It requires the following in your configuration.yaml file:

```
device_tracker:
  - platform: cisco_wlc
    host: <IP of WLC>
    username: <username>
    password: <password>
    interval_seconds: 60
```
  
The default interval of 12 seconds is too fast.  60 seconds seems to work.

To install, just move the cisco_wlc directory into /config/custom_components/.

