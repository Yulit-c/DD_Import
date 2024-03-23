bl_info = {
    "name": "DD FBX Importer",
    "author": "Yu-Lit",
    "version": (0, 0, 1),
    "blender": (4, 1, 0),
    "location": "",
    "description": "",
    "warning": "",
    "support": "COMMUNITY",
    "doc_url": "",
    "tracker_url": "",
    "category": "",
}


if "bpy" in locals():
    import importlib

    reloadable_modules = [
        "preparation_logger",
        "debug",
    ]

    for module in reloadable_modules:
        if module in locals():
            importlib.reload(locals()[module])

else:
    from .Logging import preparation_logger
    from . import debug

import bpy
from bpy_extras.io_utils import orientation_helper
from addon_utils import paths, check
from bpy.path import module_names

from pathlib import Path

from .debug import (
    launch_debug_server,
)

"""---------------------------------------------------------
------------------------------------------------------------
    Logger
------------------------------------------------------------
---------------------------------------------------------"""
from .Logging.preparation_logger import preparating_logger

logger = preparating_logger(__name__)


"""---------------------------------------------------------
------------------------------------------------------------
    Variables
------------------------------------------------------------
---------------------------------------------------------"""
presets_directory: Path = Path(bpy.utils.resource_path("USER")).joinpath("scripts", "presets", "DDFBXImport")


"""---------------------------------------------------------
------------------------------------------------------------
    Functions
------------------------------------------------------------
---------------------------------------------------------"""


def get_enabled_addon_list():
    enabled_addon_list = []
    for path in paths():
        for mod_name, mod_path in module_names(path):
            is_enabled, is_loaded = check(mod_name)
            if is_enabled:
                enabled_addon_list.append(mod_name)
    return enabled_addon_list


def get_preset_directory() -> Path:
    importer = get_ddfbx_addon_preferences().importer
    match int(importer):
        case 0:
            source_directory = presets_directory.joinpath("BuiltIn")

        case 1:
            source_directory = presets_directory.joinpath("BetterFBX")
    return source_directory


"""---------------------------------------------------------
------------------------------------------------------------
    Addon Preference
------------------------------------------------------------
---------------------------------------------------------"""


class DDFBXIMPORT_PREF_addon_preference(bpy.types.AddonPreferences):
    bl_idname = __package__

    def get_item_list(scene, context) -> list[tuple[str]]:
        items = [("0", "Built-In", "")]
        if "better_fbx" in get_enabled_addon_list():
            items.append(("1", "Better FBX", ""))
        return items

    importer: bpy.props.EnumProperty(
        name="Importer",
        description="Description",
        items=get_item_list,
        default=0,
    )

    def draw(self, context):
        layout = self.layout
        split_factor = 0.5
        box = layout.box()

        row = box.row()
        sp = row.split(align=True, factor=split_factor)
        sp.label(text="Importer")
        sp.prop(self, "importer", text="")


def get_ddfbx_addon_preferences() -> DDFBXIMPORT_PREF_addon_preference:
    """
    アドオンが定義したプリファレンスの変数を取得して使用できるようにする｡
    自身のパッケージ名からプリファレンスを取得する｡


    Returns
    -------
    AddonPreferences
        取得したプリファレンスのインスタンス
    """

    splitted_package_name = __package__.split(".")[0]
    addon_preferences = bpy.context.preferences.addons[splitted_package_name].preferences

    return addon_preferences


"""---------------------------------------------------------
------------------------------------------------------------
    Property Group
------------------------------------------------------------
---------------------------------------------------------"""


class DDFBXIMPORT_ImportOperatorBase(bpy.types.Operator):
    def get_import_presets(self, context) -> list[tuple[str]]:
        items = []
        items.append(("0", "Default", "Default Parameters"))

        for n, i in enumerate(get_preset_directory().glob("**/*.pres"), 1):
            items.append((str(n), str(i.stem), ""))
        return items

    def get_selected_preset_file(self, context) -> Path:
        items = DDFBXIMPORT_ImportOperatorBase.get_import_presets(self, context)
        selected_item = items[int(self.presets_files)][1]
        source_file = get_preset_directory().joinpath(f"{selected_item}.pres")
        return source_file

    def assign_preset_parameters(self, context):
        if self.presets_files == "0":
            source_file = Path(__file__).parent.joinpath("Default.pres")
        else:
            source_file = DDFBXIMPORT_ImportOperatorBase.get_selected_preset_file(self, context)
            logger.debug(source_file)

        with open(source_file, "r") as f:
            logger.debug(f.read())

    # ---------------------------------------------------------------------------------
    presets_files: bpy.props.EnumProperty(
        name="Presets Files",
        description="",
        items=get_import_presets,
        update=assign_preset_parameters,
        default=0,
    )


"""---------------------------------------------------------
------------------------------------------------------------
    Operator
------------------------------------------------------------
---------------------------------------------------------"""


class DDFBXIMPORT_OT_create_preset(bpy.types.Operator):
    bl_idname = "ddfbx.create_preset"
    bl_label = "Create Preset"
    bl_description = ""
    bl_options = {"UNDO", "INTERNAL"}

    file_name: bpy.props.StringProperty(
        name="File Name",
        description="",
        default="",
    )

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="Preset Name")
        row.prop(self, "file_name")

    def execute(self, context):
        preset_dir = get_preset_directory()
        preset_dir.mkdir(parents=True, exist_ok=True)
        file_path = preset_dir.joinpath(f"{self.file_name}.pres")
        with open(file_path, "w") as f:
            f.write("New Custom Preset File")

        return {"FINISHED"}


