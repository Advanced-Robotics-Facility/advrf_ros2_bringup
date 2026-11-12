"""Start only the EtherCAT bridge; the master/backend is managed separately."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


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
    return [Node(package='advrf_ros2_ecat', executable='bridge_ecat_client_node',
                 namespace=transport, output='screen', parameters=parameters)]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('bridge_config', description='ROS bridge parameter YAML file'),
        DeclareLaunchArgument('active_tx_on_first_msg', default_value='', choices=['', 'true', 'false'],
                              description='Override the bridge automatic TX activation parameter'),
        DeclareLaunchArgument('namespace', default_value='/advrf/robot'),
        OpaqueFunction(function=setup),
    ])
