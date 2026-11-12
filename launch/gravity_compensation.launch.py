"""Start gravity compensation using the robot's configured impedance gains."""
import math

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from advrf_ros2_bringup.robot_config import load_robot, node_parameters
from advrf_ros2_motors_controller.ros_names import (
    resolve_ecat_namespace,
    resolve_namespace,
)

PACKAGE_NAME = 'advrf_ros2_gravity_compensation'
EXECUTABLE_NAME = 'advrf_ros2_gravity_compensation'
NODE_NAME = 'gravity_compensation'
CONTROL_MODE = 'impedance'
CONTROLLER_CONFIG = 'joint_command_controller_node'
JOINT_FEEDBACK_TOPIC = 'rx/joint_states'
MOTOR_COMMAND_TOPIC = 'tx/motors'
GAINS_PER_JOINT = 5
DEFAULT_GAIN_RAMP_DURATION = '3.0'

def setup(context):
    def argument(name):
        return LaunchConfiguration(name).perform(context)

    namespace = resolve_namespace(argument('namespace'))
    transport_namespace = resolve_ecat_namespace(namespace)

    gain_ramp_duration = float(argument('gain_ramp_duration'))

    if not math.isfinite(gain_ramp_duration) or gain_ramp_duration <= 0:
        raise ValueError('gain_ramp_duration must be finite and positive')

    robot = load_robot(
        argument('robot_config'),
        namespace,
        argument('robot_description_file'),
        CONTROL_MODE,
        controller_config=argument('controller_config'),
        controllers_config=argument('controllers_config'),
    )

    if not robot['description']:
        raise ValueError('Gravity compensation requires a robot URDF/Xacro')

    configured_joints = robot['limits']['joints']
    configuration_file = argument('gravity_config')
    if configuration_file:
        settings = node_parameters(configuration_file, NODE_NAME, namespace)
        if 'joints' not in settings:
            raise ValueError('gravity_config must define gravity_compensation ros__parameters.joints')
        joints = settings['joints']
        if (not isinstance(joints, list) or not joints
                or any(not isinstance(name, str) or not name.strip() for name in joints)):
            raise ValueError('gravity_config joints must be a nonempty list of joint names')
    else:
        joints = configured_joints

    if (
        len(joints) != len(set(joints))
        or any(name not in configured_joints for name in joints)
    ):
        raise ValueError('gravity_config joints must be unique joints from robot_config.yaml')

    controller = robot['nodes'][CONTROLLER_CONFIG]
    indices = [configured_joints.index(name) for name in joints]
    motor_ids = [controller['motor_ids'][index] for index in indices]
    joint_gains = [
        gain
        for index in indices
        for gain in controller['joint_gains'][
            GAINS_PER_JOINT * index:GAINS_PER_JOINT * (index + 1)
        ]
    ]

    return [
        Node(
            package=PACKAGE_NAME,
            executable=EXECUTABLE_NAME,
            name=NODE_NAME,
            namespace=namespace,
            output='screen',
            parameters=[{
                'robot_description': robot['description'],
                'joints': joints,
                'motor_ids': motor_ids,
                'joint_gains': joint_gains,
                'gain_ramp_duration': gain_ramp_duration,
            }],
            remappings=[
                (JOINT_FEEDBACK_TOPIC, transport_namespace.rstrip('/') + '/' + JOINT_FEEDBACK_TOPIC),
                (MOTOR_COMMAND_TOPIC, transport_namespace.rstrip('/') + '/' + MOTOR_COMMAND_TOPIC),
            ],
        ),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('robot_config', description='Explicit YAML file path'),
        DeclareLaunchArgument('controller_config', description='Explicit YAML file path'),
        DeclareLaunchArgument('controllers_config', description='Explicit YAML file path'),
        DeclareLaunchArgument(
            'namespace',
            default_value='/advrf/robot',
            description='Robot namespace',
        ),
        DeclareLaunchArgument(
            'robot_description_file',
            default_value='',
            description='Explicit URDF/Xacro file path',
        ),
        DeclareLaunchArgument(
            'gravity_config',
            default_value='',
            description='ROS parameter YAML selecting joints; empty selects all configured joints',
        ),
        DeclareLaunchArgument(
            'gain_ramp_duration',
            default_value=DEFAULT_GAIN_RAMP_DURATION,
            description='Positive duration in seconds for the configured gain ramp',
        ),
        OpaqueFunction(function=setup),
    ])