class DDFBXIMPORT_OT_delete_preset(bpy.types.Operator):
    bl_idname = "ddfbx.delete_preset"
    bl_label = "Delete Preset"
    bl_description = ""
    bl_options = {"UNDO", "INTERNAL"}

    target_file: bpy.props.StringProperty(
        name="Target File",
        description="",
        default="",
    )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        logger.debug(self.target_file)
        return {"FINISHED"}


class DDFBXIMPORT_OT_built_in_import(DDFBXIMPORT_ImportOperatorBase):
    bl_idname = "ddfbx.built_in_import"
    bl_label = "Built-In Import"
    bl_description = ""
    bl_options = {"UNDO", "PRESET"}

    directory: bpy.props.StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE"})
    files: bpy.props.StringProperty(options={"SKIP_SAVE"})

    def invoke(self, context, event):
        logger.debug("Invoke")
        return context.window_manager.invoke_props_dialog(self, width=360)

    def draw(self, context):
        layout = self.layout
        # layout.label(text="Built-In Importer")
        row = layout.row(align=True)
        row.prop(self, "presets_files", text="Presets")
        row.operator(DDFBXIMPORT_OT_create_preset.bl_idname, text="", icon="PLUS")
        op: DDFBXIMPORT_OT_delete_preset = row.operator(
            DDFBXIMPORT_OT_delete_preset.bl_idname, text="", icon="REMOVE"
        )
        op.target_file = str(self.get_selected_preset_file(context))

    def execute(self, context):
        logger.debug("Execute")
        file_list = [i.strip() for i in self.files[1:-1].split(",")]
        for i in file_list:
            file_name = i[1:-1]
            # logger.debug(file_name)
            file_path = Path(self.directory).joinpath(file_name)
            logger.debug(file_path)
            bpy.ops.import_scene.fbx(filepath=str(file_path))
            logger.debug(f'Load Complete\n{"":#<70}')

        return {"FINISHED"}


class DDFBXIMPORT_OT_better_fbx_import(bpy.types.Operator):
    bl_idname = "ddfbx.better_fbx_import"
    bl_label = "Better FBX Import"
    bl_description = ""
    bl_options = {"UNDO", "PRESET"}

    directory: bpy.props.StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE"})
    files: list[str]

    def invoke(self, context, event):
        import os

        os.system("cls")
        # Better FBXがインストールされていない場合はEnumアイテムを0に設定
        if not "better_fbx" in get_enabled_addon_list():
            get_ddfbx_addon_preferences().importer = "0"

    def execute(self, context):
        for file in self.files:
            filepath = Path(self.directory).joinpath(file.name)
            logger.debug(filepath)
            bpy.ops.better_import.fbx(filepath=str(filepath))
            logger.debug(f'Load Complete\n{"":#<70}')

        return {"FINISHED"}


class DDFBXIMPORT_OT_fbx_import(bpy.types.Operator):
    """Test importer that creates scripts nodes from .txt files"""

    bl_idname = "ddfbx.fbx_import"
    bl_label = "D&D Import FBX"

    """
    This Operator can import multiple .txt files, we need following directory and files
    properties that the file handler will use to set files path data
    """
    directory: bpy.props.StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE"})
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == "VIEW_3D"

    def execute(self, context):
        import os

        os.system("cls")
        """The directory property need to be set."""
        if not self.directory:
            return {"CANCELLED"}

        addon_pref = get_ddfbx_addon_preferences()
        selected_importer = addon_pref.importer
        match int(selected_importer):
            case 0:
                logger.debug("Mode 0")
                bpy.ops.ddfbx.built_in_import(
                    "INVOKE_DEFAULT", directory=self.directory, files=str(self.files.keys())
                )
            case 1:
                logger.debug("Mode 1")
                bpy.ops.ddfbx.better_fbx_import(
                    "INVOKE_DEFAULT", directory=self.directory, files=self.files.keys()
                )

        return {"FINISHED"}


"""---------------------------------------------------------
------------------------------------------------------------
    File Handler
------------------------------------------------------------
---------------------------------------------------------"""


class DDFBXIMPORT_FH_fbx_import(bpy.types.FileHandler):
    bl_idname = "DDFBXIMPORT_FH_custom_fbx_import"
    bl_label = "File Handler for Custom FBX Import"
    bl_import_operator = "ddfbx.fbx_import"
    bl_file_extensions = ".fbx"

    @classmethod
    def poll_drop(cls, context):
        return context.area and context.area.type == "VIEW_3D"


"""---------------------------------------------------------
------------------------------------------------------------
    REGISTER/UNREGISTER
------------------------------------------------------------
---------------------------------------------------------"""
CLASSES = (
    DDFBXIMPORT_PREF_addon_preference,
    DDFBXIMPORT_OT_create_preset,
    DDFBXIMPORT_OT_delete_preset,
    DDFBXIMPORT_OT_built_in_import,
    DDFBXIMPORT_OT_better_fbx_import,
    DDFBXIMPORT_OT_fbx_import,
    DDFBXIMPORT_FH_fbx_import,
)


def register():
    for cls in CLASSES:
        try:
            bpy.utils.register_class(cls)
        except:
            logger.debug(f"{cls.__name__} : already registred")

    ## Property Group の登録

    # デバッグ用
    # launch_debug_server()


def unregister():
    for cls in CLASSES:
        if hasattr(bpy.types, cls.__name__):
            bpy.utils.unregister_class(cls)
            logger.debug(f"{cls.__name__} unregistred")
