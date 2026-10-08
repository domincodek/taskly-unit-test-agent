import os

SECRET_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "KEY", "CREDENTIAL")


def child_env(updates: dict[str, str] | None = None) -> dict[str, str]:
    env = {}
    for name, value in os.environ.items():
        if any(marker in name.upper() for marker in SECRET_MARKERS):
            continue
        env[name] = value
    if updates:
        env.update(updates)
    return env
