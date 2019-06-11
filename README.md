# DIAL Demo
This is a simple demo for the DIAL Protocol v2.2 written in Python based on the specifications detailed [here](https://docs.google.com/viewer?a=v&pid=sites&srcid=ZGlhbC1tdWx0aXNjcmVlbi5vcmd8ZGlhbHxneDoxOWFiYWMxMDQ4YmI4MWE2).

## Setup
- Install any dependencies via `pip`
- Turn on any DIAL-enabled devices (i.e. TVs that support DIAL).
- Run `python3 DIALDemo.py`  
  - After running DIAL Service Discovery once, you may have a default DIAL server you would like to play around with. You can replace the URL by changing the variable `defaultDialRestSeviceUrl` in `dialDemo.py`.

## DIAL concepts not covered by the Demo
- Installing an app after querying for app info
- Sending additional data from first-screen app to a DIAL server
- Hiding an app
- DIAL Wake-up
- Force Low Power Mode