"""Operator interfaces: panel and joystick share the joint command interface."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from advrf_ros2_bringup.robot_config import load_robot, node_parameters


def setup(context):
    def arg(name):
        return LaunchConfiguration(name).perform(context)

    namespace = arg('namespace')
    transport = namespace.rstrip('/') + '/ecat'
    actions = []
    if arg('use_panel') == 'true':
        actions.append(ExecuteProcess(cmd=[
            'ros2', 'run', 'rqt_gui', 'rqt_gui', '--force-discover', '--standalone',
            'advrf_ros2_motors_controller.motor_panel.MotorPanel', '--args',
            '--parameter-node', namespace.rstrip('/') + '/joint_goal_manager_node',
            '--namespace', namespace,
        ], output='screen'))
    if arg('use_joy') == 'true':
        robot = load_robot(arg('robot_config'), namespace, arg('robot_description_file'), arg('control_mode'),
                           controller_config=arg('controller_config'),
                           controllers_config=arg('controllers_config'))
        config = arg('joint_control_config')
        manual = node_parameters(config, 'joint_control_node', namespace)
        manual.update(node_parameters(config, 'manual_joint_controller_node', namespace))
        joystick = node_parameters(config, 'joy_control_node', namespace)
        joystick.update(node_parameters(config, 'joystick_input_node', namespace))
        limits = robot['limits']
        joints = manual.get('joints', limits['joints'])
        if (not isinstance(joints, list) or not joints or
                any(joint not in limits['joints'] for joint in joints) or
                len(set(joints)) != len(joints)):
            raise ValueError('joint_control.yaml: joints must be unique configured robot joints')
        indices = [limits['joints'].index(joint) for joint in joints]
        manual.update(joints=joints,
                      lower_positions=[limits['position_lower'][i] for i in indices],
                      upper_positions=[limits['position_upper'][i] for i in indices])
        actions.extend([
            Node(package='joy', executable='joy_node', namespace=namespace, output='screen',
                 parameters=[node_parameters(config, 'joy_node', namespace)]),
            Node(package='advrf_ros2_io', executable='joystick_input_node',
                 namespace=namespace, output='screen',
                 parameters=[joystick],
                 remappings=[('ecat/set_active_tx', transport.rstrip('/') + '/set_active_tx'),
                             ('ecat/active', transport.rstrip('/') + '/active')]),
            Node(package='advrf_ros2_io', executable='manual_joint_controller_node',
                 namespace=namespace, output='screen', parameters=[manual],
                 remappings=[
                     ('rx/joint_states', transport.rstrip('/') + '/rx/joint_states'),
                     ('joint_commands', namespace.rstrip('/') + '/controllers/joint_commands'),
                     ('selected_joint', namespace.rstrip('/') + '/inputs/selected_joint'),
                 ]),
        ])
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('robot_config', default_value='', description='Explicit YAML file path'),
        DeclareLaunchArgument('controller_config', default_value='', description='Explicit YAML file path'),
        DeclareLaunchArgument('controllers_config', default_value='', description='Explicit YAML file path'),
        DeclareLaunchArgument('joint_control_config', default_value='', description='Explicit YAML file path'),
        DeclareLaunchArgument('namespace', default_value='/advrf/robot'),
        DeclareLaunchArgument('robot_description_file', default_value=''),
        DeclareLaunchArgument('control_mode', default_value=''),
        DeclareLaunchArgument('use_panel', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('use_joy', default_value='false', choices=['true', 'false']),
        OpaqueFunction(function=setup),
    ])
