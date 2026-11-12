"""Prepare a process-local EC_CFG override without modifying source files."""
from pathlib import Path
import re
import tempfile

import yaml


def resolve_path(value, parent, environment):
    """Resolve client paths using the containing YAML directory as PWD."""
    variables = dict(environment, PWD=str(parent))

    def expand(match):
        name = match.group(1) or match.group(2)
        if name not in variables:
            raise ValueError(f'Undefined environment variable in client path: {name}')
        return variables[name]

    expanded = re.sub(r'\$\{([A-Za-z_][A-Za-z_0-9]*)\}|\$([A-Za-z_][A-Za-z_0-9]*)', expand, str(value))
    path = Path(expanded)
    return (parent / path).resolve() if not path.is_absolute() else path.resolve()


def prepare_motor_override(ec_cfg, motor_config, environment):
    """Return (temporary directory owner, EC_CFG path); caller owns cleanup.

    Relative motor_config paths are relative to the original robot control YAML.
    All existing *_path references are anchored before relocating the documents.
    """
    source = Path(ec_cfg).resolve()
    config = yaml.safe_load(source.read_text())
    robot = config['robot']
    for key, value in robot.items():
        if key.endswith('_path'):
            robot[key] = str(resolve_path(value, source.parent, environment))
    control_source = Path(robot['robot_control_path'])
    control = yaml.safe_load(control_source.read_text())
    for section in control.values():
        if isinstance(section, dict) and 'config_path' in section:
            section['config_path'] = str(resolve_path(section['config_path'], control_source.parent, environment))
    profile = resolve_path(motor_config, control_source.parent, environment)
    profile_document = yaml.safe_load(profile.read_text())
    if not isinstance(profile_document, dict) or not any(
            isinstance(device, dict) and 'control_mode' in device
            for device in profile_document.values()):
        raise ValueError(f'Invalid motor configuration: {profile}')
    control['motor']['config_path'] = str(profile)
    directory = tempfile.TemporaryDirectory(prefix='advrf_ec_cfg_')
    try:
        root = Path(directory.name)
        robot['robot_control_path'] = str(root / 'robot_control.yaml')
        (root / 'robot_control.yaml').write_text(yaml.safe_dump(control, sort_keys=False))
        target = root / 'ec_cfg.yaml'
        target.write_text(yaml.safe_dump(config, sort_keys=False))
    except Exception:
        directory.cleanup()
        raise
    return directory, str(target)
