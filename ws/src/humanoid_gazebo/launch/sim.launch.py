"""DroneCAD — lancement de la simulation Gazebo Harmonic (serveur sans interface par défaut).

EN: gz sim (server-only) + robot_state_publisher + spawn + ros_gz bridge + ros2_control
    controllers. Arguments: world_file (default flat_ground.sdf), enable_camera.
FR : gz sim (serveur seul) + robot_state_publisher + spawn + pont ros_gz + contrôleurs
    ros2_control. Arguments : world_file (défaut flat_ground.sdf), enable_camera.
"""

from __future__ import annotations

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    world_file = LaunchConfiguration("world_file")
    enable_camera = LaunchConfiguration("enable_camera")

    xacro_file = PathJoinSubstitution(
        [FindPackageShare("humanoid_description"), "urdf", "humanoid.urdf.xacro"]
    )
    controllers_yaml = PathJoinSubstitution(
        [FindPackageShare("humanoid_control"), "config", "controllers.yaml"]
    )
    robot_description = ParameterValue(
        Command(
            [
                "xacro ", xacro_file,
                " enable_camera:=", enable_camera,
                " controllers_yaml:=", controllers_yaml,
            ]
        ),
        value_type=str,
    )

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"]
            )
        ),
        launch_arguments={
            "gz_args": [
                "-r -s ",
                PathJoinSubstitution(
                    [FindPackageShare("humanoid_gazebo"), "worlds", world_file]
                ),
            ],
            "on_exit_shutdown": "True",
        }.items(),
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": robot_description, "use_sim_time": True}],
        output="screen",
    )

    # EN: spawn via a waiter — `ros_gz_sim create` has no "wait for the world" flag, and a fixed
    #     timer is a race: on a slow CI runner (4 vCPU) the spawn was lost and the robot never
    #     appeared (CI run 35412876213, 2026-09-19).
    # FR : spawn via un attentiste — `ros_gz_sim create` n'a aucune option « attendre le monde »,
    #     et une minuterie fixe est une course : sur un runner CI lent (4 vCPU), le spawn était
    #     perdu et le robot n'apparaissait jamais (run CI 35412876213, 2026-09-19).
    spawn = TimerAction(
        period=1.0,
        actions=[
            Node(
                package="humanoid_gazebo",
                executable="spawn_ready.py",
                arguments=[
                    "--world",
                    PythonExpression(["'", world_file, "'.replace('.sdf', '')"]),
                    "--topic", "/robot_description",
                    "--name", "humanoid",
                    "--z", "1.08",
                ],
                output="screen",
            )
        ],
    )

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        parameters=[
            {
                "config_file": PathJoinSubstitution(
                    [FindPackageShare("humanoid_gazebo"), "config", "ros_gz_bridge.yaml"]
                ),
                "use_sim_time": True,
            }
        ],
        output="screen",
    )

    # EN: controllers right after spawn (shorter unactuated window; the spawner waits for the
    #     controller manager, which the Gazebo plugin starts with the model).
    # FR : contrôleurs juste après le spawn (fenêtre non-actuée plus courte ; le spawner attend
    #     le controller_manager, démarré par le plugin Gazebo avec le modèle).
    controllers = TimerAction(
        period=3.0,
        actions=[
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=["joint_state_broadcaster", "--controller-manager-timeout", "180"],
                parameters=[{"use_sim_time": True}],
                output="screen",
            ),
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=["joint_position_controller", "--controller-manager-timeout", "180"],
                parameters=[{"use_sim_time": True}],
                output="screen",
            ),
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "world_file",
                default_value="flat_ground.sdf",
                description="Fichier de monde dans worlds/ / world file in worlds/",
            ),
            DeclareLaunchArgument(
                "enable_camera",
                default_value="true",
                description="Active la caméra RGB-D / enable the RGB-D camera",
            ),
            gz_sim,
            robot_state_publisher,
            spawn,
            bridge,
            controllers,
        ]
    )
