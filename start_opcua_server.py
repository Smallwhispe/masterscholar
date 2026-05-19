import asyncio
import logging
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "opc_ua_system"))

from asyncua import Server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OPCUA_Server")

NAMESPACE_URI = "http://example.org/UA/"

DEVICE_TYPES = {
    "CNC": {
        "Spindle": {
            "SpindleSpeed": (8000, 12000),
            "SpindleLoad": (30.0, 80.0),
            "ToolPosition": (1, 24),
        },
        "ToolChanger": {
            "ToolNumber": (1, 24),
            "ToolWear": (0.0, 0.5),
        },
        "Worktable": {
            "XPosition": (-500.0, 500.0),
            "YPosition": (-500.0, 500.0),
        },
    },
    "IR": {
        "RobotArm": {
            "Joint1Angle": (-180.0, 180.0),
            "Joint2Angle": (-120.0, 120.0),
            "TCP_Speed": (0.0, 2000.0),
        },
        "EndEffector": {
            "GripperForce": (0.0, 100.0),
            "GripperStatus": (0, 1),
        },
        "Controller": {
            "ProgramNumber": (1, 99),
            "CycleTime": (1.0, 60.0),
        },
    },
    "SOM": {
        "Conveyor": {
            "BeltSpeed": (0.0, 5.0),
            "MotorCurrent": (1.0, 15.0),
        },
        "VisionSystem": {
            "ObjectCount": (0, 1000),
            "DefectRate": (0.0, 5.0),
        },
        "Feeder": {
            "FeedRate": (0, 500),
            "JamDetected": (0, 1),
        },
    },
    "SCM": {
        "LaserHead": {
            "LaserPower": (0.0, 100.0),
            "FocusPosition": (-10.0, 10.0),
        },
        "ScribingTable": {
            "XPosition": (-500.0, 500.0),
            "YPosition": (-500.0, 500.0),
        },
        "VisionAlign": {
            "AlignmentOffset": (-5.0, 5.0),
        },
    },
    "PM": {
        "PickArm": {
            "XPosition": (-300.0, 300.0),
            "YPosition": (-300.0, 300.0),
            "VacuumPressure": (0.0, 100.0),
        },
        "PlacementHead": {
            "NozzleType": (1, 8),
            "PlacementForce": (0.0, 10.0),
        },
        "FeederBank": {
            "ComponentCount": (0, 500),
            "FeederIndex": (1, 40),
        },
    },
    "PW": {
        "WeldingGun": {
            "Current": (0.0, 300.0),
            "Voltage": (0.0, 50.0),
            "Force": (0.0, 5000.0),
        },
        "PressUnit": {
            "Pressure": (0.0, 200.0),
            "Stroke": (0.0, 100.0),
        },
        "CoolingSystem": {
            "FlowRate": (0.0, 20.0),
            "Temperature": (10.0, 80.0),
        },
    },
}


async def build_device_nodes(server: Server, idx: int, device_type: str):
    objects = server.nodes.objects

    device = await objects.add_object(idx, f"{device_type}Machine_01")
    components = DEVICE_TYPES.get(device_type, {})
    variables = {}

    for comp_name, vars_dict in components.items():
        comp = await device.add_object(idx, comp_name)
        for var_name, (lo, hi) in vars_dict.items():
            default = lo if isinstance(lo, int) else round(lo + (hi - lo) * 0.5, 2)
            data_type = "Int32" if isinstance(lo, int) else "Double"
            v = await comp.add_variable(idx, var_name, default)
            await v.set_writable()
            variables[f"{comp_name}.{var_name}"] = {
                "node": v, "lo": lo, "hi": hi, "type": data_type,
            }

    logger.info(
        f"{device_type} 设备节点树已构建: "
        f"{len(components)} 个组件, {len(variables)} 个变量"
    )
    return variables


async def update_loop(variables: dict, interval: float = 1.0):
    logger.info(f"启动数据更新循环 (间隔 {interval}s)")
    while True:
        for name, info in variables.items():
            lo, hi = info["lo"], info["hi"]
            if isinstance(lo, int):
                value = random.randint(lo, hi)
            else:
                value = round(random.uniform(lo, hi), 2)
            await info["node"].write_value(value)
        await asyncio.sleep(interval)


async def main():
    device_type = sys.argv[1] if len(sys.argv) > 1 else "CNC"
    if device_type not in DEVICE_TYPES:
        logger.error(f"未知设备类型: {device_type}, 可选: {list(DEVICE_TYPES.keys())}")
        return

    port = int(sys.argv[2]) if len(sys.argv) > 2 else 4840

    server = Server()
    await server.init()
    server.set_endpoint(f"opc.tcp://0.0.0.0:{port}")
    server.set_server_name(f"{device_type} OPC UA Simulation Server")
    idx = await server.register_namespace(NAMESPACE_URI)

    logger.info(f"OPC UA 服务器启动中: opc.tcp://0.0.0.0:{port}")
    logger.info(f"设备类型: {device_type} | 命名空间: {NAMESPACE_URI}")

    variables = await build_device_nodes(server, idx, device_type)

    async with server:
        asyncio.create_task(update_loop(variables, interval=1.0))
        logger.info(f"服务器已就绪, 持续更新中... (Ctrl+C 停止)")
        try:
            await asyncio.sleep(float("inf"))
        except KeyboardInterrupt:
            logger.info("服务器正在关闭...")


if __name__ == "__main__":
    asyncio.run(main())
