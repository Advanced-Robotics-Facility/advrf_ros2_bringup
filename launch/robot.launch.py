"""Assemble the four explicit launch groups; robot packages supply resource paths."""
from pathlib import Path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    directory = Path(__file__).resolve().parent
    robot_arguments = ('robot_config', 'controller_config', 'controllers_config', 'namespace',
                       'robot_description_file', 'control_mode')

    def include(filename, names, condition=None):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(directory / filename)), condition=condition,
            launch_arguments={name: LaunchConfiguration(name) for name in names}.items())

    return LaunchDescription([
        DeclareLaunchArgument('robot_config', description='Explicit YAML file path'),
        DeclareLaunchArgument('controller_config', description='Explicit YAML file path'),
        DeclareLaunchArgument('controllers_config', description='Explicit YAML file path'),
        DeclareLaunchArgument('joint_control_config', default_value=''),
        DeclareLaunchArgument('bridge_config', default_value=str(directory.parent / 'config/advrf_bridge.yaml')),
        DeclareLaunchArgument('namespace', default_value='/advrf/robot'),
        DeclareLaunchArgument('robot_description_file', default_value='', description='URDF/Xacro file path; empty for no model'),
        DeclareLaunchArgument('control_mode', default_value='', description='Empty uses the robot motor profile'),
        DeclareLaunchArgument('use_panel', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('use_joy', default_value='false', choices=['true', 'false']),
        DeclareLaunchArgument('active_tx_on_first_msg', default_value='', choices=['', 'true', 'false']),
        DeclareLaunchArgument('start_bridge', default_value='false', choices=['true', 'false']),
        DeclareLaunchArgument('use_rviz', default_value='false', choices=['true', 'false']),
        DeclareLaunchArgument('rviz_config', default_value='', description='Empty uses RViz defaults'),
        include('controllers.launch.py', robot_arguments),
        include('inputs.launch.py', (*robot_arguments, 'joint_control_config', 'use_panel', 'use_joy')),
        include('hardware.launch.py', ('bridge_config', 'namespace', 'active_tx_on_first_msg'),
                IfCondition(LaunchConfiguration('start_bridge'))),
        include('visualization.launch.py', ('namespace', 'robot_description_file',
                                            'use_rviz', 'rviz_config')),
    ])
