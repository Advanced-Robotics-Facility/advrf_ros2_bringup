"""Start only the EtherCAT bridge; the master/backend is managed separately."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from pathlib import Path


def setup(context):
    config = Path(LaunchConfiguration('config_dir').perform(context)) / 'config/advrf_bridge.yaml'
    namespace = LaunchConfiguration('namespace').perform(context)
    transport = LaunchConfiguration('ecat_namespace').perform(context) or namespace.rstrip('/') + '/ecat'
    parameters = [str(config)]
    automatic = LaunchConfiguration('active_tx_on_first_msg', default='').perform(context)
    if automatic:
        if automatic not in ('true', 'false'):
            raise ValueError('active_tx_on_first_msg must be true or false')
        parameters.append({'active_tx_on_first_msg': automatic == 'true'})
    return [Node(package='advrf_ros2_ecat', executable='bridge_ecat_client_node',
                 namespace=transport, output='screen', parameters=parameters)]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('config_dir', description='Robot resource directory containing config/advrf_bridge.yaml'),
        DeclareLaunchArgument('active_tx_on_first_msg', default_value='', choices=['', 'true', 'false'],
                              description='Override the bridge automatic TX activation parameter'),
        DeclareLaunchArgument('namespace', default_value='/advrf/robot'),
        DeclareLaunchArgument('ecat_namespace', default_value=''),
        OpaqueFunction(function=setup),
    ])
