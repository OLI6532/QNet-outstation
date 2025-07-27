import subprocess


def disable_power_save() -> str:
    """
    Attempts to disable wlan0 power management to prevent sleeping.
    This is not applicable to QPro models that use ethernet as their connection method.
    :return The output of the command.
    :raises subprocess.CalledProcessError: If the command fails.
    """
    result = subprocess.run(
        ["iw", "wlan0", "set", "power_save", "off"],
        capture_output=True,
        text=True,
        check=True
    )

    return result.stdout