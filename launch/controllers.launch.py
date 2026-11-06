"""Controller nodes and their public connections.

joint_commands / trajectory -> converter -> EtherCAT TX
EtherCAT RX -> trajectory controller and GoTo
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from advrf_ros2_motors_controller.robot_config import load_robot


def setup(context):
    def arg(name):
        return LaunchConfiguration(name).perform(context)

    namespace = arg('namespace')
    transport = arg('ecat_namespace') or namespace.rstrip('/') + '/ecat'
    robot = load_robot(arg('config_dir'), namespace, arg('robot_description_file'), arg('control_mode'))
    # All public connections are visible here; no node creation in a helper library.
    robot_prefix = namespace.rstrip('/')
    ecat_prefix = transport.rstrip('/')
    remappings = [
        ('rx/joint_states', ecat_prefix + '/rx/joint_states'),
        ('rx/motors', ecat_prefix + '/rx/motors'),
        ('tx/motors', ecat_prefix + '/tx/motors'),
        ('joint_commands', robot_prefix + '/controllers/joint_commands'),
        ('set_trajectory_enabled', robot_prefix + '/set_trajectory_enabled'),
        ('go_to_joint_positions', robot_prefix + '/go_to_joint_positions'),
        ('advrf_motors_controller/follow_joint_trajectory',
         robot_prefix + '/advrf_motors_controller/follow_joint_trajectory'),
    ]
    actions = [
        Node(package='advrf_ros2_motors_controller', executable='converter_tx_motor_node',
             namespace=namespace, output='screen', remappings=remappings,
             parameters=[robot['nodes']['joint_command_controller_node']]),
        Node(package='advrf_ros2_motors_controller', executable='joint_trajectory_controller_node',
             namespace=namespace, output='screen', remappings=remappings,
             parameters=[robot['nodes']['joint_trajectory_controller_node']]),
        Node(package='advrf_ros2_motors_controller', executable='joint_goal_manager_node',
             namespace=namespace, output='screen', remappings=remappings,
             parameters=[robot['nodes']['joint_go_to_node']]),
    ]
    if robot['configuration_parameters'] is not None:
        actions.append(Node(package='advrf_ros2_motors_controller', executable='robot_config_node',
                            namespace=namespace, output='screen', parameters=[{
                                **robot['configuration_parameters'],
                                'configuration_file': robot['configuration_file'],
                                'robot_description': robot['description'],
                            }]))
    return actions


def generate_launch_description():
    defaults = {
        'config_dir': '', 'namespace': '/advrf/robot', 'ecat_namespace': '',
        'robot_description_file': 'auto', 'control_mode': '',
    }
    descriptions = {
        'config_dir': 'Robot resource directory containing config/, urdf/ and rviz/',
        'namespace': 'Public robot namespace',
        'ecat_namespace': 'EtherCAT topic namespace; defaults to <namespace>/ecat',
        'robot_description_file': 'URDF/Xacro path, auto to find the model, or empty for no model',
        'control_mode': 'Motor profile name; empty uses the robot configuration',
    }
    return LaunchDescription([
        *[DeclareLaunchArgument(name, default_value=value, description=descriptions[name]) for name, value in defaults.items()],
        OpaqueFunction(function=setup),
    ])
