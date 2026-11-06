"""Inspect launch actions and parameter propagation without starting ROS nodes."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import yaml
from launch import LaunchContext
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription

LAUNCH = Path(__file__).resolve().parents[1] / 'launch'


def module(name):
    spec = importlib.util.spec_from_file_location(name, LAUNCH / f'{name}.launch.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class CompositionTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        config = self.root / 'config'
        config.mkdir()
        documents = {
            'controller.yaml': {'controller': {'name': 'arm', 'joints': ['a']}},
            'joint_limits.yaml': {'joint_limits': {'a': {'min_position': -1., 'max_position': 1.,
                                                       'max_velocity': 2., 'max_acceleration': 3.}}},
            'advrf_hardware.yaml': {'joint_map': {7: 'a'}, 'profiles': {
                'position': {'a': {'gains': [2., 0., 1., 0., 0.]}}}},
            'advrf_controllers.yaml': {},
            'joint_control.yaml': {},
            'advrf_bridge.yaml': {'/**': {'ros__parameters': {}}},
        }
        for name, document in documents.items():
            (config / name).write_text(yaml.safe_dump(document))
        self.context = LaunchContext()
        self.context.launch_configurations.update(
            config_dir=str(self.root), namespace='/custom/robot', ecat_namespace='/custom/wire',
            robot_description_file='', control_mode='', use_panel='true', use_joy='true',
            start_bridge='false', use_rviz='false', rviz_config='')

    def test_controllers_have_no_input_or_hardware_nodes(self):
        launch = module('controllers')
        with patch.object(launch, 'Node', side_effect=lambda **kwargs: kwargs):
            nodes = launch.setup(self.context)
        self.assertEqual([node['executable'] for node in nodes], [
            'converter_tx_motor_node', 'joint_trajectory_controller_node', 'joint_goal_manager_node'])
        for node in nodes:
            self.assertEqual(node['namespace'], '/custom/robot')
            self.assertIn(('rx/joint_states', '/custom/wire/rx/joint_states'), node['remappings'])
        self.assertEqual(nodes[0]['parameters'][0]['motor_ids'], [7])

    def test_panel_and_joystick_share_public_interfaces(self):
        launch = module('inputs')
        with patch.object(launch, 'Node', side_effect=lambda **kwargs: kwargs), \
                patch.object(launch, 'ExecuteProcess', side_effect=lambda **kwargs: kwargs):
            actions = launch.setup(self.context)
        self.assertIn('/custom/robot/joint_goal_manager_node', actions[0]['cmd'])
        self.assertEqual([node['executable'] for node in actions[1:]],
                         ['joy_node', 'joystick_input_node', 'manual_joint_controller_node'])
        manual = actions[-1]
        self.assertIn(('joint_commands', '/custom/robot/controllers/joint_commands'), manual['remappings'])
        self.assertEqual(manual['parameters'][0]['lower_positions'], [-1.])
        self.assertEqual(manual['parameters'][0]['upper_positions'], [1.])

    def test_disabled_inputs_need_no_configuration(self):
        self.context.launch_configurations.update(config_dir='/does/not/exist', use_panel='false', use_joy='false')
        self.assertEqual(module('inputs').setup(self.context), [])

    def test_hardware_paths_and_namespace(self):
        launch = module('hardware')
        self.context.environment['EC_CFG'] = '/chosen/ec_cfg.yaml'
        with patch.object(launch, 'Node', side_effect=lambda **kwargs: kwargs):
            node, = launch.setup(self.context)
        self.assertEqual(node['namespace'], '/custom/wire')
        self.assertNotIn('additional_env', node)
        self.assertEqual(node['parameters'], [str(self.root / 'config/advrf_bridge.yaml')])
        self.context.launch_configurations['ecat_namespace'] = ''
        with patch.object(launch, 'Node', side_effect=lambda **kwargs: kwargs):
            node, = launch.setup(self.context)
        self.assertEqual(node['namespace'], '/custom/robot/ecat')

    def test_hardware_auto_activation_override(self):
        launch = module('hardware')
        self.context.environment['EC_CFG'] = '/chosen/ec_cfg.yaml'
        for value in ('true', 'false'):
            self.context.launch_configurations['active_tx_on_first_msg'] = value
            with patch.object(launch, 'Node', side_effect=lambda **kwargs: kwargs):
                node, = launch.setup(self.context)
            self.assertEqual(node['parameters'][-1], {'active_tx_on_first_msg': value == 'true'})
        self.context.launch_configurations['active_tx_on_first_msg'] = 'invalid'
        with self.assertRaisesRegex(ValueError, 'active_tx_on_first_msg'):
            launch.setup(self.context)

    def test_hardware_warns_without_ec_cfg(self):
        launch = module('hardware')
        for value in [None, '']:
            if value is None:
                self.context.environment.pop('EC_CFG', None)
            else:
                self.context.environment['EC_CFG'] = value
            with patch.object(launch, 'get_logger') as logger, \
                    patch.object(launch, 'Node', side_effect=lambda **kwargs: kwargs):
                node, = launch.setup(self.context)
            logger.return_value.warning.assert_called_once_with('EC_CFG not set')
            self.assertNotIn('additional_env', node)

    def test_visualization_without_model(self):
        launch = module('visualization')
        self.assertEqual(launch.setup(self.context), [])
        self.context.launch_configurations['use_rviz'] = 'true'
        with self.assertRaisesRegex(ValueError, 'requires robot_description_file'):
            launch.setup(self.context)

    def test_robot_composes_four_groups_and_bridge_is_opt_in(self):
        description = module('robot').generate_launch_description()
        for action in description.entities:
            if isinstance(action, DeclareLaunchArgument):
                action.execute(self.context)
        includes = [action for action in description.entities if isinstance(action, IncludeLaunchDescription)]
        self.assertEqual(len(includes), 4)
        self.assertFalse(includes[2].condition.evaluate(self.context))
        self.context.launch_configurations['start_bridge'] = 'true'
        self.assertTrue(includes[2].condition.evaluate(self.context))
        for include in includes:
            # Load included launch files, without executing their nodes.
            self.assertIsNotNone(include.launch_description_source.get_launch_description(self.context))


if __name__ == '__main__':
    unittest.main()
