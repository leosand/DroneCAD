cmake_minimum_required(VERSION 3.8)
project(humanoid_control)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config DESTINATION share/${PROJECT_NAME})
install(PROGRAMS scripts/squat_test.py DESTINATION lib/${PROJECT_NAME})

ament_package()
