"""ROS-only configuration consistency, independent of hardware and ROS discovery."""
import copy
import tempfile
import unittest
from pathlib import Path
import yaml
from advrf_ros2_bringup.robot_config import load_robot


class RobotConfigTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'config').mkdir()
        self.document = {
            'control_mode': 'position',
            'motors': {
                name: {
                    'id': identifier,
                    'limits': {
                        'position_lower': -1.0,
                        'position_upper': 1.0,
                        'max_velocity': 2.0,
                        'max_acceleration': 3.0,
                    },
                    'profiles': {
                        mode: {f'gain_{i}': value for i, value in enumerate(gains)}
                        for mode, gains in profiles.items()
                    },
                }
                for name, identifier, profiles in (
                    ('b', 7, {'position': [5., 6., 7., 0., 0.], 'impedance': [6., 7., 8., 9., 10.]}),
                    ('a', 1, {'position': [2., 3., 4., 0., 0.], 'impedance': [1., 2., 3., 4., 5.]}),
                )
            },
        }
        self.write_central()
        self.write('advrf_controllers.yaml', {})
        self.write('moveit_controllers.yaml', {'moveit_simple_controller_manager': {
            'controller_names': ['arm'], 'arm': {'type': 'FollowJointTrajectory',
            'action_ns': 'follow_joint_trajectory', 'joints': ['a', 'b']}}})

    def write_central(self, document=None):
        self.write('robot_config.yaml', {
            '/**/robot_config_node': {
                'ros__parameters': self.document if document is None else document,
            },
        })

    def write(self, name, value):
        (self.root / 'config' / name).write_text(yaml.safe_dump(value))

    def load(self, **kwargs):
        return load_robot(self.root / 'config/robot_config.yaml', '/robot',
                          controller_config=kwargs.pop('controller_config', self.root / 'config/moveit_controllers.yaml'),
                          controllers_config=self.root / 'config/advrf_controllers.yaml', **kwargs)

    def test_without_urdf_alignment_and_position_gains_unchanged(self):
        robot = self.load()
        cmd = robot['nodes']['joint_command_controller_node']
        self.assertEqual(cmd['joints'], ['a', 'b'])
        self.assertEqual(cmd['motor_ids'], [1, 7])
        self.assertEqual(cmd['joint_gains'], [2., 3., 4., 0., 0., 5., 6., 7., 0., 0.])
        self.assertEqual(robot['action_name'], '/robot/arm/follow_joint_trajectory')

    def test_standalone_controller_without_moveit_file(self):
        (self.root / 'config/moveit_controllers.yaml').unlink()
        self.write('controller.yaml', {'controller': {
            'name': 'arm', 'action_ns': 'follow_joint_trajectory', 'joints': ['a', 'b']}})
        robot = self.load(controller_config=self.root / 'config/controller.yaml')
        self.assertEqual(robot['action_name'], '/robot/arm/follow_joint_trajectory')
        self.assertEqual(robot['moveit'], {})

    def test_explicit_files_in_unrelated_locations(self):
        paths = []
        for index, filename in enumerate(('robot_config.yaml', 'moveit_controllers.yaml', 'advrf_controllers.yaml')):
            directory = self.root / str(index)
            directory.mkdir()
            target = directory / 'custom.yaml'
            (self.root / 'config' / filename).rename(target)
            paths.append(target)
        robot = load_robot(paths[0], '/robot', controller_config=paths[1], controllers_config=paths[2])
        self.assertEqual(robot['nodes']['joint_command_controller_node']['motor_ids'], [1, 7])
        self.assertEqual(robot['configuration_file'], str(paths[0]))

    def test_impedance_preserves_all_five_values(self):
        robot = self.load(control_mode='impedance')
        self.assertEqual(robot['nodes']['joint_command_controller_node']['joint_gains'],
                         [1., 2., 3., 4., 5., 6., 7., 8., 9., 10.])

    def test_urdf_rejects_excessive_limits(self):
        path = self.root / 'robot.urdf'
        path.write_text('<robot name="test">' + ''.join(
            f'<joint name="{j}" type="revolute"><limit lower="-1" upper="1" velocity="2"/></joint>'
            for j in ['a', 'b']) + '</robot>')
        self.assertEqual(self.load(urdf=str(path))['limits']['position_lower'], [-1., -1.])
        self.document['motors']['a']['limits']['max_velocity'] = 3.0
        self.write_central()

        with self.assertRaisesRegex(ValueError, 'exceed URDF'):
            self.load(urdf=str(path))

    def test_missing_central_configuration_does_not_use_legacy_files(self):
        (self.root / 'config/robot_config.yaml').unlink()
        self.write('advrf_hardware.yaml', {})
        self.write('joint_limits.yaml', {})

        with self.assertRaisesRegex(FileNotFoundError, 'robot_config.yaml'):
            self.load()

    def test_duplicate_yaml_keys_are_rejected(self):
        (self.root / 'config/robot_config.yaml').write_text('motors: {}\nmotors: {}\n')

        with self.assertRaisesRegex(ValueError, 'Duplicate YAML key'):
            self.load()

    def test_reject_bad_mapping_and_profiles(self):
        for change in ('string_id', 'duplicate_id', 'missing_joint', 'missing_mode', 'bad_gains', 'nan'):
            with self.subTest(change=change):
                document = copy.deepcopy(self.document)
                motors = document['motors']

                if change == 'string_id':
                    motors['a']['id'] = '1'
                elif change == 'duplicate_id':
                    motors['a']['id'] = 7
                elif change == 'missing_joint':
                    del motors['a']
                elif change == 'missing_mode':
                    del motors['a']['profiles']['position']
                elif change == 'bad_gains':
                    del motors['a']['profiles']['position']['gain_0']
                elif change == 'nan':
                    motors['a']['profiles']['position']['gain_0'] = float('nan')

                self.write_central(document)

                with self.assertRaises(ValueError):
                    self.load()

    def test_reject_duplicate_limit_sources(self):
        self.write('advrf_controllers.yaml', {
            '/**/joint_go_to_node': {'ros__parameters': {'max_velocity': [99., 99.]}}})
        with self.assertRaisesRegex(ValueError, 'shared joint limits'): self.load()


if __name__ == '__main__':
    unittest.main()
