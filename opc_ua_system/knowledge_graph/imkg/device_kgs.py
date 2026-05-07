from typing import Dict, List

from ..triple_store import Triple


def build_ir_kg() -> List[Triple]:
    """Industrial Robot (IR) 工业机器人 IMKG"""
    triples = [
        Triple("IndustrialRobot", "hasComponent", "RobotArm", "Object", "Object"),
        Triple("IndustrialRobot", "hasComponent", "Controller", "Object", "Object"),
        Triple("IndustrialRobot", "hasComponent", "EndEffector", "Object", "Object"),
        Triple("IndustrialRobot", "hasComponent", "DriveSystem", "Object", "Object"),
        Triple("RobotArm", "hasProperty", "AxisCount", "Object", "Variable"),
        Triple("RobotArm", "hasProperty", "Reach", "Object", "Variable"),
        Triple("RobotArm", "hasProperty", "Payload", "Object", "Variable"),
        Triple("RobotArm", "hasProperty", "Repeatability", "Object", "Variable"),
        Triple("RobotArm", "hasOperation", "MoveJ", "Object", "Method"),
        Triple("RobotArm", "hasOperation", "MoveL", "Object", "Method"),
        Triple("Controller", "hasProperty", "ControlMode", "Object", "Variable"),
        Triple("Controller", "hasProperty", "ProgramNumber", "Object", "Variable"),
        Triple("Controller", "hasProperty", "SpeedOverride", "Object", "Variable"),
        Triple("EndEffector", "hasProperty", "GripperType", "Object", "Variable"),
        Triple("EndEffector", "hasProperty", "GrippingForce", "Object", "Variable"),
        Triple("DriveSystem", "hasProperty", "MotorSpeed", "Object", "Variable"),
        Triple("DriveSystem", "hasProperty", "MotorCurrent", "Object", "Variable"),
        Triple("DriveSystem", "hasProperty", "JointTemperature", "Object", "Variable"),
        Triple("IndustrialRobot", "hasProperty", "RobotStatus", "Object", "Variable"),
        Triple("IndustrialRobot", "hasProperty", "EmergencyStop", "Object", "Variable"),
        Triple("IndustrialRobot", "hasOperation", "StartProgram", "Object", "Method"),
        Triple("IndustrialRobot", "hasOperation", "StopProgram", "Object", "Method"),
        Triple("IndustrialRobot", "hasOperation", "ResetAlarm", "Object", "Method"),
        Triple("RobotArm", "subtypeOf", "IndustrialEquipment", "Object", "Object"),
        Triple("Controller", "controlledBy", "PLC", "Object", "Object"),
    ]
    return triples


def build_cnc_kg() -> List[Triple]:
    """CNC Machine (CNC) 数控机床 IMKG"""
    triples = [
        Triple("CNCMachine", "hasComponent", "Spindle", "Object", "Object"),
        Triple("CNCMachine", "hasComponent", "ToolChanger", "Object", "Object"),
        Triple("CNCMachine", "hasComponent", "Worktable", "Object", "Object"),
        Triple("CNCMachine", "hasComponent", "CoolantSystem", "Object", "Object"),
        Triple("CNCMachine", "hasComponent", "CNCController", "Object", "Object"),
        Triple("Spindle", "hasProperty", "SpindleSpeed", "Object", "Variable"),
        Triple("Spindle", "hasProperty", "SpindleLoad", "Object", "Variable"),
        Triple("Spindle", "hasProperty", "SpindleOrientation", "Object", "Variable"),
        Triple("Spindle", "hasOperation", "StartSpindle", "Object", "Method"),
        Triple("Spindle", "hasOperation", "StopSpindle", "Object", "Method"),
        Triple("ToolChanger", "hasProperty", "ToolNumber", "Object", "Variable"),
        Triple("ToolChanger", "hasProperty", "ToolOffset", "Object", "Variable"),
        Triple("ToolChanger", "hasOperation", "ChangeTool", "Object", "Method"),
        Triple("Worktable", "hasProperty", "XPosition", "Object", "Variable"),
        Triple("Worktable", "hasProperty", "YPosition", "Object", "Variable"),
        Triple("Worktable", "hasProperty", "ZPosition", "Object", "Variable"),
        Triple("Worktable", "hasProperty", "FeedRate", "Object", "Variable"),
        Triple("Worktable", "hasOperation", "MoveTo", "Object", "Method"),
        Triple("CoolantSystem", "hasProperty", "CoolantLevel", "Object", "Variable"),
        Triple("CoolantSystem", "hasProperty", "CoolantPressure", "Object", "Variable"),
        Triple("CNCController", "hasProperty", "ProgramName", "Object", "Variable"),
        Triple("CNCController", "hasProperty", "ExecutionMode", "Object", "Variable"),
        Triple("CNCMachine", "hasProperty", "MachineStatus", "Object", "Variable"),
        Triple("CNCMachine", "hasProperty", "AlarmCode", "Object", "Variable"),
        Triple("CNCMachine", "hasOperation", "LoadProgram", "Object", "Method"),
        Triple("CNCMachine", "hasOperation", "CycleStart", "Object", "Method"),
        Triple("CNCMachine", "hasOperation", "EmergencyStop", "Object", "Method"),
    ]
    return triples


