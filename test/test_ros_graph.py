"""Graph export checks without a running robot."""
import importlib.machinery
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/ros_graph'
loader = importlib.machinery.SourceFileLoader('ros_graph', str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
graph = importlib.util.module_from_spec(spec)
loader.exec_module(graph)


class GraphTest(unittest.TestCase):
    def test_noise_filters(self):
        for name, kind in [('/a/get_parameters', 'service'), ('/rosout', 'topic'),
                           ('/parameter_events', 'topic'), ('/a/_action/status', 'topic')]:
            self.assertFalse(graph.visible(name, kind))
        self.assertTrue(graph.visible('/a/home', 'service'))
        self.assertTrue(graph.visible('/a/get_parameters', 'service', True))
        self.assertFalse(graph.visible('/a/_action/status', 'topic', True))

    def test_namespace_boundary_and_connected_nodes(self):
        def record(node, name, role):
            return dict(node=node, name=name, role=role, kind=graph.ROLES[role], types=['test/Type'])
        records = [record('/advrf/miranda/controller', '/arm/trajectory', 'action_server'),
                   record('/move_group', '/arm/trajectory', 'action_client'),
                   record('/move_group', '/other', 'publish'),
                   record('/advrf/miranda2/controller', '/another', 'publish')]
        selected = graph.select(records, ['/advrf/miranda'])
        self.assertEqual(selected, records[:2])
        self.assertEqual(graph.select(records, ['/advrf/miranda'], True), records[:1])
        dot = graph.dot_graph(selected)
        self.assertIn('shape=box3d', dot)
        self.assertIn('action client', dot)
        self.assertIn('action server', dot)
        self.assertEqual(len(graph.select(records, ['/'])), 4)


if __name__ == '__main__':
    unittest.main()
