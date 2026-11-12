# advrf_ros2_bringup
ros version: jazzy

## Quick Use

```bash
ros2 launch advrf_ros2_miranda_bringup miranda.launch.py
```

Shared controller launch, explicit YAML paths:

```bash
ros2 launch advrf_ros2_bringup controllers.launch.py \
  robot_config:=/path/to/robot_config.yaml \
  controller_config:=/path/to/controller.yaml \
  controllers_config:=/path/to/advrf_controllers.yaml
```

## Edit Config

| Argument | File content | Launch |
| --- | --- | --- |
| `robot_config` | Motor IDs, profiles, gains, limits | Controllers, inputs, gravity, robot |
| `controller_config` | Trajectory controller name, joints, action | Controllers, inputs, gravity, robot |
| `controllers_config` | ADVRF controller node parameters | Controllers, inputs, gravity, robot |
| `joint_control_config` | Joystick/manual control parameters | Inputs, robot |
| `bridge_config` | EtherCAT bridge ROS parameters | Hardware, robot |
| `diagnostics_config` | Diagnostic aggregator parameters | Diag |
| `robot_description_file` | URDF/Xacro | Controllers, inputs, visualization, gravity, robot |
| `rviz_config` | RViz display configuration | Visualization, robot |

- File paths only; no `config_dir`, filename search or URDF auto-detection.
- `controller_config`: standalone `controller` schema or `moveit_simple_controller_manager` schema.
- `robot_description_file`: empty for no model; required for RViz and gravity compensation.
- Robot wrappers: explicit installed-file defaults; each file independently overridable.
- Miranda MoveIt: `robot_config`, `controllers_config`, `bridge_config`, `moveit_controllers_file`, `kinematics_file`, `pilz_cartesian_limits_file`, `robot_description_file`, `robot_srdf_file`, `rviz_config`.
- Single `namespace` argument; EtherCAT endpoints under `<namespace>/ecat`.
- `EC_CFG`: separate EtherCAT client YAML environment variable.

## Nodes Details

Node: `robot_config_node` / motor configuration parameters

- Parameters: `configuration_file`, `robot_description`, `control_mode`, `motors.*`, `application_policy`.
- Topics: standard ROS parameter events.
- Services: standard ROS parameter services.
- Actions: none.
- Runtime edits: memory only; restart consumers after source YAML changes.

## Dependencies

- `rcl_interfaces`
- `std_srvs`
- `xacro`
- `advrf_ros2_motors_controller`
- `advrf_ros2_io`
- `advrf_ros2_ecat`
- `ament_index_python`
- `rclpy`
- `rmw_cyclonedds_cpp`
- `launch`
- `launch_ros`
- `joy`
- `robot_state_publisher`
- `rviz2`
- `rqt_gui`
- `diagnostic_aggregator`
- `rqt_robot_monitor`

## TroubleShooting

| Symptom | Check |
| --- | --- |
| Missing YAML | Explicit file argument; installed robot resources |
| Unknown `config_dir` usage | Replace with individual file arguments above |
| RViz without model | Set `robot_description_file` to a URDF/Xacro |
| No bridge | `start_bridge:=true`; export `EC_CFG`; start master/backend |
