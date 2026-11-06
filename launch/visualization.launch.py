"""Robot state publisher and optional RViz; no controllers or hardware startup."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from advrf_ros2_motors_controller.robot_config import load_robot


def setup(context):
    def value(name):
        return LaunchConfiguration(name).perform(context)
    def enabled(name):
        return value(name).lower() == 'true'
    namespace = '/' + value('namespace').strip('/')
    transport = value('ecat_namespace') or namespace.rstrip('/') + '/ecat'
    robot = load_robot(value('config_dir'), namespace, value('robot_description_file'),
                       value('control_mode'))
    actions = []
    if robot['description']:
        actions.append(Node(package='robot_state_publisher', executable='robot_state_publisher',
                            namespace=namespace, output='screen',
                            parameters=[{'robot_description': robot['description']}],
                            remappings=[
                                ('joint_states', transport.rstrip('/') + '/rx/joint_states'),
                                ('robot_description', '/robot_description'),
                            ]))
    if enabled('use_rviz'):
        rviz = value('rviz_config')
        if not robot['description']:
            raise ValueError('RViz robot visualization requires robot_description_file')
        actions.append(Node(package='rviz2', executable='rviz2', output='screen',
                            arguments=['-d', rviz] if rviz else [],
                            remappings=[('inputs/selected_joint', namespace.rstrip('/') + '/inputs/selected_joint')]))
    return actions


def generate_launch_description():
    defaults = {
        'config_dir': '', 'namespace': '/advrf/robot', 'ecat_namespace': '',
        'robot_description_file': 'auto', 'control_mode': '',
        'use_rviz': 'false', 'rviz_config': '',
    }
    descriptions = {
        'config_dir': 'Robot resource directory containing config/, urdf/ and rviz/',
        'namespace': 'Public robot namespace',
        'ecat_namespace': 'EtherCAT topic namespace; defaults to <namespace>/ecat',
        'robot_description_file': 'URDF/Xacro path, auto to find the model, or empty for no model',
        'control_mode': 'Motor profile name; empty uses the robot configuration',
        'use_rviz': 'Open RViz',
        'rviz_config': 'RViz configuration file; empty uses RViz defaults',
    }
    return LaunchDescription([DeclareLaunchArgument(k, default_value=v, description=descriptions[k]) for k, v in defaults.items()]
                             + [OpaqueFunction(function=setup)])
