cmake_minimum_required(VERSION 3.16)
project(advrf_ros2_bringup)
find_package(ament_cmake REQUIRED)

install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})
install(PROGRAMS scripts/ros_graph DESTINATION lib/${PROJECT_NAME})
install(FILES README.md DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(Python3 REQUIRED COMPONENTS Interpreter)
  ament_add_test(test_ros_graph
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/test/test_ros_graph.py"
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO)
  ament_add_test(test_launch_composition
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/test/test_launch_composition.py"
    ENV "ROS_LOG_DIR=/tmp/advrf_bringup_test_logs"
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO)
endif()

ament_package()
