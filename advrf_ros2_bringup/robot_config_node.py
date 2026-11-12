"""Editable in-memory robot definition; consumer configuration is startup-only."""
from pathlib import Path

import rclpy
from rclpy.node import Node
from rcl_interfaces.msg import ParameterDescriptor, FloatingPointRange, SetParametersResult

from .central_config import load_central, adapt_central, unflatten, gain_range


# ROS names are relative to the selected namespace unless they start with / or ~.
NODE_NAME = 'robot_config_node'


class RobotConfigNode(Node):
    def __init__(self):
        super().__init__(NODE_NAME)
        readonly = ParameterDescriptor(read_only=True)
        self.path = Path(self.declare_parameter('configuration_file', '', readonly).value)
        self.description = self.declare_parameter('robot_description', '', readonly).value
        self.declare_parameter('application_policy', 'memory_only', readonly)
        document = load_central(self.path)
        initial = adapt_central(document, description=self.description)['parameters']
        self.names = tuple(initial)

        for name, value in initial.items():
            fixed = name.endswith('.id') or '.gain_bounds.' in name
            descriptor = ParameterDescriptor(
                read_only=fixed,
                description='In-memory robot definition. Edits are not persisted or applied to consumers.')
            parts = name.split('.')

            if '.profiles.' in name and '.gain_bounds.' not in name:
                profile = document['motors'][parts[1]]['profiles'][parts[3]]
                lower, upper = gain_range(profile, parts[4])

                if parts[3] in ('position', 'velocity') and parts[4] in ('gain_3', 'gain_4'):
                    lower = upper = 0.0

                descriptor.floating_point_range = [FloatingPointRange(
                    from_value=lower, to_value=upper, step=0.0)]

            self.declare_parameter(name, value, descriptor)
        # Validate actual ROS overrides, not just the defaults read from disk.

        adapt_central(self.snapshot(), description=self.description)
        self.callback = self.add_on_set_parameters_callback(self.validate_changes)
        self.get_logger().info('Scalar robot configuration ready. Edits remain in memory only.')

    def snapshot(self):
        return unflatten({name: self.get_parameter(name).value for name in self.names})

    def validate_changes(self, parameters):
        try:
            values = {name: self.get_parameter(name).value for name in self.names}

            for parameter in parameters:
                if parameter.name not in values:
                    raise ValueError('Configuration metadata is read-only')

                if parameter.name.endswith('.id') or '.gain_bounds.' in parameter.name:
                    raise ValueError('IDs and gain bounds are startup-only')

                values[parameter.name] = parameter.value

            adapt_central(unflatten(values), description=self.description)
            self.get_logger().info('Configuration edit validated for this node only; files and consumers are unchanged.')
            return SetParametersResult(successful=True)
        except (ValueError, TypeError, KeyError) as error:
            return SetParametersResult(successful=False, reason=str(error))



def main():
    rclpy.init()
    node = None

    try:
        node = RobotConfigNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()