def build_som_kg() -> List[Triple]:
    """Sorting Machine (SOM) 分拣机 IMKG"""
    triples = [
        Triple("SortingMachine", "hasComponent", "Feeder", "Object", "Object"),
        Triple("SortingMachine", "hasComponent", "Conveyor", "Object", "Object"),
        Triple("SortingMachine", "hasComponent", "VisionSystem", "Object", "Object"),
        Triple("SortingMachine", "hasComponent", "SortingActuator", "Object", "Object"),
        Triple("Feeder", "hasProperty", "FeedRate", "Object", "Variable"),
        Triple("Feeder", "hasProperty", "FeederStatus", "Object", "Variable"),
        Triple("Conveyor", "hasProperty", "BeltSpeed", "Object", "Variable"),
        Triple("Conveyor", "hasProperty", "BeltDirection", "Object", "Variable"),
        Triple("Conveyor", "hasOperation", "StartBelt", "Object", "Method"),
        Triple("Conveyor", "hasOperation", "StopBelt", "Object", "Method"),
        Triple("VisionSystem", "hasProperty", "RecognitionRate", "Object", "Variable"),
        Triple("VisionSystem", "hasProperty", "CameraResolution", "Object", "Variable"),
        Triple("VisionSystem", "hasOperation", "CaptureImage", "Object", "Method"),
        Triple("SortingActuator", "hasProperty", "SortCount", "Object", "Variable"),
        Triple("SortingActuator", "hasProperty", "SortCategory", "Object", "Variable"),
        Triple("SortingMachine", "hasProperty", "Throughput", "Object", "Variable"),
        Triple("SortingMachine", "hasProperty", "ErrorCount", "Object", "Variable"),
        Triple("SortingMachine", "hasOperation", "StartSorting", "Object", "Method"),
        Triple("SortingMachine", "hasOperation", "PauseSorting", "Object", "Method"),
    ]
    return triples


def build_scm_kg() -> List[Triple]:
    """Scribing Machine (SCM) 划线机 IMKG"""
    triples = [
        Triple("ScribingMachine", "hasComponent", "ScribingHead", "Object", "Object"),
        Triple("ScribingMachine", "hasComponent", "XYTable", "Object", "Object"),
        Triple("ScribingMachine", "hasComponent", "LaserSystem", "Object", "Object"),
        Triple("ScribingMachine", "hasComponent", "VisionAlign", "Object", "Object"),
        Triple("ScribingHead", "hasProperty", "ScribingForce", "Object", "Variable"),
        Triple("ScribingHead", "hasProperty", "ScribingSpeed", "Object", "Variable"),
        Triple("ScribingHead", "hasProperty", "ToolWear", "Object", "Variable"),
        Triple("ScribingHead", "hasOperation", "StartScribing", "Object", "Method"),
        Triple("XYTable", "hasProperty", "XPosition", "Object", "Variable"),
        Triple("XYTable", "hasProperty", "YPosition", "Object", "Variable"),
        Triple("XYTable", "hasProperty", "TableAccuracy", "Object", "Variable"),
        Triple("LaserSystem", "hasProperty", "LaserPower", "Object", "Variable"),
        Triple("LaserSystem", "hasProperty", "PulseFrequency", "Object", "Variable"),
        Triple("VisionAlign", "hasProperty", "AlignmentAccuracy", "Object", "Variable"),
        Triple("ScribingMachine", "hasProperty", "SubstrateSize", "Object", "Variable"),
        Triple("ScribingMachine", "hasProperty", "ProcessingTime", "Object", "Variable"),
        Triple("ScribingMachine", "hasOperation", "LoadPattern", "Object", "Method"),
        Triple("ScribingMachine", "hasOperation", "StartProcess", "Object", "Method"),
    ]
    return triples


