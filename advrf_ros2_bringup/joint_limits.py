"""Validate joint configuration independently of launch composition."""
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import yaml


class UniqueLoader(yaml.SafeLoader):
    """Reject accidental duplicate IDs/settings instead of silently keeping the last."""

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        result = {}

        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)

            if key in result:
                raise ValueError(f'Duplicate YAML key: {key}')

            result[key] = self.construct_object(value_node, deep=deep)

        return result


def read_yaml(path):
    with Path(path).open() as stream:
        value = yaml.load(stream, Loader=UniqueLoader)

    if not isinstance(value, dict):
        raise ValueError(f'{path}: expected a mapping')

    return value


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label}: expected a finite number')

    return float(value)


def urdf_limits(description):
    """Return physical limits in URDF joint order."""

    if not description:
        return {}

    return {joint.get('name'): {key: float(value) for key, value in limit.attrib.items()}
            for joint in ET.fromstring(description).findall('joint')
            if joint.get('type') != 'fixed' and (limit := joint.find('limit')) is not None}


def limits_from_entries(entries, joints, description=''):
    physical = urdf_limits(description)
    result = {'joints': joints}

    for key in ('position_lower', 'position_upper', 'max_velocity', 'max_acceleration'):
        result[key] = []

    for name in joints:
        if description and name not in physical:
            raise ValueError(f'{name}: controlled joint missing from URDF limits')

        entry = entries.get(name)

        if not isinstance(entry, dict):
            raise ValueError(f'{name}: missing MoveIt limits')

        base = physical.get(name, {})
        values = [entry.get('min_position', base.get('lower')),
                  entry.get('max_position', base.get('upper')),
                  entry.get('max_velocity', base.get('velocity')),
                  entry.get('max_acceleration')]
        lo, hi, vel, acc = [number(v, f'{name} limits') for v in values]

        if any(entry.get(flag) is False for flag in
               ('has_position_limits', 'has_velocity_limits', 'has_acceleration_limits')):
            raise ValueError(f'{name}: finite enabled limits are required by ADVRF')

        if (lo > hi or vel <= 0 or acc <= 0 or
                lo < base.get('lower', lo) or hi > base.get('upper', hi) or
                vel > base.get('velocity', vel)):
            raise ValueError(f'{name}: invalid limits or limits exceed URDF')

        for key, value in zip(list(result)[1:], (lo, hi, vel, acc)):
            result[key].append(value)

    return result
