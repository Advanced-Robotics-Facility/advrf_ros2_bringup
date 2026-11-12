"""Scalar edits stay in memory and never write configuration files."""
import os
os.environ['ROS_DOMAIN_ID'] = '216'
os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'LOCALHOST'
import tempfile
from pathlib import Path
import unittest
import yaml
import rclpy
from rclpy.parameter import Parameter
from advrf_ros2_bringup.robot_config_node import RobotConfigNode
from advrf_ros2_bringup.robot_config import load_robot


class ConfigNodeTest(unittest.TestCase):
    def test_scalar_edits_bounds_without_persistence(self):
        with tempfile.TemporaryDirectory() as temporary:
            os.environ['ROS_LOG_DIR'] = temporary
            config = Path(temporary) / 'config'
            config.mkdir()
            path = config / 'robot_config.yaml'
            motor = {'id': 1, 'limits': {'position_lower': -1., 'position_upper': 1.,
                     'max_velocity': 2., 'max_acceleration': 3.}, 'profiles': {'position': {
                     'gain_0': .009, 'gain_1': 0., 'gain_2': 0., 'gain_3': 0., 'gain_4': 0.,
                     'gain_bounds': {'gain_0': {'min': 0., 'max': .02}}}}}
            path.write_text(yaml.safe_dump({'/**/robot_config_node': {
                'ros__parameters': {'control_mode': 'position', 'motors': {'a': motor}}}}))
            (config / 'controller.yaml').write_text('controller: {name: arm, joints: [a]}\n')
            (config / 'advrf_controllers.yaml').write_text('{}\n')
            rclpy.init(args=['--ros-args', '-p', f'configuration_file:={path}'])
            node = RobotConfigNode()
            original = path.read_bytes()
            try:
                key = 'motors.a.profiles.position.gain_0'
                self.assertEqual(node.get_parameter(key).value, .009)
                descriptor = node.describe_parameter(key)
                self.assertEqual(descriptor.floating_point_range[0].to_value, .02)
                self.assertFalse(node.set_parameters_atomically([Parameter(key, value=.03)]).successful)
                self.assertTrue(node.set_parameters_atomically([Parameter(key, value=.015)]).successful)
                self.assertFalse(node.set_parameters_atomically([Parameter('motors.a.id', value=2)]).successful)
                self.assertFalse(node.set_parameters_atomically([Parameter('control_mode', value='velocity')]).successful)
                self.assertFalse(node.set_parameters_atomically([
                    Parameter('motors.a.limits.position_lower', value=2.)]).successful)
                self.assertEqual(node.get_parameter('application_policy').value, 'memory_only')
                services = {name for name, _ in node.get_service_names_and_types()}
                self.assertNotIn('/robot_config_node/save', services)
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(
                    load_robot(path, '/robot', controller_config=config / 'controller.yaml',
                               controllers_config=config / 'advrf_controllers.yaml')['nodes']['joint_command_controller_node']['joint_gains'][0],
                    .009,
                )
            finally:
                node.destroy_node()
                rclpy.shutdown()


if __name__ == '__main__':
    unittest.main()
