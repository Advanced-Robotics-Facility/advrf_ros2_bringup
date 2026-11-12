cmake_minimum_required(VERSION 3.16)
project(advrf_ros2_bringup)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(${PROJECT_NAME})

install(DIRECTORY launch config DESTINATION share/${PROJECT_NAME})
install(PROGRAMS scripts/ros_graph scripts/robot_config_node DESTINATION lib/${PROJECT_NAME})
install(FILES README.md DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(Python3 REQUIRED COMPONENTS Interpreter)
  ament_add_test(test_ros_graph
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/test/test_ros_graph.py"
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO)
  ament_add_test(test_launch_composition
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/test/test_launch_composition.py"
    APPEND_ENV "PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}"
    ENV "ROS_LOG_DIR=/tmp/advrf_bringup_test_logs"
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO)
  foreach(config_test test_robot_config test_central_config test_robot_config_node)
    ament_add_test(${config_test}
      COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/test/${config_test}.py"
      APPEND_ENV "PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}"
      ENV "ROS_LOG_DIR=/tmp/advrf_bringup_config_test_logs"
      GENERATE_RESULT_FOR_RETURN_CODE_ZERO
      TIMEOUT 20)
  endforeach()
endif()

ament_package()
