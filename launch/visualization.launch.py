"""Robot state publisher and optional RViz; no controllers or hardware startup."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from advrf_ros2_bringup.robot_config import robot_description


def setup(context):
    def value(name):
        return LaunchConfiguration(name).perform(context)
    def enabled(name):
        return value(name).lower() == 'true'
    namespace = '/' + value('namespace').strip('/')
    transport = namespace.rstrip('/') + '/ecat'
    description = robot_description(value('robot_description_file'))
    actions = []
    if description:
        actions.append(Node(package='robot_state_publisher', executable='robot_state_publisher',
                            namespace=namespace, output='screen',
                            parameters=[{'robot_description': description}],
                            remappings=[
                                ('joint_states', transport.rstrip('/') + '/rx/joint_states'),
                                ('robot_description', '/robot_description'),
                            ]))
    if enabled('use_rviz'):
        rviz = value('rviz_config')
        if not description:
            raise ValueError('RViz robot visualization requires robot_description_file')
        actions.append(Node(package='rviz2', executable='rviz2', output='screen',
                            arguments=['-d', rviz] if rviz else [],
                            remappings=[('inputs/selected_joint', namespace.rstrip('/') + '/inputs/selected_joint')]))
    return actions


def generate_launch_description():
    defaults = {
        'namespace': '/advrf/robot',
        'robot_description_file': '',
        'use_rviz': 'false', 'rviz_config': '',
    }
    descriptions = {
        'namespace': 'Public robot namespace',
        'robot_description_file': 'URDF/Xacro file path; empty for no model',
        'use_rviz': 'Open RViz',
        'rviz_config': 'RViz configuration file; empty uses RViz defaults',
    }
    return LaunchDescription([DeclareLaunchArgument(k, default_value=v, description=descriptions[k]) for k, v in defaults.items()]
                             + [OpaqueFunction(function=setup)])
