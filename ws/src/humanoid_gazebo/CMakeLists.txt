cmake_minimum_required(VERSION 3.8)
project(humanoid_gazebo)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch worlds config DESTINATION share/${PROJECT_NAME})
# EN: spawn wrapper runs as a node executable / FR : le wrapper de spawn est un exécutable ROS
install(PROGRAMS scripts/spawn_ready.py DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_stand test/test_stand.py TIMEOUT 600)
endif()

ament_package()