def build_pm_kg() -> List[Triple]:
    """Pick-and-Place Machine (PM) 贴片机 IMKG"""
    triples = [
        Triple("PickPlaceMachine", "hasComponent", "PickHead", "Object", "Object"),
        Triple("PickPlaceMachine", "hasComponent", "PlacementHead", "Object", "Object"),
        Triple("PickPlaceMachine", "hasComponent", "FeederBank", "Object", "Object"),
        Triple("PickPlaceMachine", "hasComponent", "NozzleChanger", "Object", "Object"),
        Triple("PickPlaceMachine", "hasComponent", "PCBConveyor", "Object", "Object"),
        Triple("PickHead", "hasProperty", "PickAccuracy", "Object", "Variable"),
        Triple("PickHead", "hasProperty", "PickSpeed", "Object", "Variable"),
        Triple("PickHead", "hasProperty", "VacuumPressure", "Object", "Variable"),
        Triple("PlacementHead", "hasProperty", "PlacementAccuracy", "Object", "Variable"),
        Triple("PlacementHead", "hasProperty", "PlacementForce", "Object", "Variable"),
        Triple("PlacementHead", "hasProperty", "RotationAngle", "Object", "Variable"),
        Triple("FeederBank", "hasProperty", "FeederCount", "Object", "Variable"),
        Triple("FeederBank", "hasProperty", "ComponentType", "Object", "Variable"),
        Triple("NozzleChanger", "hasProperty", "NozzleType", "Object", "Variable"),
        Triple("NozzleChanger", "hasOperation", "ChangeNozzle", "Object", "Method"),
        Triple("PCBConveyor", "hasProperty", "BoardPosition", "Object", "Variable"),
        Triple("PCBConveyor", "hasOperation", "LoadBoard", "Object", "Method"),
        Triple("PickPlaceMachine", "hasProperty", "CycleTime", "Object", "Variable"),
        Triple("PickPlaceMachine", "hasProperty", "ComponentCount", "Object", "Variable"),
        Triple("PickPlaceMachine", "hasOperation", "StartPlacement", "Object", "Method"),
        Triple("PickPlaceMachine", "hasOperation", "StopPlacement", "Object", "Method"),
    ]
    return triples


def build_pw_kg() -> List[Triple]:
    """Press Welder (PW) 压焊机 IMKG"""
    triples = [
        Triple("PressWelder", "hasComponent", "WeldingHead", "Object", "Object"),
        Triple("PressWelder", "hasComponent", "PressureSystem", "Object", "Object"),
        Triple("PressWelder", "hasComponent", "PowerSupply", "Object", "Object"),
        Triple("PressWelder", "hasComponent", "CoolingSystem", "Object", "Object"),
        Triple("PressWelder", "hasComponent", "WorkHolder", "Object", "Object"),
        Triple("WeldingHead", "hasProperty", "ElectrodeForce", "Object", "Variable"),
        Triple("WeldingHead", "hasProperty", "ElectrodeDisplacement", "Object", "Variable"),
        Triple("WeldingHead", "hasProperty", "WeldCount", "Object", "Variable"),
        Triple("WeldingHead", "hasOperation", "WeldStart", "Object", "Method"),
        Triple("PressureSystem", "hasProperty", "CylinderPressure", "Object", "Variable"),
        Triple("PressureSystem", "hasProperty", "ClampingForce", "Object", "Variable"),
        Triple("PowerSupply", "hasProperty", "WeldingCurrent", "Object", "Variable"),
        Triple("PowerSupply", "hasProperty", "WeldingVoltage", "Object", "Variable"),
        Triple("PowerSupply", "hasProperty", "PowerFactor", "Object", "Variable"),
        Triple("PowerSupply", "hasOperation", "SetCurrent", "Object", "Method"),
        Triple("CoolingSystem", "hasProperty", "WaterTemperature", "Object", "Variable"),
        Triple("CoolingSystem", "hasProperty", "WaterFlow", "Object", "Variable"),
        Triple("WorkHolder", "hasProperty", "ClampStatus", "Object", "Variable"),
        Triple("PressWelder", "hasProperty", "WeldingMode", "Object", "Variable"),
        Triple("PressWelder", "hasProperty", "TotalWeldCount", "Object", "Variable"),
        Triple("PressWelder", "hasOperation", "EmergencyStop", "Object", "Method"),
        Triple("PressWelder", "hasOperation", "ResetCounter", "Object", "Method"),
    ]
    return triples


IMKG_BUILDERS = {
    "IR": build_ir_kg,
    "CNC": build_cnc_kg,
    "SOM": build_som_kg,
    "SCM": build_scm_kg,
    "PM": build_pm_kg,
    "PW": build_pw_kg,
}
