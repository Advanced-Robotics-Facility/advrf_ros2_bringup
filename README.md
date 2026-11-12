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
| `gravity_config` | Selected gravity compensation joints | Gravity compensation |
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

## Motor startup mode

Keep your existing `EC_CFG` export and select a Miranda hardware profile at bridge startup:

```bash
ros2 launch advrf_ros2_miranda_bringup bridge.launch.py motor_start_mode:=position
# Also supported: impedance, idle
```

The profile files are resolved relative to the robot control YAML referenced by
`EC_CFG`: `motor/miranda_pos_3b.yaml`, `motor/miranda_imp_d4.yaml`,
`motor/miranda_idle.yaml`. A missing profile fails before starting the bridge.

For another profile, pass `motor_start_config:=/absolute/path/to/motor.yaml`
(instead of `motor_start_mode`). The shared `hardware.launch.py` also accepts
`motor_start_config`; relative paths refer to the original robot control YAML directory.

Only the bridge process receives a temporary `EC_CFG`. Source files and the shell
environment are unchanged. Network, timing, IDs, trajectory and other device
settings are preserved, with file references made absolute. Temporary YAML files
are removed on launch shutdown. Without either argument, the original `EC_CFG`
is used directly.

This selects the hardware START mode and gains when the bridge starts. It does
not switch running motors or change the separate ROS controller `control_mode`.
Set that controller profile consistently when launching controllers separately.
The named mode argument is exposed by Miranda `bridge.launch.py`.

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
