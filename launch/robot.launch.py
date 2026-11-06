"""Assemble the four explicit launch groups; robot packages supply resource paths."""
from pathlib import Path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    directory = Path(__file__).resolve().parent
    robot_arguments = ('config_dir', 'namespace', 'ecat_namespace',
                       'robot_description_file', 'control_mode')

    def include(filename, names, condition=None):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(directory / filename)), condition=condition,
            launch_arguments={name: LaunchConfiguration(name) for name in names}.items())

    return LaunchDescription([
        DeclareLaunchArgument('config_dir', description='Robot resource directory containing config/, urdf/ and rviz/'),
        DeclareLaunchArgument('namespace', default_value='/advrf/robot'),
        DeclareLaunchArgument('ecat_namespace', default_value='', description='Default: <namespace>/ecat'),
        DeclareLaunchArgument('robot_description_file', default_value='auto', description='URDF/Xacro path, auto, or empty for no model'),
        DeclareLaunchArgument('control_mode', default_value='', description='Empty uses the robot motor profile'),
        DeclareLaunchArgument('use_panel', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('use_joy', default_value='false', choices=['true', 'false']),
        DeclareLaunchArgument('active_tx_on_first_msg', default_value='', choices=['', 'true', 'false']),
        DeclareLaunchArgument('start_bridge', default_value='false', choices=['true', 'false']),
        DeclareLaunchArgument('use_rviz', default_value='false', choices=['true', 'false']),
        DeclareLaunchArgument('rviz_config', default_value='', description='Empty uses RViz defaults'),
        include('controllers.launch.py', robot_arguments),
        include('inputs.launch.py', (*robot_arguments, 'use_panel', 'use_joy')),
        include('hardware.launch.py', ('config_dir', 'namespace', 'ecat_namespace', 'active_tx_on_first_msg'),
                IfCondition(LaunchConfiguration('start_bridge'))),
        include('visualization.launch.py', (*robot_arguments, 'use_rviz', 'rviz_config')),
    ])
