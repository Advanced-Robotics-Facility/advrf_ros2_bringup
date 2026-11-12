"""Load robot configuration from explicit ROS resource paths."""
from pathlib import Path

from .joint_limits import read_yaml, number


# ROS names are relative to the selected namespace unless they start with / or ~.
COMMAND_CONTROLLER_CONFIG = 'joint_command_controller_node'
TRAJECTORY_CONTROLLER_CONFIG = 'joint_trajectory_controller_node'
GO_TO_CONFIG = 'joint_go_to_node'
DEFAULT_ACTION_NAMESPACE = 'follow_joint_trajectory'

MODES = {'position', 'velocity', 'impedance', 'torque', 'current'}


def node_parameters(path, node, namespace=''):
    document = read_yaml(path)
    result = {}
    full = '/' + '/'.join(filter(None, [namespace.strip('/'), node]))

    for key in ('/**', f'/**/{node}', node, full):
        result.update(document.get(key, {}).get('ros__parameters', {}))

    return result


def robot_description(path):
    if not path:
        return ''

    path = Path(path).expanduser().resolve(strict=True)

    if path.suffix == '.xacro':
        import xacro
        return xacro.process_file(str(path)).toxml()

    return path.read_text()


def load_robot(config_dir, namespace, urdf='', control_mode=''):
    root = Path(config_dir).expanduser().resolve(strict=True)
    config = root / 'config'

    if (config / 'controller.yaml').is_file():
        document = {}
        controller = read_yaml(config / 'controller.yaml')['controller']
        name = controller['name']
    else:
        document = read_yaml(config / 'moveit_controllers.yaml')
        manager = document['moveit_simple_controller_manager']
        names = manager['controller_names']

        if len(names) != 1:
            raise ValueError(
                'ADVRF currently requires one shared FollowJointTrajectory controller'
            )

        name = names[0]
        controller = manager[name]

    joints = controller['joints']

    if (controller.get('type', 'FollowJointTrajectory') != 'FollowJointTrajectory' or not isinstance(joints, list)
            or not joints or any(not isinstance(j, str) or not j for j in joints)
            or len(set(joints)) != len(joints)):
        raise ValueError(
            'Expected FollowJointTrajectory with unique nonempty joint names'
        )

    action = controller.get('action_ns', DEFAULT_ACTION_NAMESPACE)

    if not isinstance(action, str) or not action.strip('/'):
        raise ValueError('Invalid trajectory action namespace')

    prefix = namespace.rstrip('/')
    full_controller = name if name.startswith('/') else prefix + '/' + name
    full_action = full_controller.rstrip('/') + '/' + action.strip('/')

    if urdf == 'auto':
        candidates = sorted((root / 'urdf').glob('*.urdf'))
        candidates = [p for p in candidates if '.' not in p.stem]

        if len(candidates) > 1:
            raise ValueError(
                'Multiple URDF files; pass robot_description_file explicitly'
            )

        urdf = str(candidates[0]) if candidates else ''

    description = robot_description(urdf)
    from .central_config import load_central, adapt_central

    configuration_file = config / 'robot_config.yaml'
    central = load_central(configuration_file)
    adapted = adapt_central(central, joints, description)
    limits = adapted['limits']
    hardware = adapted['hardware']

    mapping = hardware['joint_map']

    if (not isinstance(mapping, dict) or any(type(i) is not int or not 0 <= i <= 2147483647
                                           for i in mapping)
            or any(not isinstance(n, str) or not n for n in mapping.values())
            or len(set(mapping.values())) != len(mapping)):
        raise ValueError(
            'joint_map must map unique nonnegative int32 IDs to unique joint names'
        )

    reverse = {name: i for i, name in mapping.items()}

    try:
        ids = [reverse[j] for j in joints]
    except KeyError as error:
        raise ValueError(f'Missing hardware mapping: {error}') from error

    settings = config / 'advrf_controllers.yaml'
    nodes = {
        node: node_parameters(settings, node, namespace)
        for node in (
            COMMAND_CONTROLLER_CONFIG,
            TRAJECTORY_CONTROLLER_CONFIG,
            GO_TO_CONFIG,
        )
    }

    mode = control_mode or central.get('control_mode', 'position')

    if mode not in MODES or mode not in hardware.get('profiles', {}):
        raise ValueError(f'No configured profile for control mode {mode}')

    selected = []

    for joint in joints:
        values = hardware['profiles'][mode].get(joint, {}).get('gains')

        if not isinstance(values, list) or len(values) != 5:
            raise ValueError(f'{mode}/{joint}: expected five gains')

        values = [number(v, f'{mode}/{joint} gains') for v in values]

        if any(abs(v) > 3.402823466e38 for v in values):
            raise ValueError(f'{mode}/{joint}: gains exceed float32 range')

        selected.extend(values)

    command = selected[:]
    # Preserve the existing native bridge position/velocity wire permutation.

    if mode in ('position', 'velocity'):
        command = []

        for i in range(0, len(selected), 5):
            kp, ki, kd, unused3, unused4 = selected[i:i + 5]

            if unused3 != 0 or unused4 != 0:
                raise ValueError(
                    f'{mode}: native position/velocity profile slots 4/5 must be zero'
                )

            command.extend([kp, kd, 0.0, 0.0, ki])

    for node, values in nodes.items():
        for key, expected in limits.items():
            if key in values and values[key] != expected:
                raise ValueError(
                    f'{node}: {key} must come from the shared joint limits'
                )

        values.update(limits)

        if 'action_name' in values and values['action_name'] != full_action:
            raise ValueError(f'{node}: action_name must match moveit_controllers.yaml')

    nodes[COMMAND_CONTROLLER_CONFIG].update(motor_ids=ids, joint_gains=command)
    # Converter currently receives the selected gains; drive mode is set by START.
    nodes[COMMAND_CONTROLLER_CONFIG]['control_mode'] = mode
    nodes[TRAJECTORY_CONTROLLER_CONFIG]['action_name'] = full_action
    nodes[GO_TO_CONFIG]['action_name'] = full_action

    adapted['parameters']['control_mode'] = mode

    return {
        'root': root,
        'nodes': nodes,
        'limits': limits,
        'description': description,
        'moveit': document,
        'action_name': full_action,
        'control_mode': mode,
        'configuration_parameters': adapted['parameters'],
        'configuration_file': str(configuration_file),
        'moveit_limits': adapted['moveit_limits'],
    }
