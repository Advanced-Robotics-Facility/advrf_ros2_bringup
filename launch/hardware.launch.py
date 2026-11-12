"""Start only the EtherCAT bridge; the master/backend is managed separately."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnShutdown
from advrf_ros2_bringup.ec_config_override import prepare_motor_override
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from advrf_ros2_bringup.robot_config import node_parameters


def setup(context):
    config = LaunchConfiguration('bridge_config').perform(context)
    namespace = LaunchConfiguration('namespace').perform(context)
    transport = namespace.rstrip('/') + '/ecat'
    parameters = [str(config)]
    automatic = LaunchConfiguration('active_tx_on_first_msg', default='').perform(context)
    if automatic:
        if automatic not in ('true', 'false'):
            raise ValueError('active_tx_on_first_msg must be true or false')
        parameters.append({'active_tx_on_first_msg': automatic == 'true'})
    options = {}
    cleanup = []
    motor_config = LaunchConfiguration('motor_start_config', default='').perform(context)
    control_mode = LaunchConfiguration('control_mode', default='').perform(context)

    if control_mode and motor_config:
        raise ValueError('Choose control_mode or motor_start_config, not both')

    if control_mode:
        profiles = node_parameters(config, 'bridge_ecat_client_node', transport).get(
            'motor_start_profiles', {}
        )

        if not isinstance(profiles, dict) or control_mode not in profiles:
            raise ValueError(f'No motor_start_profiles entry for control_mode {control_mode!r} in {config}')

        motor_config = profiles[control_mode]

        if not isinstance(motor_config, str) or not motor_config.strip():
            raise ValueError(f'Invalid motor profile path for control_mode {control_mode!r}')

    if motor_config:
        ec_cfg = context.environment.get('EC_CFG', '')
        if not ec_cfg:
            raise ValueError('motor_start_config requires EC_CFG in the environment')
        directory, target = prepare_motor_override(ec_cfg, motor_config, context.environment)
        options['additional_env'] = {'EC_CFG': target}

        def release_directory(context):
            directory.cleanup()
            return []

        cleanup = [RegisterEventHandler(OnShutdown(
            on_shutdown=[OpaqueFunction(function=release_directory)]))]
    return cleanup + [Node(package='advrf_ros2_ecat', executable='bridge_ecat_client_node',
                 namespace=transport, output='screen', parameters=parameters, **options)]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('bridge_config', description='ROS bridge parameter YAML file'),
        DeclareLaunchArgument('active_tx_on_first_msg', default_value='', choices=['', 'true', 'false'],
                              description='Override the bridge automatic TX activation parameter'),
        DeclareLaunchArgument('control_mode', default_value='',
                              description='Hardware startup mode from bridge_config motor_start_profiles'),
        DeclareLaunchArgument('motor_start_config', default_value='',
                              description='Motor profile YAML; relative to EC_CFG robot control YAML'),
        DeclareLaunchArgument('namespace', default_value='/advrf/robot'),
        OpaqueFunction(function=setup),
    ])
