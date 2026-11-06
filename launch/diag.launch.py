"""Aggregate EtherCAT diagnostics and optionally open the robot monitor."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('use_monitor', default_value='true', choices=['true', 'false'],
                              description='Open rqt_robot_monitor'),
        DeclareLaunchArgument('diagnostics_config', default_value=PathJoinSubstitution([
            FindPackageShare('advrf_ros2_ecat'), 'config', 'diagnostics.yaml']),
            description='Diagnostic aggregator configuration'),
        Node(package='diagnostic_aggregator', executable='aggregator_node',
             name='diagnostic_aggregator', namespace='/', output='screen',
             parameters=[LaunchConfiguration('diagnostics_config')]),
        Node(package='rqt_robot_monitor', executable='rqt_robot_monitor',
             namespace='/', output='screen',
             condition=IfCondition(LaunchConfiguration('use_monitor'))),
    ])
