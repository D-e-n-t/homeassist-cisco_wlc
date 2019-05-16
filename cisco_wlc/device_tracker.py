
"""Support for Cisco Aeronet Wireless Controllers."""
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.device_tracker import (
    DOMAIN, PLATFORM_SCHEMA, DeviceScanner)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, \
    CONF_PORT

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.All(
    PLATFORM_SCHEMA.extend({
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Optional(CONF_PASSWORD, default=''): cv.string,
        vol.Optional(CONF_PORT): cv.port,
    })
)


def get_scanner(hass, config):
    """Validate the configuration and return a Cisco scanner."""
    scanner = CiscoWLCScanner(config[DOMAIN])

    return scanner if scanner.success_init else None


class CiscoWLCScanner(DeviceScanner):
    """This class queries a wireless controller running Cisco Aironet firmware (not IOS XE)."""

    def __init__(self, config):
        """Initialize the scanner."""
        self.host = config[CONF_HOST]
        self.username = config[CONF_USERNAME]
        self.port = config.get(CONF_PORT)
        self.password = config.get(CONF_PASSWORD)

        self.last_results = {}

        self.success_init = self._update_info()
        _LOGGER.info('cisco_wlc scanner initialized')

    def get_device_name(self, device):
        """Get the firmware doesn't save the name of the wireless device."""
        return None

    def scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        self._update_info()

        return self.last_results

    def _update_info(self):
        """
        Ensure the information from the Cisco WLC is up to date.
        Returns boolean if scanning successful.
        """
        string_result = self._get_client_data()

        if string_result:
            self.last_results = []
            last_results = []

            lines_result = string_result.splitlines()

            # Remove the first eight lines, as they contains the show client command
            # and spacing/headers/etc. 
            # show client summary
            # MAC Address       AP Name                        Slot Status        WLAN  Auth Protocol         Port Wired Tunnel  Role
            lines_result = lines_result[8:]

            for line in lines_result:
                parts = line.split()
                if len(parts) != 12:
                    _LOGGER.info('cisco_wlc: wrong number of parts in line: %s',line)
                    continue

                # MAC AP_Name Radio_Slot Client_Status WLAN_ID Authenticated
                # Wireless_Protocol Port Wired Tunnel WLC_Role
                # ['00:00:00:00:00:00', 'AP Name', '0', 'Associated', '4',
                # 'Yes', '802.11n(2.4 GHz)', '13', 'No', 'No', 'Local']
                status = parts[3]
                hw_addr = parts[0]

                if status == "Associated":
                    last_results.append(hw_addr)

            self.last_results = last_results
            return True

        return False

    def _get_client_data(self):
        """Open connection to the WLC and get arp entries."""
        from pexpect import pxssh
        import re

        try:
            cisco_ssh = pxssh.pxssh()
            cisco_ssh.login(self.host, self.username, self.password,
                            port=self.port, auto_prompt_reset=False)

            # WLCs are strange - the initial SSH connection does not authentication
            cisco_ssh.PROMPT = "User: "
            cisco_ssh.sendline(self.username)
            cisco_ssh.PROMPT = "Password:"
            cisco_ssh.sendline(self.password)
            # Find the hostname
            #initial_line = cisco_ssh.before.decode('utf-8').splitlines()
            #router_hostname = initial_line[len(initial_line) - 1]
            #router_hostname += ">"
            # Set the discovered hostname as prompt
            #regex_expression = ('(?i)^%s' % router_hostname).encode()
            #cisco_ssh.PROMPT = re.compile(regex_expression, re.MULTILINE)
            cisco_ssh.PROMPT = "(Cisco Controller) >"
            # Allow full arp table to print at once
            cisco_ssh.sendline("config paging disable")
            cisco_ssh.prompt(1)

            cisco_ssh.sendline("show client summary")
            cisco_ssh.prompt(1)

            devices_result = cisco_ssh.before

            return devices_result.decode('utf-8')
        except pxssh.ExceptionPxssh as px_e:
            _LOGGER.error("pxssh failed on login")
            _LOGGER.error(px_e)

        return None
